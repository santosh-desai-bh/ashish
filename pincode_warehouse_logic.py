#!/usr/bin/env python3
"""
Pincode-based feeder warehouse placement logic to eliminate overlapping coverage
"""

import json
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import folium

def load_pincode_boundaries():
    """Load Bangalore pincode boundaries from GeoJSON"""
    try:
        # Try multiple possible locations for the GeoJSON file
        possible_paths = [
            '/Users/blowhorn/Downloads/bengaluru.geojson',
            '/Users/blowhorn/ashish/bengaluru.geojson',
            './bengaluru.geojson',
            'bengaluru.geojson'
        ]
        
        geojson_data = None
        for path in possible_paths:
            try:
                with open(path, 'r') as f:
                    geojson_data = json.load(f)
                print(f"✅ Loaded GeoJSON from: {path}")
                break
            except FileNotFoundError:
                continue
        
        if not geojson_data:
            raise FileNotFoundError("GeoJSON file not found in any expected location")
        
        pincode_boundaries = {}
        for feature in geojson_data['features']:
            properties = feature['properties']
            pincode = str(properties.get('pin_code', ''))
            area_name = properties.get('area_name', '')
            
            if pincode and feature['geometry']['type'] == 'Polygon':
                coords = feature['geometry']['coordinates'][0]
                polygon = Polygon(coords)
                
                pincode_boundaries[pincode] = {
                    'polygon': polygon,
                    'area_name': area_name,
                    'centroid': polygon.centroid,
                    'bounds': polygon.bounds  # (minx, miny, maxx, maxy)
                }
        
        print(f"✅ Loaded {len(pincode_boundaries)} pincode boundaries")
        return pincode_boundaries
        
    except Exception as e:
        print(f"❌ Error loading pincode boundaries: {e}")
        return {}

def analyze_order_density_by_pincode(df_filtered, pincode_boundaries):
    """Analyze order density for each pincode area"""
    pincode_analysis = {}
    
    for pincode, boundary_info in pincode_boundaries.items():
        polygon = boundary_info['polygon']
        
        # Count orders within this pincode boundary
        orders_in_pincode = []
        for _, order in df_filtered.iterrows():
            order_point = Point(order['order_long'], order['order_lat'])
            if polygon.contains(order_point):
                orders_in_pincode.append(order)
        
        if orders_in_pincode:
            order_count = len(orders_in_pincode)
            
            # Calculate area in km²
            bounds = polygon.bounds
            width_km = (bounds[2] - bounds[0]) * 111  # degrees to km
            height_km = (bounds[3] - bounds[1]) * 111
            area_km2 = width_km * height_km
            
            density = order_count / area_km2 if area_km2 > 0 else 0
            
            # Calculate centroid of actual orders (not geometric centroid)
            if len(orders_in_pincode) > 0:
                orders_df = pd.DataFrame(orders_in_pincode)
                order_centroid_lat = orders_df['order_lat'].mean()
                order_centroid_lon = orders_df['order_long'].mean()
            else:
                centroid = boundary_info['centroid']
                order_centroid_lat = centroid.y
                order_centroid_lon = centroid.x
            
            pincode_analysis[pincode] = {
                'area_name': boundary_info['area_name'],
                'order_count': order_count,
                'area_km2': area_km2,
                'density': density,
                'order_centroid': {'lat': order_centroid_lat, 'lon': order_centroid_lon},
                'geometric_centroid': {'lat': boundary_info['centroid'].y, 'lon': boundary_info['centroid'].x},
                'polygon': polygon,
                'orders': orders_in_pincode
            }
    
    return pincode_analysis

def select_optimal_pincode_feeders(pincode_analysis, min_orders_per_feeder=50, max_feeders=8):
    """Select optimal pincodes for feeder warehouse placement"""
    
    # Sort pincodes by order density and count
    candidates = []
    for pincode, analysis in pincode_analysis.items():
        if analysis['order_count'] >= min_orders_per_feeder:
            # Score based on both density and absolute count
            score = (analysis['density'] * 0.6) + (analysis['order_count'] * 0.4)
            
            candidates.append({
                'pincode': pincode,
                'score': score,
                'order_count': analysis['order_count'],
                'density': analysis['density'],
                'analysis': analysis
            })
    
    # Sort by score (highest first)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Select top candidates avoiding geographic overlap
    selected_feeders = []
    used_polygons = []
    
    for candidate in candidates[:max_feeders]:
        candidate_polygon = candidate['analysis']['polygon']
        
        # Check for significant overlap with already selected areas
        has_major_overlap = False
        for used_polygon in used_polygons:
            try:
                intersection = candidate_polygon.intersection(used_polygon)
                if intersection.area > (candidate_polygon.area * 0.3):  # >30% overlap
                    has_major_overlap = True
                    break
            except:
                continue
        
        if not has_major_overlap:
            selected_feeders.append({
                'pincode': candidate['pincode'],
                'area_name': candidate['analysis']['area_name'],
                'order_count': candidate['analysis']['order_count'],
                'density': candidate['analysis']['density'],
                'centroid_lat': candidate['analysis']['order_centroid']['lat'],
                'centroid_lon': candidate['analysis']['order_centroid']['lon'],
                'coverage_area_km2': candidate['analysis']['area_km2'],
                'polygon': candidate_polygon
            })
            used_polygons.append(candidate_polygon)
    
    return selected_feeders

def assign_feeders_to_hubs(selected_feeders, big_warehouses, max_distance_km=10):
    """Assign each feeder to the nearest big warehouse hub"""
    
    feeder_assignments = []
    
    for i, feeder in enumerate(selected_feeders):
        # Find nearest big warehouse
        min_distance = float('inf')
        nearest_hub = None
        
        for hub in big_warehouses:
            # Calculate distance
            distance = ((feeder['centroid_lat'] - hub['lat'])**2 + 
                       (feeder['centroid_lon'] - hub['lon'])**2)**0.5 * 111
            
            if distance < min_distance and distance <= max_distance_km:
                min_distance = distance
                nearest_hub = hub
        
        if nearest_hub:
            # Estimate daily capacity based on order density and area - minimum 100 orders
            base_capacity = max(100, int(feeder['order_count'] * 1.2))  # 20% buffer, minimum 100
            daily_capacity = min(base_capacity, 400)  # Maximum 400 for very high density areas
            
            feeder_assignments.append({
                'id': f"PF{i+1}",  # Pincode Feeder
                'pincode': feeder['pincode'],
                'area_name': feeder['area_name'],
                'lat': feeder['centroid_lat'],
                'lon': feeder['centroid_lon'],
                'parent': nearest_hub['id'],
                'distance_to_parent': min_distance,
                'capacity': daily_capacity,
                'coverage_orders': feeder['order_count'],
                'coverage_area_km2': feeder['coverage_area_km2'],
                'density': feeder['density'],
                'coverage_type': 'pincode_boundary',
                'polygon': feeder['polygon'],
                'size_category': 'Large' if daily_capacity >= 250 else 'Medium' if daily_capacity >= 150 else 'Small'
            })
    
    return feeder_assignments

def create_pincode_based_network(df_filtered, big_warehouses, min_orders_per_feeder=50, max_distance_from_hub=10, delivery_radius=3):
    """Create complete pincode-based feeder network"""
    
    print("🗺️ Creating pincode-based feeder network...")
    
    # Load pincode boundaries
    pincode_boundaries = load_pincode_boundaries()
    if not pincode_boundaries:
        return [], []  # Return empty if can't load boundaries
    
    # Analyze order density by pincode
    print("📊 Analyzing order density by pincode...")
    pincode_analysis = analyze_order_density_by_pincode(df_filtered, pincode_boundaries)
    
    print(f"📍 Found orders in {len(pincode_analysis)} pincodes")
    
    # Calculate max_feeders based on delivery radius
    # Smaller radius = more warehouses needed for coverage
    if delivery_radius <= 2:
        max_feeders = 35  # Dense network for 2km radius
    elif delivery_radius <= 3:
        max_feeders = 25  # Balanced network for 3km radius
    else:  # 5km radius
        max_feeders = 15  # Wider coverage for 5km radius
    
    # Select optimal pincode areas for feeders
    print("🎯 Selecting optimal feeder locations...")
    selected_feeders = select_optimal_pincode_feeders(
        pincode_analysis, 
        min_orders_per_feeder=min_orders_per_feeder,
        max_feeders=max_feeders
    )
    
    print(f"✅ Selected {len(selected_feeders)} pincode areas for feeders")
    
    # Assign feeders to nearest hubs
    print("🔗 Assigning feeders to hubs...")
    feeder_assignments = assign_feeders_to_hubs(
        selected_feeders, 
        big_warehouses, 
        max_distance_km=max_distance_from_hub
    )
    
    # Create density clusters for visualization (simplified)
    density_clusters = []
    for feeder in feeder_assignments:
        density_clusters.append({
            'lat': feeder['lat'],
            'lon': feeder['lon'],
            'order_count': feeder['coverage_orders'],
            'density_score': feeder['density']
        })
    
    print(f"🏭 Created {len(feeder_assignments)} pincode-based feeders")
    return feeder_assignments, density_clusters

def add_pincode_feeder_visualization(m, feeder_assignments):
    """Add pincode-based feeder visualization to map"""
    
    if not feeder_assignments:
        return
    
    # Create feeder layer
    feeder_layer = folium.FeatureGroup(name="📍 Feeders")
    
    for feeder in feeder_assignments:
        # Add feeder marker
        size_color = {'Small': 'lightblue', 'Medium': 'orange', 'Large': 'red'}
        
        folium.CircleMarker(
            location=[feeder['lat'], feeder['lon']],
            radius=8 + (feeder['capacity'] / 25),  # Size based on capacity
            popup=f"""
            <b>Feeder {feeder['id']}</b><br>
            <b>Pincode:</b> {feeder['pincode']}<br>
            <b>Area:</b> {feeder['area_name']}<br>
            <b>Daily Capacity:</b> {feeder['capacity']} orders<br>
            <b>Coverage:</b> {feeder['coverage_orders']} orders<br>
            <b>Area:</b> {feeder['coverage_area_km2']:.1f} km²<br>
            <b>Density:</b> {feeder['density']:.1f} orders/km²<br>
            <b>Parent Hub:</b> {feeder['parent']}<br>
            <b>Distance:</b> {feeder['distance_to_parent']:.1f} km
            """,
            tooltip=f"Feeder {feeder['id']} - {feeder['pincode']} ({feeder['capacity']} orders/day)",
            color='darkblue',
            weight=2,
            fill=True,
            fillColor=size_color.get(feeder['size_category'], 'orange'),
            fillOpacity=0.8
        ).add_to(feeder_layer)
        
        # Add capacity indicator
        folium.Marker(
            location=[feeder['lat'], feeder['lon']],
            icon=folium.DivIcon(
                html=f'<div style="color: white; font-weight: bold; font-size: 10px; text-align: center; text-shadow: 1px 1px 1px black;">{feeder["capacity"]}</div>',
                icon_size=(25, 15),
                icon_anchor=(12, 7)
            )
        ).add_to(feeder_layer)
    
    feeder_layer.add_to(m)
    
    # Add pincode boundaries layer (optional)
    boundary_layer = folium.FeatureGroup(name="🗺️ Coverage Areas")
    
    for feeder in feeder_assignments:
        if hasattr(feeder['polygon'], 'exterior'):
            # Convert polygon to coordinates for folium
            coords = list(feeder['polygon'].exterior.coords)
            folium.Polygon(
                locations=[(lat, lon) for lon, lat in coords],
                popup=f"Coverage: {feeder['pincode']} - {feeder['area_name']}",
                tooltip=f"{feeder['coverage_orders']} orders in {feeder['pincode']}",
                color='green',
                weight=2,
                fill=True,
                fillColor='lightgreen',
                fillOpacity=0.1
            ).add_to(boundary_layer)
    
    boundary_layer.add_to(m)

if __name__ == "__main__":
    print("🧪 Testing pincode-based feeder placement...")
    # This would be called from the main visualization system