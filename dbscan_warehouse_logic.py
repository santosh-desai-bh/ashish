#!/usr/bin/env python3
"""
DBSCAN-based auxiliary warehouse placement logic
Creates auxiliaries when natural clusters have ~200 order density
"""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from shapely.geometry import Point

def assign_pincode_to_location(lat, lon):
    """Assign pincode to a warehouse location using pincode boundaries"""
    try:
        from pincode_warehouse_logic import load_pincode_boundaries
        
        pincode_boundaries = load_pincode_boundaries()
        if not pincode_boundaries:
            return "UNKNOWN", "Unknown Area"
        
        # Create point for the warehouse location
        warehouse_point = Point(lon, lat)
        
        # Find which pincode boundary contains this point
        for pincode, boundary_data in pincode_boundaries.items():
            polygon = boundary_data['polygon']
            if polygon.contains(warehouse_point):
                return pincode, boundary_data['area_name']
        
        # If not in any pincode boundary, find the nearest one
        min_distance = float('inf')
        nearest_pincode = "UNKNOWN"
        nearest_area = "Unknown Area"
        
        for pincode, boundary_data in pincode_boundaries.items():
            polygon = boundary_data['polygon']
            distance = warehouse_point.distance(polygon)
            if distance < min_distance:
                min_distance = distance
                nearest_pincode = pincode
                nearest_area = boundary_data['area_name']
        
        return nearest_pincode, nearest_area
        
    except Exception as e:
        print(f"⚠️ Could not assign pincode: {e}")
        return "UNKNOWN", "Unknown Area"

def find_dbscan_clusters(df_filtered, delivery_radius=3, min_density=200):
    """
    Use DBSCAN to find natural order clusters for auxiliary placement
    
    Args:
        df_filtered: DataFrame with order_lat, order_long columns
        delivery_radius: Last mile delivery radius in km
        min_density: Minimum orders per cluster to justify auxiliary (~200)
    
    Returns:
        List of cluster info dictionaries
    """
    
    if len(df_filtered) < 50:  # Not enough data for clustering
        print(f"⚠️  DEBUG: Too few orders ({len(df_filtered)}) for DBSCAN clustering (need ≥50)")
        return []
    
    # Prepare coordinates for clustering
    coordinates = df_filtered[['order_lat', 'order_long']].values
    
    # Scale coordinates to account for lat/long differences
    scaler = StandardScaler()
    coordinates_scaled = scaler.fit_transform(coordinates)
    
    # DBSCAN parameters based on delivery radius
    # eps: maximum distance between points in a cluster (in scaled coordinates)
    # min_samples: minimum points to form a cluster
    
    # Fixed DBSCAN parameters optimized for coverage, not delivery radius
    eps = 0.15  # Moderate cluster size - balance between too many tiny clusters and too few big ones
    min_samples = max(4, min_density // 5)  # Very low sample requirement for maximum coverage
    
    print(f"🔍 DBSCAN clustering with eps={eps}, min_samples={min_samples}")
    
    # Perform DBSCAN clustering
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
    cluster_labels = dbscan.fit_predict(coordinates_scaled)
    
    # Analyze clusters
    unique_labels = set(cluster_labels)
    noise_points = sum(1 for label in cluster_labels if label == -1)
    print(f"📊 DEBUG: DBSCAN found {len(unique_labels)} total labels, {noise_points} noise points")
    
    if -1 in unique_labels:
        unique_labels.remove(-1)  # Remove noise points
    
    print(f"📊 DEBUG: {len(unique_labels)} actual clusters found")
    
    clusters = []
    
    for label in unique_labels:
        # Get points in this cluster
        cluster_mask = cluster_labels == label
        cluster_points = df_filtered[cluster_mask]
        
        order_count = len(cluster_points)
        
        print(f"📊 DEBUG: Cluster {label}: {order_count} orders (threshold: {min_density})")
        
        # Only consider clusters with sufficient density
        if order_count >= min_density:
            print(f"✅ DEBUG: Cluster {label} passes density threshold")
            # Calculate cluster centroid
            centroid_lat = cluster_points['order_lat'].mean()
            centroid_lon = cluster_points['order_long'].mean()
            
            # Calculate cluster density (orders per km²)
            # Estimate cluster area using std deviation
            lat_std = cluster_points['order_lat'].std()
            lon_std = cluster_points['order_long'].std()
            
            # Convert to approximate km² (rough estimate)
            area_km2 = (lat_std * 111) * (lon_std * 111 * np.cos(np.radians(centroid_lat)))
            area_km2 = max(area_km2, 0.1)  # Minimum area to avoid division by zero
            
            density_score = order_count / area_km2
            
            clusters.append({
                'label': label,
                'lat': centroid_lat,
                'lon': centroid_lon,
                'order_count': order_count,
                'density_score': density_score,
                'area_km2': area_km2,
                'cluster_points': cluster_points
            })
        else:
            print(f"❌ DEBUG: Cluster {label} rejected - only {order_count} orders (need ≥{min_density})")
    
    # Sort by density score (highest density first)
    clusters.sort(key=lambda x: x['density_score'], reverse=True)
    
    print(f"📊 Found {len(clusters)} dense clusters (≥{min_density} orders)")
    for i, cluster in enumerate(clusters[:5]):  # Show top 5
        print(f"  Cluster {i+1}: {cluster['order_count']} orders, density: {cluster['density_score']:.1f}/km²")
    
    return clusters

def place_auxiliaries_at_dbscan_clusters(clusters, big_warehouses, delivery_radius=3, max_auxiliaries=6):
    """
    Place auxiliary warehouses at DBSCAN cluster centroids
    
    Args:
        clusters: List of cluster dictionaries from find_dbscan_clusters
        big_warehouses: List of main warehouse dictionaries
        delivery_radius: Last mile delivery radius in km
        max_auxiliaries: Maximum auxiliary warehouses allowed
    
    Returns:
        List of auxiliary warehouse dictionaries
    """
    
    auxiliaries = []
    aux_id = 1
    
    # Minimum separation between auxiliaries - very relaxed for maximum coverage
    min_separation = 2.0  # Fixed 2km minimum separation regardless of delivery radius
    
    print(f"📊 DEBUG: Processing {min(len(clusters), max_auxiliaries * 2)} clusters for auxiliary placement...")
    
    for cluster in clusters[:max_auxiliaries * 2]:  # Consider more clusters than limit
        cluster_lat, cluster_lon = cluster['lat'], cluster['lon']
        order_count = cluster['order_count']
        
        print(f"🔍 DEBUG: Evaluating cluster at ({cluster_lat:.3f}, {cluster_lon:.3f}) with {order_count} orders")
        
        # Find nearest main warehouse
        min_distance_to_main = float('inf')
        nearest_main = None
        
        for main_wh in big_warehouses:
            distance = ((cluster_lat - main_wh['lat'])**2 + (cluster_lon - main_wh['lon'])**2)**0.5 * 111
            if distance < min_distance_to_main:
                min_distance_to_main = distance
                nearest_main = main_wh
        
        # REMOVED: Distance-based filtering - we need coverage-first approach
        # Every order cluster should get an auxiliary if it's dense enough
        # Distance to main warehouse is irrelevant for last mile coverage
        
        # Check separation from existing auxiliaries
        too_close_to_auxiliary = False
        for existing_aux in auxiliaries:
            distance = ((cluster_lat - existing_aux['lat'])**2 + (cluster_lon - existing_aux['lon'])**2)**0.5 * 111
            if distance < min_separation:
                too_close_to_auxiliary = True
                print(f"  ⏭️  Cluster too close to existing auxiliary ({distance:.1f}km < {min_separation:.1f}km)")
                break
        
        if too_close_to_auxiliary:
            print(f"❌ DEBUG: Cluster rejected - too close to existing auxiliary")
            continue
        
        # REMOVED: Maximum distance filter - coverage is more important than middle mile efficiency
        # Electronic City and other outlying areas need coverage regardless of distance to main warehouses
        
        # Calculate auxiliary capacity (with buffer)
        capacity = max(200, int(order_count * 1.3))  # 30% buffer
        
        # Determine size category
        if capacity >= 400:
            size_category = "Large"
        elif capacity >= 300:
            size_category = "Medium"
        else:
            size_category = "Small"
        
        # Assign pincode to auxiliary warehouse
        pincode, area_name = assign_pincode_to_location(cluster_lat, cluster_lon)
        
        # Create auxiliary warehouse
        auxiliary = {
            'id': aux_id,
            'lat': cluster_lat,
            'lon': cluster_lon,
            'orders': order_count,
            'capacity': capacity,
            'size_category': size_category,
            'parent': nearest_main['id'],
            'distance_to_parent': min_distance_to_main,
            'density_score': cluster['density_score'],
            'type': 'auxiliary',
            'delivery_radius': delivery_radius,
            'cluster_label': cluster['label'],
            'method': 'DBSCAN',
            'pincode': pincode,
            'area_name': area_name
        }
        
        auxiliaries.append(auxiliary)
        aux_id += 1
        
        print(f"  ✅ DEBUG: Created Auxiliary {aux_id-1}: {order_count} orders, density: {cluster['density_score']:.1f}/km²")
        print(f"     Location: ({cluster_lat:.3f}, {cluster_lon:.3f}), Pincode: {pincode}")
        
        # Stop if we've reached the maximum
        if len(auxiliaries) >= max_auxiliaries:
            print(f"📊 DEBUG: Reached max auxiliaries limit ({max_auxiliaries})")
            break
    
    print(f"🎯 Created {len(auxiliaries)} auxiliary warehouses using DBSCAN")
    
    return auxiliaries

def create_dbscan_auxiliary_network(df_filtered, big_warehouses, delivery_radius=3):
    """
    Create auxiliary warehouse network using DBSCAN clustering
    
    Args:
        df_filtered: DataFrame with order data
        big_warehouses: List of main warehouses
        delivery_radius: Last mile delivery radius
    
    Returns:
        Tuple of (auxiliary_warehouses, cluster_info)
    """
    
    print(f"🧬 Creating DBSCAN-based auxiliary network (radius: {delivery_radius}km)")
    print(f"📊 DEBUG: Input data has {len(df_filtered)} total orders")
    print(f"📊 DEBUG: {len(big_warehouses)} main warehouses provided")
    
    # Coverage-first parameters - ignore delivery radius constraints
    # Goal: 80-90% coverage with as many auxiliaries as needed
    min_density = 15   # Very low threshold - accept small but meaningful clusters
    max_auxiliaries = 12  # Allow many auxiliaries for maximum coverage
    
    print(f"📊 DEBUG: Using min_density={min_density}, max_auxiliaries={max_auxiliaries}")
    
    # Find natural clusters using DBSCAN
    clusters = find_dbscan_clusters(df_filtered, delivery_radius, min_density)
    
    if not clusters:
        print("⚠️  No dense clusters found - no auxiliaries needed")
        return [], []
    
    # Place auxiliaries at cluster centroids
    auxiliaries = place_auxiliaries_at_dbscan_clusters(
        clusters, big_warehouses, delivery_radius, max_auxiliaries
    )
    
    return auxiliaries, clusters