import numpy as np
import pandas as pd

def find_order_density_clusters(df_filtered, min_cluster_size=30, grid_size=0.005):
    """Find high-density order clusters for feeder warehouse placement"""
    # Create density grid (finer grid for better cluster detection)
    lat_min, lat_max = df_filtered['order_lat'].min(), df_filtered['order_lat'].max()
    lon_min, lon_max = df_filtered['order_long'].min(), df_filtered['order_long'].max()
    
    # Use configurable grid size
    lat_steps = int((lat_max - lat_min) / grid_size) + 1
    lon_steps = int((lon_max - lon_min) / grid_size) + 1
    
    density_clusters = []
    
    for i in range(lat_steps):
        for j in range(lon_steps):
            cell_lat_min = lat_min + i * grid_size
            cell_lat_max = cell_lat_min + grid_size
            cell_lon_min = lon_min + j * grid_size
            cell_lon_max = cell_lon_min + grid_size
            
            # Count orders in this grid cell
            cell_orders = df_filtered[
                (df_filtered['order_lat'] >= cell_lat_min) & 
                (df_filtered['order_lat'] < cell_lat_max) &
                (df_filtered['order_long'] >= cell_lon_min) & 
                (df_filtered['order_long'] < cell_lon_max)
            ]
            
            order_count = len(cell_orders)
            
            if order_count >= min_cluster_size:
                # Calculate cluster center (centroid of orders in this cell)
                cluster_center_lat = cell_orders['order_lat'].mean()
                cluster_center_lon = cell_orders['order_long'].mean()
                
                # Calculate density score (orders per km²)
                area_km2 = (grid_size * 111) ** 2  # Convert degrees to km²
                density_score = order_count / area_km2
                
                density_clusters.append({
                    'lat': cluster_center_lat,
                    'lon': cluster_center_lon,
                    'order_count': order_count,
                    'density_score': density_score,
                    'cell_bounds': {
                        'lat_min': cell_lat_min,
                        'lat_max': cell_lat_max,
                        'lon_min': cell_lon_min,
                        'lon_max': cell_lon_max
                    }
                })
    
    # Sort by density score (orders per km²) descending
    density_clusters.sort(key=lambda x: x['density_score'], reverse=True)
    
    return density_clusters

def place_feeder_warehouses_near_clusters(density_clusters, big_warehouses, max_distance_from_big=8.0, delivery_radius=2.0, feeder_separation=1.5):
    """Place feeder warehouses at density clusters within range of big warehouses"""
    feeder_warehouses = []
    aux_id_counter = 1
    
    for cluster in density_clusters:
        cluster_lat, cluster_lon = cluster['lat'], cluster['lon']
        
        # Find nearest big warehouse
        min_distance_to_big = float('inf')
        nearest_big_warehouse = None
        
        for big_wh in big_warehouses:
            distance = ((cluster_lat - big_wh['lat'])**2 + (cluster_lon - big_wh['lon'])**2)**0.5 * 111
            if distance < min_distance_to_big:
                min_distance_to_big = distance
                nearest_big_warehouse = big_wh
        
        # Only place feeder if within reasonable distance from a big warehouse
        if min_distance_to_big <= max_distance_from_big:
            # Check if there's already a feeder warehouse too close to this location
            too_close = False
            for existing_feeder in feeder_warehouses:
                distance_to_existing = ((cluster_lat - existing_feeder['lat'])**2 + 
                                      (cluster_lon - existing_feeder['lon'])**2)**0.5 * 111
                if distance_to_existing < feeder_separation:
                    too_close = True
                    break
            
            if not too_close:
                # Determine feeder warehouse capacity - minimum 100-200 orders per warehouse
                order_count = cluster['order_count']
                
                # Calculate base capacity with proper minimums
                base_capacity = max(100, order_count * 1.2)  # 20% buffer above current orders
                
                if delivery_radius <= 2:
                    # Dense network for 2km radius - smaller warehouses but still minimum 100
                    if order_count >= 120:
                        capacity = max(200, int(base_capacity))
                        size_category = "Large"
                    elif order_count >= 60:
                        capacity = max(150, int(base_capacity))
                        size_category = "Medium"
                    else:
                        capacity = max(100, int(base_capacity))
                        size_category = "Small"
                elif delivery_radius <= 3:
                    # Balanced network for 3km radius
                    if order_count >= 150:
                        capacity = max(250, int(base_capacity))
                        size_category = "Large"
                    elif order_count >= 80:
                        capacity = max(180, int(base_capacity))
                        size_category = "Medium"
                    else:
                        capacity = max(120, int(base_capacity))
                        size_category = "Small"
                elif delivery_radius <= 5:
                    # Wider coverage for 5km radius
                    if order_count >= 200:
                        capacity = max(350, int(base_capacity))
                        size_category = "Large"
                    elif order_count >= 120:
                        capacity = max(250, int(base_capacity))
                        size_category = "Medium"
                    else:
                        capacity = max(150, int(base_capacity))
                        size_category = "Small"
                else:
                    # Very wide coverage for 7km+ radius
                    if order_count >= 250:
                        capacity = max(450, int(base_capacity))
                        size_category = "Large"
                    elif order_count >= 150:
                        capacity = max(300, int(base_capacity))
                        size_category = "Medium"
                    else:
                        capacity = max(200, int(base_capacity))
                        size_category = "Small"
                
                feeder_warehouses.append({
                    'id': aux_id_counter,
                    'lat': cluster_lat,
                    'lon': cluster_lon,
                    'orders': order_count,
                    'capacity': capacity,
                    'size_category': size_category,
                    'parent': nearest_big_warehouse['id'],
                    'distance_to_parent': min_distance_to_big,
                    'density_score': cluster['density_score'],
                    'type': 'feeder',
                    'delivery_radius': delivery_radius
                })
                
                aux_id_counter += 1
    
    return feeder_warehouses

def create_pincode_based_feeder_network(df_filtered, big_warehouses, min_cluster_size, max_distance_from_big, delivery_radius):
    """Create feeder network based on pincode clustering to eliminate overlaps"""
    try:
        from pincode_warehouse_logic import create_pincode_based_network
        
        # Use the pincode-based network creation
        feeder_assignments, density_clusters = create_pincode_based_network(
            df_filtered, big_warehouses, min_cluster_size, max_distance_from_big
        )
        
        # Convert to the expected format for compatibility
        feeder_warehouses = []
        for feeder in feeder_assignments:
            feeder_warehouses.append({
                'id': feeder['id'],
                'lat': feeder['lat'],
                'lon': feeder['lon'],
                'orders': feeder['coverage_orders'],
                'capacity': feeder['capacity'],
                'size_category': feeder['size_category'],
                'parent': feeder['parent'],
                'distance_to_parent': feeder['distance_to_parent'],
                'density_score': feeder['density'],
                'type': 'feeder',
                'delivery_radius': delivery_radius,
                'coverage_type': 'pincode_boundary',
                'pincode': feeder.get('pincode', ''),
                'area_name': feeder.get('area_name', '')
            })
        
        print(f"✅ Created {len(feeder_warehouses)} pincode-based feeders")
        return feeder_warehouses, density_clusters
        
    except Exception as e:
        print(f"❌ Pincode system failed: {e}. Falling back to grid system.")
        # Fallback to grid system if pincode system fails
        return create_grid_based_feeder_network(df_filtered, big_warehouses, min_cluster_size, max_distance_from_big, delivery_radius)

def create_grid_based_feeder_network(df_filtered, big_warehouses, min_cluster_size, max_distance_from_big, delivery_radius):
    """Create feeder network using optimized grid system with minimal overlaps"""
    
    # Use larger separation distances to minimize overlaps
    if delivery_radius <= 2:
        grid_size = 0.008  # Larger grid for less overlap
        min_gap_orders = 15
        feeder_separation = 3.0  # Increased separation
    elif delivery_radius <= 3:
        grid_size = 0.012  # Larger grid for 3km radius
        min_gap_orders = 20
        feeder_separation = 4.0  # Increased separation
    elif delivery_radius <= 5:
        grid_size = 0.018  # Much larger grid for 5km radius
        min_gap_orders = 30
        feeder_separation = 6.0  # Much larger separation
    else:
        grid_size = 0.025  # Very large grid for 7km+ radius
        min_gap_orders = 40
        feeder_separation = 8.0  # Very large separation
    
    # Step 1: Find high-density clusters with adjusted parameters
    density_clusters = find_order_density_clusters(df_filtered, min_cluster_size, grid_size)
    feeder_warehouses = place_feeder_warehouses_near_clusters(
        density_clusters, big_warehouses, max_distance_from_big, delivery_radius, feeder_separation
    )
    
    # Step 2: Find uncovered orders (more than delivery_radius from any feeder)
    uncovered_orders = []
    for _, order in df_filtered.iterrows():
        order_lat, order_lon = order['order_lat'], order['order_long']
        
        # Check distance to all feeders
        min_distance_to_feeder = float('inf')
        for feeder in feeder_warehouses:
            distance = ((order_lat - feeder['lat'])**2 + (order_lon - feeder['lon'])**2)**0.5 * 111
            min_distance_to_feeder = min(min_distance_to_feeder, distance)
        
        # If more than delivery_radius from nearest feeder, mark as uncovered
        if min_distance_to_feeder > delivery_radius:
            uncovered_orders.append({
                'lat': order_lat,
                'lon': order_lon,
                'distance_to_nearest_feeder': min_distance_to_feeder
            })
    
    # Step 3: Create additional feeders for uncovered areas
    additional_feeders = []
    aux_id_counter = len(feeder_warehouses) + 1
    
    if uncovered_orders:
        # Group uncovered orders by proximity
        uncovered_df = pd.DataFrame(uncovered_orders)
        
        # Use grid for uncovered areas
        lat_min, lat_max = uncovered_df['lat'].min(), uncovered_df['lat'].max()
        lon_min, lon_max = uncovered_df['lon'].min(), uncovered_df['lon'].max()
        
        # Adjust grid size for gap-filling based on delivery radius
        gap_grid_size = grid_size * 1.5
        lat_steps = int((lat_max - lat_min) / gap_grid_size) + 1
        lon_steps = int((lon_max - lon_min) / gap_grid_size) + 1
        
        for i in range(lat_steps):
            for j in range(lon_steps):
                cell_lat_min = lat_min + i * gap_grid_size
                cell_lat_max = cell_lat_min + gap_grid_size
                cell_lon_min = lon_min + j * gap_grid_size
                cell_lon_max = cell_lon_min + gap_grid_size
                
                # Count uncovered orders in this cell
                cell_uncovered = [
                    order for order in uncovered_orders
                    if (cell_lat_min <= order['lat'] < cell_lat_max) and 
                       (cell_lon_min <= order['lon'] < cell_lon_max)
                ]
                
                if len(cell_uncovered) >= min_gap_orders:
                    # Calculate center of uncovered orders in this cell
                    cell_center_lat = sum([order['lat'] for order in cell_uncovered]) / len(cell_uncovered)
                    cell_center_lon = sum([order['lon'] for order in cell_uncovered]) / len(cell_uncovered)
                    
                    # Find nearest big warehouse
                    min_distance_to_big = float('inf')
                    nearest_big_warehouse = None
                    
                    for big_wh in big_warehouses:
                        distance = ((cell_center_lat - big_wh['lat'])**2 + (cell_center_lon - big_wh['lon'])**2)**0.5 * 111
                        if distance < min_distance_to_big:
                            min_distance_to_big = distance
                            nearest_big_warehouse = big_wh
                    
                    # Only place if within distance limit and not too close to existing feeders
                    if min_distance_to_big <= max_distance_from_big:
                        too_close = False
                        all_feeders = feeder_warehouses + additional_feeders
                        
                        for existing_feeder in all_feeders:
                            distance_to_existing = ((cell_center_lat - existing_feeder['lat'])**2 + 
                                                  (cell_center_lon - existing_feeder['lon'])**2)**0.5 * 111
                            if distance_to_existing < feeder_separation:
                                too_close = True
                                break
                        
                        if not too_close:
                            # Adjust capacity based on delivery radius and order count - minimum 100 orders
                            base_capacity = max(100, len(cell_uncovered) * 1.5)  # 50% buffer for uncovered areas
                            
                            if delivery_radius <= 2:
                                capacity = max(100, min(200, int(base_capacity)))
                            elif delivery_radius <= 3:
                                capacity = max(120, min(250, int(base_capacity)))
                            elif delivery_radius <= 5:
                                capacity = max(150, min(300, int(base_capacity)))
                            else:
                                capacity = max(200, min(400, int(base_capacity)))
                            
                            size_category = "Large" if capacity >= 250 else "Medium" if capacity >= 150 else "Small"
                            
                            additional_feeders.append({
                                'id': aux_id_counter,
                                'lat': cell_center_lat,
                                'lon': cell_center_lon,
                                'orders': len(cell_uncovered),
                                'capacity': capacity,
                                'size_category': size_category,
                                'parent': nearest_big_warehouse['id'],
                                'distance_to_parent': min_distance_to_big,
                                'density_score': len(cell_uncovered) / ((gap_grid_size * 111) ** 2),
                                'type': 'feeder',
                                'delivery_radius': delivery_radius
                            })
                            aux_id_counter += 1
    
    # Combine all feeders
    all_feeders = feeder_warehouses + additional_feeders
    
    # Add delivery radius info to all feeders
    for feeder in all_feeders:
        feeder['delivery_radius'] = delivery_radius
    
    return all_feeders, density_clusters

def create_comprehensive_feeder_network(df_filtered, big_warehouses, min_cluster_size=20, max_distance_from_big=8.0, delivery_radius=2.0):
    """Create a comprehensive feeder network using pincode-based clustering to minimize overlaps"""
    
    # Try pincode-based clustering first if postcode data is available
    if 'postcode' in df_filtered.columns:
        return create_pincode_based_feeder_network(df_filtered, big_warehouses, min_cluster_size, max_distance_from_big, delivery_radius)
    
    # Fallback to optimized grid system with minimal overlaps
    return create_grid_based_feeder_network(df_filtered, big_warehouses, min_cluster_size, max_distance_from_big, delivery_radius)

def determine_optimal_date_range(daily_summary, max_orders=5000):
    """Determine optimal date range for performance"""
    daily_summary = daily_summary.sort_values('Date', ascending=False)
    
    cumulative_orders = 0
    optimal_days = 0
    
    for _, row in daily_summary.iterrows():
        cumulative_orders += row['Orders']
        optimal_days += 1
        
        if cumulative_orders >= max_orders:
            break
    
    return optimal_days

def calculate_big_warehouse_locations(df_filtered):
    """Calculate optimal locations for big warehouses (IF Hubs) with minimum 4-5 hubs"""
    try:
        total_orders = len(df_filtered)
        
        # Ensure minimum 4-5 big warehouses for proper first mile coverage
        big_warehouse_count = max(5, total_orders // 400)  # Minimum 5 hubs, 400 orders per hub
        big_warehouse_count = min(big_warehouse_count, 8)  # Cap at 8 for Bangalore
        
        # Use geographic distribution for warehouse placement - prioritize city center areas
        lat_median = df_filtered['order_lat'].median()
        lon_median = df_filtered['order_long'].median()
        lat_range = df_filtered['order_lat'].max() - df_filtered['order_lat'].min()
        lon_range = df_filtered['order_long'].max() - df_filtered['order_long'].min()
        
        # Handle edge case where lat_range or lon_range is 0
        if lat_range == 0:
            lat_range = 0.01
        if lon_range == 0:
            lon_range = 0.01
        
        # Find high-density urban areas for big warehouse placement
        grid_size = 5
        lat_step = lat_range / grid_size
        lon_step = lon_range / grid_size
        
        density_zones = []
        for i in range(grid_size):
            for j in range(grid_size):
                zone_lat_min = df_filtered['order_lat'].min() + i * lat_step
                zone_lat_max = zone_lat_min + lat_step
                zone_lon_min = df_filtered['order_long'].min() + j * lon_step
                zone_lon_max = zone_lon_min + lon_step
                
                # Count orders in this zone
                zone_orders = df_filtered[
                    (df_filtered['order_lat'] >= zone_lat_min) & 
                    (df_filtered['order_lat'] < zone_lat_max) &
                    (df_filtered['order_long'] >= zone_lon_min) & 
                    (df_filtered['order_long'] < zone_lon_max)
                ]
                
                if len(zone_orders) > 0:
                    zone_center_lat = zone_lat_min + lat_step/2
                    zone_center_lon = zone_lon_min + lon_step/2
                    density_zones.append({
                        'lat': zone_center_lat,
                        'lon': zone_center_lon,
                        'density': len(zone_orders),
                        'distance_from_center': ((zone_center_lat - lat_median)**2 + (zone_center_lon - lon_median)**2)**0.5
                    })
        
        # Sort zones by DENSITY FIRST - prioritize high order areas regardless of location
        density_zones.sort(key=lambda x: -x['density'])  # Highest density first
        
        # Select top density zones for big warehouses - no distance restriction
        urban_zones = density_zones[:big_warehouse_count * 3]  # Get top density zones
        
        # Place big warehouses (IF Hubs) - prioritize density but ensure geographic spread
        if len(urban_zones) >= big_warehouse_count:
            big_warehouse_centers = []
            selected_zones = []
            
            # First, take the highest density zone
            if urban_zones:
                selected_zones.append(urban_zones[0])
                big_warehouse_centers.append([urban_zones[0]['lat'], urban_zones[0]['lon']])
            
            # For remaining warehouses, balance density and distance
            for i in range(1, big_warehouse_count):
                best_zone = None
                best_score = -1
                
                for zone in urban_zones:
                    if zone in selected_zones:
                        continue
                    
                    # Calculate minimum distance to existing warehouses
                    min_distance_to_selected = float('inf')
                    for selected in selected_zones:
                        distance = ((zone['lat'] - selected['lat'])**2 + (zone['lon'] - selected['lon'])**2)**0.5 * 111  # km
                        min_distance_to_selected = min(min_distance_to_selected, distance)
                    
                    # Score combines density and distance (avoid too close warehouses)
                    density_score = zone['density'] / max([z['density'] for z in urban_zones])  # Normalize 0-1
                    distance_score = min(min_distance_to_selected / 10, 1.0)  # Normalize, prefer >10km apart
                    
                    # Combined score: 70% density, 30% distance
                    combined_score = 0.7 * density_score + 0.3 * distance_score
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_zone = zone
                
                if best_zone:
                    selected_zones.append(best_zone)
                    big_warehouse_centers.append([best_zone['lat'], best_zone['lon']])
        else:
            # Fallback to geometric distribution for better coverage
            big_warehouse_centers = []
            if big_warehouse_count == 5:
                # Optimized 5-point distribution for Bangalore
                big_warehouse_centers = [
                    [lat_median, lon_median],  # Center
                    [lat_median + lat_range/4, lon_median + lon_range/4],  # NE
                    [lat_median + lat_range/4, lon_median - lon_range/4],  # NW
                    [lat_median - lat_range/4, lon_median + lon_range/4],  # SE
                    [lat_median - lat_range/4, lon_median - lon_range/4]   # SW
                ]
            elif big_warehouse_count == 6:
                big_warehouse_centers = [
                    [lat_median, lon_median],  # Center
                    [lat_median + lat_range/3, lon_median],  # North
                    [lat_median - lat_range/3, lon_median],  # South
                    [lat_median, lon_median + lon_range/3],  # East
                    [lat_median, lon_median - lon_range/3],  # West
                    [lat_median + lat_range/5, lon_median + lon_range/5]   # NE
                ]
            else:
                # Default distribution pattern
                angle_step = 2 * 3.14159 / (big_warehouse_count - 1) if big_warehouse_count > 1 else 0
                radius_lat = lat_range / 3
                radius_lon = lon_range / 3
                
                big_warehouse_centers = [[lat_median, lon_median]]  # Center hub
                
                for i in range(1, big_warehouse_count):
                    angle = (i - 1) * angle_step
                    hub_lat = lat_median + radius_lat * np.cos(angle)
                    hub_lon = lon_median + radius_lon * np.sin(angle)
                    big_warehouse_centers.append([hub_lat, hub_lon])
        
        return big_warehouse_centers, big_warehouse_count
    
    except Exception as e:
        # Fallback to simple center placement if anything goes wrong
        print(f"Error in calculate_big_warehouse_locations: {e}")
        lat_center = df_filtered['order_lat'].mean()
        lon_center = df_filtered['order_long'].mean()
        return [[lat_center, lon_center]], 1
