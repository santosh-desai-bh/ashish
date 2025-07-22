import folium
from warehouse_logic import find_order_density_clusters, place_feeder_warehouses_near_clusters, calculate_big_warehouse_locations, create_comprehensive_feeder_network
from pincode_warehouse_logic import create_pincode_based_network, add_pincode_feeder_visualization
import pandas as pd

def generate_geographic_hub_name(hub_lat, hub_lon, df_filtered, hub_id):
    """Generate geographic hub name based on actual position relative to city center and data distribution"""
    
    # Calculate city center from data
    center_lat = df_filtered['order_lat'].median()
    center_lon = df_filtered['order_long'].median()
    
    # Calculate relative position
    lat_diff = hub_lat - center_lat
    lon_diff = hub_lon - center_lon
    
    # Determine primary direction
    if abs(lat_diff) > abs(lon_diff):
        # More north-south movement
        if lat_diff > 0:
            primary = "NTH"  # North
        else:
            primary = "STH"  # South
    else:
        # More east-west movement  
        if lon_diff > 0:
            primary = "EST"  # East
        else:
            primary = "WST"  # West
    
    # Add secondary direction for precision if significant
    if abs(lat_diff) > 0.01 and abs(lon_diff) > 0.01:  # Both are significant
        if lat_diff > 0 and lon_diff > 0:
            return "NE"   # Northeast
        elif lat_diff > 0 and lon_diff < 0:
            return "NW"   # Northwest  
        elif lat_diff < 0 and lon_diff > 0:
            return "SE"   # Southeast
        elif lat_diff < 0 and lon_diff < 0:
            return "SW"   # Southwest
    
    # Check if very close to center
    if abs(lat_diff) < 0.005 and abs(lon_diff) < 0.005:
        return "CTR"  # Central
    
    return primary

def create_warehouse_network(df_filtered, m, min_cluster_size, max_distance_from_big, delivery_radius=2):
    """Create the complete warehouse network on the map"""
    
    # Calculate big warehouse locations
    big_warehouse_centers, big_warehouse_count = calculate_big_warehouse_locations(df_filtered)
    
    # Create separate layers for hubs and auxiliaries 
    hub_layer = folium.FeatureGroup(name=f"🏭 Hub Warehouses ({big_warehouse_count})")
    auxiliary_warehouse_layer = folium.FeatureGroup(name=f"📦 Auxiliary Warehouses (auto-calculated | {delivery_radius}km)")
    
    big_warehouses = []
    
    # Place IF Hub warehouses
    for i, center in enumerate(big_warehouse_centers):
        lat, lon = center[0], center[1]
        
        # Generate geographic hub name based on position
        hub_code = generate_geographic_hub_name(lat, lon, df_filtered, i+1)
        
        # Count orders served by this hub warehouse
        orders_served = 0
        for _, row in df_filtered.iterrows():
            distance = ((row['order_lat'] - lat)**2 + (row['order_long'] - lon)**2)**0.5 * 111
            if distance <= 8:  # 8km radius for hub warehouse
                orders_served += 1
        
        big_warehouses.append({
            'id': i+1,
            'hub_code': hub_code,
            'lat': lat,
            'lon': lon,
            'orders': orders_served,
            'capacity': 500,
            'type': 'hub'
        })
        
        # Add hub warehouse marker with enhanced details
        hub_capacity_utilization = (orders_served/500)*100
        hub_popup = f"<b>{hub_code} Main Hub</b><br>📍 Geographic Zone: {hub_code}<br>🏢 Type: Main Distribution Hub<br>🏗️ Size: 1000-1500 sqft<br>⚡ Daily Capacity: 500 orders<br>📊 Current Orders: {orders_served}<br>📈 Utilization: {hub_capacity_utilization:.1f}%<br>🎯 Coverage: 8km radius<br>💰 Monthly Rent: ₹35,000<br>🔄 Role: Primary sorting & auxiliary coordination"
        
        folium.Marker(
            location=[lat, lon],
            popup=hub_popup,
            tooltip=f"🏭 {hub_code} Hub | Capacity: 500 | Current: {orders_served}",
            icon=folium.Icon(color='red', icon='industry', prefix='fa')
        ).add_to(hub_layer)
        
        # Add capacity indicator for hub
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f'<div style="background: red; color: white; border-radius: 3px; padding: 2px 6px; font-size: 12px; font-weight: bold; border: 1px solid white; box-shadow: 1px 1px 3px rgba(0,0,0,0.4);">500</div>',
                icon_size=(35, 18),
                icon_anchor=(17, -10)
            )
        ).add_to(hub_layer)
        
        # Add coverage circle for hub warehouse
        folium.Circle(
            location=[lat, lon],
            radius=8000,
            popup=f"Blowhorn IF Hub {i+1} Primary Coverage",
            color='red',
            weight=3,
            fill=True,
            fillColor='red',
            fillOpacity=0.1
        ).add_to(hub_layer)
    
    # Create pincode-based feeder network (no overlaps!)
    try:
        feeder_warehouses, density_clusters = create_pincode_based_network(
            df_filtered, big_warehouses, min_cluster_size, max_distance_from_big
        )
        using_pincode_system = True
    except Exception as e:
        print(f"⚠️ Pincode system failed ({e}), falling back to grid-based system")
        # Fallback to original grid system
        feeder_warehouses, density_clusters = create_comprehensive_feeder_network(
            df_filtered, big_warehouses, min_cluster_size, max_distance_from_big, delivery_radius
        )
        using_pincode_system = False
    
    # Add feeder warehouses to map based on system type
    if using_pincode_system:
        # Use specialized pincode visualization
        add_pincode_feeder_visualization(m, feeder_warehouses)
        
        # Calculate orders within coverage for analytics
        for feeder_wh in feeder_warehouses:
            if 'coverage_orders' in feeder_wh:
                feeder_wh['orders_within_radius'] = feeder_wh['coverage_orders']
            else:
                # Fallback calculation for pincode system
                orders_within_radius = 0
                for _, row in df_filtered.iterrows():
                    distance = ((row['order_lat'] - feeder_wh['lat'])**2 + (row['order_long'] - feeder_wh['lon'])**2)**0.5 * 111
                    if distance <= delivery_radius:
                        orders_within_radius += 1
                feeder_wh['orders_within_radius'] = orders_within_radius
    
    else:
        # Use original circular system visualization
        for feeder_wh in feeder_warehouses:
            # Calculate actual orders within delivery radius
            orders_within_radius = 0
            for _, row in df_filtered.iterrows():
                distance = ((row['order_lat'] - feeder_wh['lat'])**2 + (row['order_long'] - feeder_wh['lon'])**2)**0.5 * 111
                if distance <= delivery_radius:
                    orders_within_radius += 1
            
            feeder_wh['orders_within_radius'] = orders_within_radius
            
            # Get auxiliary name if available (from analytics naming)
            aux_name = feeder_wh.get('aux_name', f"AX{feeder_wh['id']}")
            hub_code = feeder_wh.get('hub_code', f"HUB{feeder_wh['parent']}")
            
            # Use centralized color coding
            from analytics import HUB_COLORS
            icon_color = HUB_COLORS.get(hub_code, 'lightred')
            
            # Create auxiliary popup text with enhanced info
            rent_amount = 12000 if feeder_wh['size_category'] == 'Small' else 15000 if feeder_wh['size_category'] == 'Medium' else 18000
            vehicle_assigned = feeder_wh.get('vehicle_assigned', 'Mini Truck')
            capacity_utilization = (orders_within_radius / feeder_wh['capacity']) * 100 if feeder_wh['capacity'] > 0 else 0
            aux_popup = f"<b>{aux_name} Auxiliary Hub</b><br>📍 Parent Hub: {hub_code}<br>📦 Type: Last-mile Auxiliary<br>🏢 Size: {feeder_wh['size_category']} (400-800 sqft)<br>⚡ Daily Capacity: {feeder_wh['capacity']} orders<br>📊 Current Orders: {orders_within_radius}<br>📈 Utilization: {capacity_utilization:.1f}%<br>🛣️ Distance to Hub: {feeder_wh['distance_to_parent']:.1f}km<br>🚛 Vehicle: {vehicle_assigned}<br>💰 Monthly Rent: ₹{rent_amount:,}"
            
            # Add auxiliary warehouse icon with capacity indicator
            folium.Marker(
                location=[feeder_wh['lat'], feeder_wh['lon']],
                popup=aux_popup,
                tooltip=f"📦 {aux_name} | Capacity: {feeder_wh['capacity']} | Current: {orders_within_radius}",
                icon=folium.Icon(color=icon_color, icon='warehouse', prefix='fa')
            ).add_to(auxiliary_warehouse_layer)
            
            # Add capacity indicator as a small label
            folium.Marker(
                location=[feeder_wh['lat'], feeder_wh['lon']],
                icon=folium.DivIcon(
                    html=f'<div style="background: {icon_color}; color: white; border-radius: 3px; padding: 2px 4px; font-size: 10px; font-weight: bold; border: 1px solid white; box-shadow: 1px 1px 2px rgba(0,0,0,0.3);">{feeder_wh["capacity"]}</div>',
                    icon_size=(30, 15),
                    icon_anchor=(15, 25)
                )
            ).add_to(auxiliary_warehouse_layer)
            
            # Add connection line to parent hub
            parent_hub = next((wh for wh in big_warehouses if wh['id'] == feeder_wh['parent']), None)
            if parent_hub:
                # Extract hub code to avoid nested f-string issues
                parent_hub_code = parent_hub.get('hub_code', f"HUB{parent_hub['id']}")
                
                folium.PolyLine(
                    locations=[
                        [parent_hub['lat'], parent_hub['lon']],
                        [feeder_wh['lat'], feeder_wh['lon']]
                    ],
                    color=icon_color,
                    weight=2,
                    opacity=0.7,
                    dash_array='5, 5',
                    popup=f"Connection: {parent_hub_code} → {aux_name}<br>Distance: {feeder_wh['distance_to_parent']:.1f}km<br>Capacity Flow: {feeder_wh['capacity']} orders/day",
                    tooltip=f"🔗 {parent_hub_code} → {aux_name}"
                ).add_to(auxiliary_warehouse_layer)
            
            # Add delivery radius coverage circle (only for circular system)
            radius_meters = delivery_radius * 1000
            circle_color = 'orange' if delivery_radius <= 3 else 'yellow' if delivery_radius <= 5 else 'red'
            
            folium.Circle(
                location=[feeder_wh['lat'], feeder_wh['lon']],
                radius=radius_meters,
                popup=f"IF Feeder {feeder_wh['id']} - {delivery_radius}km Delivery Zone<br>{orders_within_radius} orders within range",
                tooltip=f"{delivery_radius}km delivery zone - {orders_within_radius} orders",
                color=circle_color,
                weight=2,
                fill=True,
                fillColor=circle_color,
                fillOpacity=0.15
            ).add_to(auxiliary_warehouse_layer)
    
    # Add both warehouse layers to the map
    hub_layer.add_to(m)
    auxiliary_warehouse_layer.add_to(m)
    
    # Calculate coverage statistics
    total_orders = len(df_filtered)
    covered_orders = 0
    
    for _, order in df_filtered.iterrows():
        order_lat, order_lon = order['order_lat'], order['order_long']
        
        # Check if within delivery_radius of any feeder
        within_radius = False
        for feeder in feeder_warehouses:
            distance = ((order_lat - feeder['lat'])**2 + (order_lon - feeder['lon'])**2)**0.5 * 111
            if distance <= delivery_radius:
                within_radius = True
                break
        
        if within_radius:
            covered_orders += 1
    
    coverage_percentage = (covered_orders / total_orders) * 100 if total_orders > 0 else 0
    
    print(f"Coverage Analysis ({delivery_radius}km radius): {covered_orders}/{total_orders} orders within range ({coverage_percentage:.1f}%)")
    
    return big_warehouses, feeder_warehouses, density_clusters

def add_density_clusters(m, density_clusters):
    """Add density clusters visualization to map"""
    clusters_layer = folium.FeatureGroup(name="🎯 Clusters")
    
    for i, cluster in enumerate(density_clusters[:30]):
        color = 'darkgreen' if cluster['order_count'] >= 100 else 'green' if cluster['order_count'] >= 50 else 'lightgreen'
        
        folium.CircleMarker(
            location=[cluster['lat'], cluster['lon']],
            radius=8,
            popup=f"Density Cluster {i+1}<br>Orders: {cluster['order_count']}<br>Density: {cluster['density_score']:.1f} orders/km²<br>Suitable for feeder warehouse",
            tooltip=f"🎯 Cluster {i+1} - {cluster['order_count']} orders",
            color=color,
            weight=2,
            fill=True,
            fillColor=color,
            fillOpacity=0.6
        ).add_to(clusters_layer)
    
    clusters_layer.add_to(m)

def create_relay_routes(m, df_filtered, big_warehouses, feeder_warehouses):
    """Create separate relay routes visualization layers on map"""
    
    # Create separate layers for different route types
    collection_layer = folium.FeatureGroup(name="🚚 Collection Routes")
    auxiliary_layer = folium.FeatureGroup(name="🔗 Hub-Auxiliary Routes") 
    interhub_layer = folium.FeatureGroup(name="🔄 Inter-Hub Relays")
    
    # Get pickup hubs data
    pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
    
    # First Mile: Customer pickups to nearest hub warehouse
    for _, hub in pickup_hubs.iterrows():
        hub_lat, hub_lon = hub['pickup_lat'], hub['pickup_long']
        
        # Find nearest hub warehouse
        min_distance = float('inf')
        nearest_hub = None
        
        for warehouse in big_warehouses:
            distance = ((hub_lat - warehouse['lat'])**2 + (hub_lon - warehouse['lon'])**2)**0.5 * 111
            if distance < min_distance:
                min_distance = distance
                nearest_hub = warehouse
        
        if nearest_hub:
            # Add first mile route
            folium.PolyLine(
                locations=[
                    [hub_lat, hub_lon],
                    [nearest_hub['lat'], nearest_hub['lon']]
                ],
                color='blue',
                weight=3,
                opacity=0.7,
                popup=f"Collection: {hub['pickup']} → IF Hub {nearest_hub['id']}<br>Distance: {min_distance:.1f} km<br>Frequency: 4-6 times daily",
                tooltip=f"🚚 Collection Route ({min_distance:.1f} km)"
            ).add_to(collection_layer)
    
    # Hub-to-Feeder Routes
    for feeder_wh in feeder_warehouses:
        parent_hub = next((wh for wh in big_warehouses if wh['id'] == feeder_wh['parent']), None)
        if parent_hub:
            # Add hub-feeder connection
            route_popup = f"Hub-Feeder Link<br>IF Hub {parent_hub['id']} ↔ Feeder {feeder_wh['id']}<br>Distance: {feeder_wh['distance_to_parent']:.1f} km<br>Capacity: {feeder_wh['capacity']} orders/day<br>Frequency: 6-8 shuttles daily<br>Role: Bulk transfer & replenishment"
            
            folium.PolyLine(
                locations=[
                    [parent_hub['lat'], parent_hub['lon']],
                    [feeder_wh['lat'], feeder_wh['lon']]
                ],
                color='green',
                weight=4,
                opacity=0.9,
                popup=route_popup,
                tooltip=f"🔗 Hub-Feeder Link ({feeder_wh['distance_to_parent']:.1f} km)"
            ).add_to(auxiliary_layer)
            
            # Add directional arrow marker
            mid_lat = (parent_hub['lat'] + feeder_wh['lat']) / 2
            mid_lon = (parent_hub['lon'] + feeder_wh['lon']) / 2
            
            folium.Marker(
                location=[mid_lat, mid_lon],
                icon=folium.DivIcon(
                    html='<div style="color: green; font-size: 20px;">⬌</div>',
                    icon_size=(20, 20),
                    icon_anchor=(10, 10)
                )
            ).add_to(auxiliary_layer)
    
    # Inter-Hub Relay System
    if len(big_warehouses) > 1:
        for i, hub1 in enumerate(big_warehouses):
            for j, hub2 in enumerate(big_warehouses):
                if i < j:  # Avoid duplicate routes
                    distance = ((hub1['lat'] - hub2['lat'])**2 + (hub1['lon'] - hub2['lon'])**2)**0.5 * 111
                    
                    # Get hub codes for better display
                    hub1_code = hub1.get('hub_code', f"HUB{hub1['id']}")
                    hub2_code = hub2.get('hub_code', f"HUB{hub2['id']}")
                    
                    relay_popup = f"<b>Inter-Hub Relay Network</b><br>{hub1_code} ↔ {hub2_code}<br>Distance: {distance:.1f} km<br>Purpose: Cross-hub order routing<br>Frequency: 2 trips daily<br>Capacity: 120-400 orders per trip<br>Enables: {hub1_code} pickups → {hub2_code} delivery<br>Vehicle: Auto/Mini Truck based on distance"
                    
                    folium.PolyLine(
                        locations=[
                            [hub1['lat'], hub1['lon']],
                            [hub2['lat'], hub2['lon']]
                        ],
                        color='purple',
                        weight=4,
                        opacity=0.7,
                        popup=relay_popup,
                        tooltip=f"🔄 {hub1_code} ↔ {hub2_code} ({distance:.1f} km)"
                    ).add_to(interhub_layer)
                    
                    # Add relay marker
                    mid_lat = (hub1['lat'] + hub2['lat']) / 2
                    mid_lon = (hub1['lon'] + hub2['lon']) / 2
                    
                    folium.Marker(
                        location=[mid_lat, mid_lon],
                        icon=folium.DivIcon(
                            html='<div style="background: purple; color: white; border-radius: 50%; width: 25px; height: 25px; text-align: center; line-height: 25px; font-size: 12px; font-weight: bold;">R</div>',
                            icon_size=(25, 25),
                            icon_anchor=(12, 12)
                        )
                    ).add_to(interhub_layer)
    
    # Add all separate route layers to the map
    collection_layer.add_to(m)
    auxiliary_layer.add_to(m) 
    interhub_layer.add_to(m)
