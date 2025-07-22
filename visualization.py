import folium
from warehouse_logic import find_order_density_clusters, place_feeder_warehouses_near_clusters, calculate_big_warehouse_locations, create_comprehensive_feeder_network
import pandas as pd

def create_warehouse_network(df_filtered, m, min_cluster_size, max_distance_from_big, delivery_radius=2):
    """Create the complete warehouse network on the map"""
    
    # Calculate big warehouse locations
    big_warehouse_centers, big_warehouse_count = calculate_big_warehouse_locations(df_filtered)
    
    # Create warehouse network layer
    warehouse_layer = folium.FeatureGroup(name=f"🏭 Blowhorn IF Network ({big_warehouse_count} hubs + feeders | {delivery_radius}km radius)")
    
    big_warehouses = []
    
    # Place IF Hub warehouses
    for i, center in enumerate(big_warehouse_centers):
        lat, lon = center[0], center[1]
        
        # Count orders served by this hub warehouse
        orders_served = 0
        for _, row in df_filtered.iterrows():
            distance = ((row['order_lat'] - lat)**2 + (row['order_long'] - lon)**2)**0.5 * 111
            if distance <= 8:  # 8km radius for hub warehouse
                orders_served += 1
        
        big_warehouses.append({
            'id': i+1,
            'lat': lat,
            'lon': lon,
            'orders': orders_served,
            'capacity': 500,
            'type': 'hub'
        })
        
        # Add hub warehouse marker
        hub_popup = f"Blowhorn IF Hub {i+1}<br>Type: Central Distribution Hub<br>Size: 1000-1500 sqft<br>Daily Capacity: 500 orders<br>Current Orders: {orders_served}<br>Utilization: {(orders_served/500)*100:.1f}%<br>Coverage: 8km radius<br>Monthly Rent: ₹35,000<br>Role: Primary sorting & relay coordination"
        
        folium.Marker(
            location=[lat, lon],
            popup=hub_popup,
            tooltip=f"🏭 Blowhorn IF Hub {i+1} - {orders_served} orders",
            icon=folium.Icon(color='red', icon='industry', prefix='fa')
        ).add_to(warehouse_layer)
        
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
        ).add_to(warehouse_layer)
    
    # Create comprehensive feeder network
    feeder_warehouses, density_clusters = create_comprehensive_feeder_network(
        df_filtered, big_warehouses, min_cluster_size, max_distance_from_big, delivery_radius
    )
    
    # Add feeder warehouses to map
    for feeder_wh in feeder_warehouses:
        # Calculate actual orders within delivery radius
        orders_within_radius = 0
        for _, row in df_filtered.iterrows():
            distance = ((row['order_lat'] - feeder_wh['lat'])**2 + (row['order_long'] - feeder_wh['lon'])**2)**0.5 * 111
            if distance <= delivery_radius:
                orders_within_radius += 1
        
        feeder_wh['orders_within_radius'] = orders_within_radius
        
        # Icon color based on size category
        if feeder_wh['size_category'] == 'Large':
            icon_color = 'orange'
        elif feeder_wh['size_category'] == 'Medium':
            icon_color = 'lightred'
        else:
            icon_color = 'beige'
        
        # Create feeder popup text
        rent_amount = 12000 if feeder_wh['size_category'] == 'Small' else 15000 if feeder_wh['size_category'] == 'Medium' else 18000
        feeder_popup = f"Blowhorn IF Feeder {feeder_wh['id']}<br>Hub: IF Hub {feeder_wh['parent']}<br>Type: Last-mile Feeder Warehouse<br>Size: {feeder_wh['size_category']} (400-800 sqft)<br>Daily Capacity: {feeder_wh['capacity']} orders<br>Orders in cluster: {feeder_wh['orders']}<br>Orders within {delivery_radius}km: {orders_within_radius}<br>Utilization: {(orders_within_radius/feeder_wh['capacity'])*100:.1f}%<br>Distance to hub: {feeder_wh['distance_to_parent']:.1f}km<br>Delivery radius: {delivery_radius}km<br>Density score: {feeder_wh['density_score']:.1f} orders/km²<br>Monthly Rent: ₹{rent_amount:,}<br>Role: Local delivery dispatch"
        
        folium.Marker(
            location=[feeder_wh['lat'], feeder_wh['lon']],
            popup=feeder_popup,
            tooltip=f"📦 Blowhorn IF Feeder {feeder_wh['id']} - {orders_within_radius} orders ({delivery_radius}km)",
            icon=folium.Icon(color=icon_color, icon='cube', prefix='fa')
        ).add_to(warehouse_layer)
        
        # Add delivery radius coverage circle
        radius_meters = delivery_radius * 1000
        circle_color = 'orange' if delivery_radius <= 3 else 'yellow' if delivery_radius <= 5 else 'red'
        
        folium.Circle(
            location=[feeder_wh['lat'], feeder_wh['lon']],
            radius=radius_meters,
            popup=f"Blowhorn IF Feeder {feeder_wh['id']} - {delivery_radius}km Delivery Zone<br>{orders_within_radius} orders within range",
            tooltip=f"{delivery_radius}km delivery zone - {orders_within_radius} orders",
            color=circle_color,
            weight=2,
            fill=True,
            fillColor=circle_color,
            fillOpacity=0.15
        ).add_to(warehouse_layer)
    
    warehouse_layer.add_to(m)
    
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
    clusters_layer = folium.FeatureGroup(name="🎯 Order Density Clusters")
    
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
    """Create relay routes visualization on map"""
    routes_layer = folium.FeatureGroup(name="🚛 Blowhorn IF Relay Network")
    
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
            ).add_to(routes_layer)
    
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
            ).add_to(routes_layer)
            
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
            ).add_to(routes_layer)
    
    # Inter-Hub Relay System
    if len(big_warehouses) > 1:
        for i, hub1 in enumerate(big_warehouses):
            for j, hub2 in enumerate(big_warehouses):
                if i < j:  # Avoid duplicate routes
                    distance = ((hub1['lat'] - hub2['lat'])**2 + (hub1['lon'] - hub2['lon'])**2)**0.5 * 111
                    
                    relay_popup = f"Inter-Hub Relay<br>IF Hub {hub1['id']} ↔ IF Hub {hub2['id']}<br>Distance: {distance:.1f} km<br>Purpose: Load balancing & overflow<br>Frequency: 2-3 times daily<br>Capacity: 100-200 orders per transfer<br>Time: 45-60 minutes transit"
                    
                    folium.PolyLine(
                        locations=[
                            [hub1['lat'], hub1['lon']],
                            [hub2['lat'], hub2['lon']]
                        ],
                        color='purple',
                        weight=5,
                        opacity=0.8,
                        popup=relay_popup,
                        tooltip=f"🔄 Inter-Hub Relay ({distance:.1f} km)"
                    ).add_to(routes_layer)
                    
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
                    ).add_to(routes_layer)
    
    routes_layer.add_to(m)
