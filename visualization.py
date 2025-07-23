import folium
from warehouse_logic import find_order_density_clusters, place_feeder_warehouses_near_clusters, calculate_big_warehouse_locations, create_comprehensive_feeder_network
from pincode_warehouse_logic import create_pincode_based_network, add_pincode_feeder_visualization
import pandas as pd

def get_capacity_color(utilization_percent):
    """Get color based on capacity utilization percentage"""
    if utilization_percent <= 10:
        return '#2E8B57', '10%'  # Dark green
    elif utilization_percent <= 20:
        return '#32CD32', '20%'  # Lime green  
    elif utilization_percent <= 30:
        return '#9ACD32', '30%'  # Yellow green
    elif utilization_percent <= 40:
        return '#FFFF00', '40%'  # Yellow
    elif utilization_percent <= 50:
        return '#FFD700', '50%'  # Gold
    elif utilization_percent <= 60:
        return '#FFA500', '60%'  # Orange
    elif utilization_percent <= 70:
        return '#FF6347', '70%'  # Tomato
    elif utilization_percent <= 80:
        return '#FF4500', '80%'  # Orange red
    elif utilization_percent <= 90:
        return '#FF0000', '90%'  # Red
    else:
        return '#8B0000', '90%+'  # Dark red

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

def create_warehouse_network(df_filtered, m, min_cluster_size, max_distance_from_big, delivery_radius=2, show_coverage_circles=False, target_capacity=None):
    """Create the complete warehouse network on the map"""
    
    # Calculate big warehouse locations
    big_warehouse_centers, big_warehouse_count = calculate_big_warehouse_locations(df_filtered)
    
    # Calculate dynamic hub capacity based on actual warehouse dimensions
    # Using your warehouse data: orders per sqft capacity varies by warehouse efficiency
    # Average capacity: ~0.4 orders per sqft for efficient warehouse operations
    
    current_orders = len(df_filtered)
    
    # Warehouse dimension data from your table
    warehouse_specs = {
        'Banashankari': {'sqft': 450 * 11, 'capacity_per_sqft': 0.35},  # Smaller, less efficient
        'Chandra Layout': {'sqft': 800 * 11, 'capacity_per_sqft': 0.35},
        'Hebbal': {'sqft': 550 * 11, 'capacity_per_sqft': 0.35},
        'Koramangala': {'sqft': 0, 'capacity_per_sqft': 0.4},  # Spare vehicle used
        'Kudlu': {'sqft': 550 * 11, 'capacity_per_sqft': 0.35},
        'Mahadevapura': {'sqft': 1200 * 14, 'capacity_per_sqft': 0.4}  # Largest, most efficient
    }
    
    # Calculate average capacity per hub based on warehouse efficiency
    total_theoretical_capacity = sum([spec['sqft'] * spec['capacity_per_sqft'] for spec in warehouse_specs.values()])
    avg_warehouse_capacity = int(total_theoretical_capacity / len(warehouse_specs)) if len(warehouse_specs) > 0 else 600
    
    if target_capacity is not None and target_capacity > 0:
        hub_capacity = max(avg_warehouse_capacity, int(target_capacity / big_warehouse_count))
    else:
        hub_capacity = max(avg_warehouse_capacity, int(current_orders / big_warehouse_count * 1.2))
    
    # Create separate layers for hubs and auxiliaries (we'll update count later)
    hub_layer = folium.FeatureGroup(name=f"🏭 Main Warehouses ({big_warehouse_count})")
    auxiliary_warehouse_layer = folium.FeatureGroup(name="📦 Auxiliary Warehouses")
    
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
            'capacity': hub_capacity,
            'type': 'hub'
        })
        
        # Add hub warehouse marker with capacity color coding
        hub_capacity_utilization = (orders_served/hub_capacity)*100 if hub_capacity > 0 else 0
        
        # Use realistic main microwarehouse specifications
        from analytics import WAREHOUSE_SPECS
        main_wh_specs = WAREHOUSE_SPECS['main_microwarehouse']
        estimated_sqft = main_wh_specs['avg_size_sqft']  # Use standard 850 sqft
        estimated_rent = main_wh_specs['avg_monthly_rent']  # Use realistic ₹35k/month
        
        # Get capacity color
        capacity_color, capacity_label = get_capacity_color(hub_capacity_utilization)
        
        hub_popup = f"<b>{hub_code} Main Hub</b><br>📍 Geographic Zone: {hub_code}<br>🏢 Type: Main Microwarehouse ({main_wh_specs['size_range_sqft'][0]}-{main_wh_specs['size_range_sqft'][1]} sqft)<br>🏗️ Size: ~{estimated_sqft:,} sqft<br>⚡ Daily Capacity: {hub_capacity} orders<br>📊 Current Orders: {orders_served}<br>📈 Utilization: {hub_capacity_utilization:.1f}% ({capacity_label})<br>🎯 Coverage: 8km radius<br>💰 Monthly Rent: ₹{estimated_rent:,} ({main_wh_specs['monthly_rent_range'][0]:,}-{main_wh_specs['monthly_rent_range'][1]:,} range)<br>🔄 Role: Primary sorting & auxiliary coordination"
        
        # Create custom icon with capacity color
        folium.Marker(
            location=[lat, lon],
            popup=hub_popup,
            tooltip=f"🏭 {hub_code} Main | {capacity_label} utilized",
            icon=folium.DivIcon(
                html=f'<div style="background-color: {capacity_color}; border: 2px solid #000; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center;"><i class="fa fa-industry" style="color: white; font-size: 14px;"></i></div>',
                icon_size=(30, 30),
                icon_anchor=(15, 15)
            )
        ).add_to(hub_layer)
        
        # Remove the separate capacity indicator - info is available in popup/tooltip
        
        # Add coverage circle for hub warehouse (only if enabled)
        if show_coverage_circles:
            folium.Circle(
                location=[lat, lon],
                radius=8000,
                popup=f"Blowhorn IF Hub {i+1} Primary Coverage",
                color='red',
                weight=1,
                fill=True,
                fillColor='red',
                fillOpacity=0.05
            ).add_to(hub_layer)
    
    # Create pincode-based feeder network (no overlaps!) - always use grid-based for reliability
    # Always use grid-based system but with optimized parameters to reduce overlaps
    feeder_warehouses, density_clusters = create_comprehensive_feeder_network(
        df_filtered, big_warehouses, min_cluster_size, max_distance_from_big, delivery_radius
    )
    using_pincode_system = False  # Use grid system but optimize for minimal overlaps
    
    # Add feeder warehouses to map - always show auxiliary warehouses clearly  
    for feeder_wh in feeder_warehouses:
        # Calculate orders within coverage
        if 'coverage_orders' in feeder_wh:
            orders_within_radius = feeder_wh['coverage_orders']
        else:
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
        
        # Create auxiliary popup text with realistic sizing based on specifications
        aux_wh_specs = WAREHOUSE_SPECS['auxiliary_warehouse']
        estimated_aux_sqft = aux_wh_specs['avg_size_sqft']  # Use standard 350 sqft
        rent_amount = aux_wh_specs['avg_monthly_rent']  # Use realistic ₹15k/month
        vehicle_assigned = feeder_wh.get('vehicle_assigned', 'Mini Truck')
        capacity_utilization = (orders_within_radius / feeder_wh['capacity']) * 100 if feeder_wh['capacity'] > 0 else 0
        aux_popup = f"<b>{aux_name} Auxiliary Hub</b><br>📍 Parent Hub: {hub_code}<br>📦 Type: Auxiliary Warehouse ({aux_wh_specs['size_range_sqft'][0]}-{aux_wh_specs['size_range_sqft'][1]} sqft)<br>🏢 Size: ~{estimated_aux_sqft:,} sqft<br>⚡ Daily Capacity: {feeder_wh['capacity']} orders<br>📊 Current Orders: {orders_within_radius}<br>📈 Utilization: {capacity_utilization:.1f}%<br>🛣️ Distance to Hub: {feeder_wh['distance_to_parent']:.1f}km<br>🚛 Vehicle: {vehicle_assigned}<br>💰 Monthly Rent: ₹{rent_amount:,} ({aux_wh_specs['monthly_rent_range'][0]:,}-{aux_wh_specs['monthly_rent_range'][1]:,} range)"
        
        # Get capacity color for auxiliary warehouse
        aux_capacity_color, aux_capacity_label = get_capacity_color(capacity_utilization)
        
        # Add auxiliary warehouse icon with capacity color coding
        folium.Marker(
            location=[feeder_wh['lat'], feeder_wh['lon']],
            popup=aux_popup,
            tooltip=f"📦 {aux_name} | {aux_capacity_label} utilized",
            icon=folium.DivIcon(
                html=f'<div style="background-color: {aux_capacity_color}; border: 2px solid #000; border-radius: 3px; width: 25px; height: 25px; display: flex; align-items: center; justify-content: center;"><i class="fa fa-warehouse" style="color: white; font-size: 12px;"></i></div>',
                icon_size=(25, 25),
                icon_anchor=(12, 12)
            )
        ).add_to(auxiliary_warehouse_layer)
        
        # Add connection line to parent hub with capacity color coding
        parent_hub = next((wh for wh in big_warehouses if wh['id'] == feeder_wh['parent']), None)
        if parent_hub:
            # Extract hub code to avoid nested f-string issues
            parent_hub_code = parent_hub.get('hub_code', f"HUB{parent_hub['id']}")
            
            # Calculate route capacity utilization (based on auxiliary capacity)
            route_capacity_util = capacity_utilization
            route_color, route_capacity_label = get_capacity_color(route_capacity_util)
            
            folium.PolyLine(
                locations=[
                    [parent_hub['lat'], parent_hub['lon']],
                    [feeder_wh['lat'], feeder_wh['lon']]
                ],
                color=route_color,
                weight=3,
                opacity=0.8,
                dash_array='5, 5',
                popup=f"Hub-Auxiliary Route: {parent_hub_code} → {aux_name}<br>Distance: {feeder_wh['distance_to_parent']:.1f}km<br>Route Capacity: {feeder_wh['capacity']} orders/day<br>Current Flow: {orders_within_radius} orders<br>Utilization: {route_capacity_util:.1f}% ({route_capacity_label})",
                tooltip=f"🔗 {parent_hub_code} → {aux_name} | {route_capacity_label} utilized"
            ).add_to(auxiliary_warehouse_layer)
        
        # Add delivery radius coverage circle (only if enabled)
        if show_coverage_circles:
            radius_meters = delivery_radius * 1000
            circle_color = 'orange' if delivery_radius <= 3 else 'yellow' if delivery_radius <= 5 else 'red'
            
            folium.Circle(
                location=[feeder_wh['lat'], feeder_wh['lon']],
                radius=radius_meters,
                popup=f"Auxiliary {feeder_wh['id']} - {delivery_radius}km Delivery Zone<br>{orders_within_radius} orders within range",
                tooltip=f"{delivery_radius}km delivery zone - {orders_within_radius} orders",
                color=circle_color,
                weight=1,
                fill=True,
                fillColor=circle_color,
                fillOpacity=0.08
            ).add_to(auxiliary_warehouse_layer)
    
    # Update auxiliary layer name with actual count and add both layers to the map
    auxiliary_count = len(feeder_warehouses)
    auxiliary_warehouse_layer.name = f"📦 Auxiliary Warehouses ({auxiliary_count})"
    
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

def create_relay_routes(m, df_filtered, big_warehouses, feeder_warehouses, show_collection=True, show_hub_auxiliary=True, show_interhub=True):
    """Create separate relay routes visualization layers on map"""
    
    # Create separate layers for different route types (only if requested)
    if show_collection:
        collection_layer = folium.FeatureGroup(name="🚚 Collection Routes")
    if show_hub_auxiliary:
        auxiliary_layer = folium.FeatureGroup(name="🔗 Hub-Auxiliary Routes") 
    if show_interhub:
        interhub_layer = folium.FeatureGroup(name="🔄 Inter-Hub Relays")
    
    # First Mile: Customer pickups to nearest hub warehouse (only if requested)
    if show_collection:
        # Get pickup hubs data
        pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
        
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
                # Calculate trip details for this route
                trips_per_day = min(6, max(4, hub['order_count'] // 20))  # 4-6 trips based on volume
                orders_per_trip = hub['order_count'] / trips_per_day if trips_per_day > 0 else 0
                
                # Determine vehicle type based on volume and distance
                if orders_per_trip <= 60 and min_distance <= 15:
                    vehicle_type = "Auto"
                    trip_cost = 900
                elif orders_per_trip <= 120:
                    vehicle_type = "Mini Truck"
                    trip_cost = 1350
                else:
                    vehicle_type = "Truck"
                    trip_cost = 1800
                
                daily_cost = trips_per_day * trip_cost
                monthly_cost = daily_cost * 30
                cost_per_order = daily_cost / hub['order_count'] if hub['order_count'] > 0 else 0
                
                # Enhanced popup with cost and trip details
                detailed_popup = f"""
                <b>First Mile Collection Route</b><br>
                <b>From:</b> {hub['pickup']}<br>
                <b>To:</b> IF Hub {nearest_hub['id']}<br>
                <b>Distance:</b> {min_distance:.1f} km<br>
                <b>Daily Orders:</b> {hub['order_count']}<br>
                <b>Vehicle:</b> {vehicle_type}<br>
                <b>Trips/Day:</b> {trips_per_day}<br>
                <b>Orders/Trip:</b> {orders_per_trip:.0f}<br>
                <b>Daily Cost:</b> ₹{daily_cost:,.0f}<br>
                <b>Monthly Cost:</b> ₹{monthly_cost:,.0f}<br>
                <b>Cost/Order:</b> ₹{cost_per_order:.1f}
                """
                
                # Add first mile route with enhanced details
                folium.PolyLine(
                    locations=[
                        [hub_lat, hub_lon],
                        [nearest_hub['lat'], nearest_hub['lon']]
                    ],
                    color='blue',
                    weight=max(2, min(6, trips_per_day)),  # Line weight based on trip frequency
                    opacity=0.7,
                    popup=detailed_popup,
                    tooltip=f"🚚 {trips_per_day} trips/day • ₹{cost_per_order:.1f}/order"
                ).add_to(collection_layer)
    
    # Hub-to-Auxiliary Routes (only if requested)
    if show_hub_auxiliary:
        for feeder_wh in feeder_warehouses:
            parent_hub = next((wh for wh in big_warehouses if wh['id'] == feeder_wh['parent']), None)
            if parent_hub:
                # Get vehicle assignment and trip details from analytics
                vehicle_assigned = feeder_wh.get('vehicle_assigned', 'mini_truck')  # Fixed: use underscore format
                current_orders = feeder_wh.get('orders_within_radius', feeder_wh.get('coverage_orders', 0))
                capacity = feeder_wh['capacity']
                
                # Calculate trips based on vehicle capacity and current orders
                from analytics import VEHICLE_SPECS, VEHICLE_COSTS
                
                # Ensure vehicle_assigned is in correct format (with underscores)
                vehicle_key = vehicle_assigned.lower().replace(' ', '_')
                if vehicle_key not in VEHICLE_SPECS:
                    vehicle_key = 'mini_truck'  # Default fallback
                    
                vehicle_capacity = VEHICLE_SPECS[vehicle_key]['practical_mixed_capacity']
                trips_per_day = max(1, min(8, (current_orders + capacity) // vehicle_capacity))
                trip_cost = VEHICLE_COSTS[vehicle_key]
                
                daily_cost = trips_per_day * trip_cost
                monthly_cost = daily_cost * 30
                cost_per_order = daily_cost / max(1, current_orders) if current_orders > 0 else daily_cost
                
                # Get hub and auxiliary names
                hub_code = parent_hub.get('hub_code', f"HUB{parent_hub['id']}")
                aux_name = feeder_wh.get('aux_name', f"AX{feeder_wh['id']}")
                
                # Enhanced popup with comprehensive details
                vehicle_display_name = vehicle_key.replace('_', ' ').title()
                route_popup = f"""
                <b>Middle Mile Distribution Route</b><br>
                <b>From:</b> {hub_code} Main Hub<br>
                <b>To:</b> {aux_name} Auxiliary<br>
                <b>Distance:</b> {feeder_wh['distance_to_parent']:.1f} km<br>
                <b>Current Orders:</b> {current_orders}<br>
                <b>Auxiliary Capacity:</b> {capacity} orders/day<br>
                <b>Vehicle:</b> {vehicle_display_name}<br>
                <b>Vehicle Capacity:</b> {vehicle_capacity} orders/trip<br>
                <b>Trips/Day:</b> {trips_per_day}<br>
                <b>Daily Cost:</b> ₹{daily_cost:,.0f}<br>
                <b>Monthly Cost:</b> ₹{monthly_cost:,.0f}<br>
                <b>Cost/Order:</b> ₹{cost_per_order:.1f}<br>
                <b>Role:</b> Hub sorting → Last mile distribution
                """
                
                folium.PolyLine(
                    locations=[
                        [parent_hub['lat'], parent_hub['lon']],
                        [feeder_wh['lat'], feeder_wh['lon']]
                    ],
                    color='green',
                    weight=max(2, min(6, trips_per_day)),  # Line weight based on trip frequency
                    opacity=0.9,
                    popup=route_popup,
                    tooltip=f"🔗 {trips_per_day} trips/day • ₹{cost_per_order:.1f}/order"
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
    
    # Inter-Hub Relay System (only if requested)
    if show_interhub and len(big_warehouses) > 1:
        for i, hub1 in enumerate(big_warehouses):
            for j, hub2 in enumerate(big_warehouses):
                if i < j:  # Avoid duplicate routes
                    distance = ((hub1['lat'] - hub2['lat'])**2 + (hub1['lon'] - hub2['lon'])**2)**0.5 * 111
                    
                    # Get hub codes for better display
                    hub1_code = hub1.get('hub_code', f"HUB{hub1['id']}")
                    hub2_code = hub2.get('hub_code', f"HUB{hub2['id']}")
                    
                    # Determine vehicle and cost based on distance
                    from analytics import VEHICLE_COSTS
                    if distance <= 15:
                        relay_vehicle = "auto"
                        trips_per_day = 3
                    elif distance <= 25:
                        relay_vehicle = "mini_truck"
                        trips_per_day = 2
                    else:
                        relay_vehicle = "truck"
                        trips_per_day = 2
                    
                    trip_cost = VEHICLE_COSTS[relay_vehicle]
                    daily_cost = trips_per_day * trip_cost
                    monthly_cost = daily_cost * 30
                    
                    # Estimate order flow based on hub capacities
                    avg_hub_capacity = (hub1.get('capacity', 500) + hub2.get('capacity', 500)) / 2
                    estimated_daily_flow = min(100, avg_hub_capacity * 0.1)  # 10% cross-hub flow
                    cost_per_order = daily_cost / max(1, estimated_daily_flow)
                    
                    relay_popup = f"""
                    <b>Inter-Hub Relay Network</b><br>
                    <b>Route:</b> {hub1_code} ↔ {hub2_code}<br>
                    <b>Distance:</b> {distance:.1f} km<br>
                    <b>Vehicle:</b> {relay_vehicle.replace('_', ' ').title()}<br>
                    <b>Trips/Day:</b> {trips_per_day}<br>
                    <b>Est. Daily Flow:</b> {estimated_daily_flow:.0f} orders<br>
                    <b>Daily Cost:</b> ₹{daily_cost:,.0f}<br>
                    <b>Monthly Cost:</b> ₹{monthly_cost:,.0f}<br>
                    <b>Cost/Order:</b> ₹{cost_per_order:.1f}<br>
                    <b>Purpose:</b> Cross-hub order routing & load balancing<br>
                    <b>Enables:</b> {hub1_code} pickups → {hub2_code} delivery
                    """
                    
                    folium.PolyLine(
                        locations=[
                            [hub1['lat'], hub1['lon']],
                            [hub2['lat'], hub2['lon']]
                        ],
                        color='purple',
                        weight=max(2, min(5, trips_per_day)),  # Line weight based on trip frequency
                        opacity=0.7,
                        popup=relay_popup,
                        tooltip=f"🔄 {trips_per_day} trips/day • ₹{cost_per_order:.1f}/order"
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
    
    # Add separate route layers to the map (only if they were created)
    if show_collection:
        collection_layer.add_to(m)
    if show_hub_auxiliary:
        auxiliary_layer.add_to(m) 
    if show_interhub:
        interhub_layer.add_to(m)
