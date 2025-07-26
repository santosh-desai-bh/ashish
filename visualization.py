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

def create_warehouse_network(df_filtered, m, max_distance_from_big, delivery_radius=2, show_coverage_circles=False, target_capacity=None):
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
    coverage_layer = folium.FeatureGroup(name="📍 Warehouse Coverage Areas", show=False)
    
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
        
        # Create simple hub popup without vehicle count (will be updated later)
        hub_popup = f"<b>{hub_code} Main Hub</b><br>📍 Geographic Zone: {hub_code}<br>⚡ Daily Capacity: {hub_capacity} orders<br>📊 Current Orders: {orders_served}<br>🔄 Role: Primary sorting & auxiliary coordination"
        
        # Create simple icon without utilization color coding
        folium.Marker(
            location=[lat, lon],
            popup=hub_popup,
            tooltip=f"🏭 {hub_code} Main Hub",
            icon=folium.DivIcon(
                html=f'<div style="background-color: #4169E1; border: 2px solid #000; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center;"><i class="fa fa-industry" style="color: white; font-size: 14px;"></i></div>',
                icon_size=(30, 30),
                icon_anchor=(15, 15)
            )
        ).add_to(hub_layer)
        
        # Remove the separate capacity indicator - info is available in popup/tooltip
        
        # Coverage circles removed - network connections show relationships
    
    # Create pincode-based feeder network (no overlaps!) - always use grid-based for reliability
    # Always use grid-based system but with optimized parameters to reduce overlaps
    feeder_warehouses, density_clusters = create_comprehensive_feeder_network(
        df_filtered, big_warehouses, max_distance_from_big, delivery_radius
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
        
        # Create simple auxiliary popup without vehicle count (will be updated later)
        aux_popup = f"<b>{aux_name} Auxiliary Hub</b><br>📍 Parent Hub: {hub_code}<br>📊 Current Orders: {orders_within_radius}<br>⚡ Daily Capacity: {feeder_wh['capacity']} orders"
        
        # Add auxiliary warehouse icon without utilization color coding
        folium.Marker(
            location=[feeder_wh['lat'], feeder_wh['lon']],
            popup=aux_popup,
            tooltip=f"📦 {aux_name} Auxiliary",
            icon=folium.DivIcon(
                html=f'<div style="background-color: #FF6347; border: 2px solid #000; border-radius: 3px; width: 25px; height: 25px; display: flex; align-items: center; justify-content: center;"><i class="fa fa-warehouse" style="color: white; font-size: 12px;"></i></div>',
                icon_size=(25, 25),
                icon_anchor=(12, 12)
            )
        ).add_to(auxiliary_warehouse_layer)
        
        # Add connection line to parent hub with capacity color coding
        parent_hub = next((wh for wh in big_warehouses if wh['id'] == feeder_wh['parent']), None)
        if parent_hub:
            # Extract hub code to avoid nested f-string issues
            parent_hub_code = parent_hub.get('hub_code', f"HUB{parent_hub['id']}")
            
            # Simple connection line without utilization color coding
            folium.PolyLine(
                locations=[
                    [parent_hub['lat'], parent_hub['lon']],
                    [feeder_wh['lat'], feeder_wh['lon']]
                ],
                color='#666666',  # Simple gray color
                weight=2,
                opacity=0.6,
                dash_array='5, 5',
                popup=f"Hub-Auxiliary Route: {parent_hub_code} → {aux_name}<br>Distance: {feeder_wh['distance_to_parent']:.1f}km<br>Route Capacity: {feeder_wh['capacity']} orders/day<br>Current Flow: {orders_within_radius} orders",
                tooltip=f"🔗 {parent_hub_code} → {aux_name}"
            ).add_to(auxiliary_warehouse_layer)
        
        # Coverage circles removed - replaced with connection lines
    
    # Update auxiliary layer name with actual count and add both layers to the map
    auxiliary_count = len(feeder_warehouses)
    auxiliary_warehouse_layer.name = f"📦 Auxiliary Warehouses ({auxiliary_count})"
    
    hub_layer.add_to(m)
    auxiliary_warehouse_layer.add_to(m)
    
    # Add auxiliary-to-main hub connection lines
    add_auxiliary_hub_connections(m, feeder_warehouses, big_warehouses)
    
    # Add optional interhub connections
    add_interhub_connections(m, big_warehouses)
    
    # Calculate tiered coverage statistics (2km, 3km, 5km, >5km)
    total_orders = len(df_filtered)
    coverage_tiers = {
        '2km': 0,
        '3km': 0, 
        '5km': 0,
        '>5km': 0
    }
    
    for _, order in df_filtered.iterrows():
        order_lat, order_lon = order['order_lat'], order['order_long']
        
        # Find minimum distance to any warehouse (main or auxiliary)
        min_distance = float('inf')
        
        # Check distance to main warehouses
        for main_wh in big_warehouses:
            distance = ((order_lat - main_wh['lat'])**2 + (order_lon - main_wh['lon'])**2)**0.5 * 111
            min_distance = min(min_distance, distance)
        
        # Check distance to auxiliary warehouses
        for aux_wh in feeder_warehouses:
            distance = ((order_lat - aux_wh['lat'])**2 + (order_lon - aux_wh['lon'])**2)**0.5 * 111
            min_distance = min(min_distance, distance)
        
        # Categorize by closest warehouse distance
        if min_distance <= 2:
            coverage_tiers['2km'] += 1
        elif min_distance <= 3:
            coverage_tiers['3km'] += 1
        elif min_distance <= 5:
            coverage_tiers['5km'] += 1
        else:
            coverage_tiers['>5km'] += 1
    
    # Store coverage analysis for use in main.py
    coverage_analysis = {
        'total_orders': total_orders,
        'tiers': coverage_tiers,
        'percentages': {tier: (count / total_orders) * 100 if total_orders > 0 else 0 
                      for tier, count in coverage_tiers.items()}
    }
    
    print(f"Tiered Coverage Analysis:")
    print(f"  ≤2km: {coverage_tiers['2km']} orders ({coverage_analysis['percentages']['2km']:.1f}%)")
    print(f"  ≤3km: {coverage_tiers['3km']} orders ({coverage_analysis['percentages']['3km']:.1f}%)")
    print(f"  ≤5km: {coverage_tiers['5km']} orders ({coverage_analysis['percentages']['5km']:.1f}%)")
    print(f"  >5km: {coverage_tiers['>5km']} orders ({coverage_analysis['percentages']['>5km']:.1f}%)")
    
    return big_warehouses, feeder_warehouses, density_clusters, coverage_analysis

def update_warehouse_markers_with_vehicles(m, big_warehouses, feeder_warehouses, last_mile_assignments):
    """Update warehouse markers to show last mile vehicle counts instead of utilization"""
    
    # Create a new layer for updated warehouse markers with vehicle info
    updated_hub_layer = folium.FeatureGroup(name=f"🏭 Main Warehouses with Vehicles ({len(big_warehouses)})")
    updated_aux_layer = folium.FeatureGroup(name=f"📦 Auxiliary Warehouses with Vehicles ({len(feeder_warehouses)})")
    
    # Update main hub markers
    for hub in big_warehouses:
        hub_vehicles = {'autos': 0, 'bikes': 0}
        
        # Calculate vehicles for this hub (from its auxiliaries)
        for assignment in last_mile_assignments:
            aux_info = next((aux for aux in feeder_warehouses if aux.get('id') == assignment.get('auxiliary_id')), None)
            if aux_info and aux_info.get('parent') == hub['id']:
                hub_vehicles['autos'] += assignment.get('auto_vehicles', 0)
                hub_vehicles['bikes'] += assignment.get('bike_vehicles', 0)
        
        total_hub_vehicles = hub_vehicles['autos'] + hub_vehicles['bikes']
        hub_code = hub.get('hub_code', f"HUB{hub['id']}")
        
        # Updated popup with vehicle information
        hub_popup = f"<b>{hub_code} Main Hub</b><br>📍 Geographic Zone: {hub_code}<br>⚡ Daily Capacity: {hub['capacity']} orders<br>📊 Current Orders: {hub['orders']}<br>🚛 LM Vehicles: {total_hub_vehicles} ({hub_vehicles['autos']}🛺 + {hub_vehicles['bikes']}🏍️)<br>🔄 Can deliver directly from hub"
        
        folium.Marker(
            location=[hub['lat'], hub['lon']],
            popup=hub_popup,
            tooltip=f"🏭 {hub_code} | {total_hub_vehicles} vehicles",
            icon=folium.DivIcon(
                html=f'<div style="background-color: #4169E1; border: 2px solid #000; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; position: relative;"><i class="fa fa-industry" style="color: white; font-size: 14px;"></i><span style="position: absolute; top: -8px; right: -8px; background: #FFD700; color: black; border-radius: 50%; width: 16px; height: 16px; font-size: 10px; font-weight: bold; display: flex; align-items: center; justify-content: center;">{total_hub_vehicles}</span></div>',
                icon_size=(30, 30),
                icon_anchor=(15, 15)
            )
        ).add_to(updated_hub_layer)
    
    # Update auxiliary markers
    for aux in feeder_warehouses:
        aux_vehicles = {'autos': 0, 'bikes': 0}
        
        # Find vehicles for this auxiliary
        for assignment in last_mile_assignments:
            if assignment.get('auxiliary_id') == aux['id']:
                aux_vehicles['autos'] = assignment.get('auto_vehicles', 0)
                aux_vehicles['bikes'] = assignment.get('bike_vehicles', 0)
                break
        
        total_aux_vehicles = aux_vehicles['autos'] + aux_vehicles['bikes']
        aux_name = aux.get('aux_name', f"AX{aux['id']}")
        hub_code = aux.get('hub_code', f"HUB{aux['parent']}")
        
        # Updated popup with vehicle information  
        aux_popup = f"<b>{aux_name} Auxiliary Hub</b><br>📍 Parent Hub: {hub_code}<br>📊 Current Orders: {aux.get('orders_within_radius', 0)}<br>⚡ Daily Capacity: {aux['capacity']} orders<br>🚛 LM Vehicles: {total_aux_vehicles} ({aux_vehicles['autos']}🛺 + {aux_vehicles['bikes']}🏍️)<br>🔄 Can deliver directly from auxiliary"
        
        folium.Marker(
            location=[aux['lat'], aux['lon']],
            popup=aux_popup,
            tooltip=f"📦 {aux_name} | {total_aux_vehicles} vehicles",
            icon=folium.DivIcon(
                html=f'<div style="background-color: #FF6347; border: 2px solid #000; border-radius: 3px; width: 25px; height: 25px; display: flex; align-items: center; justify-content: center; position: relative;"><i class="fa fa-warehouse" style="color: white; font-size: 12px;"></i><span style="position: absolute; top: -8px; right: -8px; background: #FFD700; color: black; border-radius: 50%; width: 14px; height: 14px; font-size: 9px; font-weight: bold; display: flex; align-items: center; justify-content: center;">{total_aux_vehicles}</span></div>',
                icon_size=(25, 25),
                icon_anchor=(12, 12)
            )
        ).add_to(updated_aux_layer)
    
    # Add updated layers to map
    updated_hub_layer.add_to(m)
    updated_aux_layer.add_to(m)

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

def add_pincode_coverage_areas(m, feeder_warehouses, big_warehouses):
    """Add pincode-based coverage areas instead of circles to eliminate overlaps"""
    
    try:
        from pincode_warehouse_logic import load_pincode_boundaries
        
        # Load pincode boundaries
        pincode_boundaries = load_pincode_boundaries()
        if not pincode_boundaries:
            print("⚠️ No pincode boundaries available, keeping circle coverage")
            return
        
        # Create pincode coverage layer
        pincode_coverage_layer = folium.FeatureGroup(name="🗺️ Pincode Coverage Areas", show=False)
        
        # Add coverage for auxiliary warehouses (these have pincode assignments)
        for feeder in feeder_warehouses:
            if 'pincode' in feeder and feeder['pincode'] in pincode_boundaries:
                pincode = feeder['pincode']
                boundary_data = pincode_boundaries[pincode]
                polygon = boundary_data['polygon']
                area_name = boundary_data['area_name']
                
                # Convert polygon to coordinates for folium
                if hasattr(polygon, 'exterior'):
                    coords = list(polygon.exterior.coords)
                    
                    # Determine color based on auxiliary capacity
                    capacity = feeder.get('capacity', 200)
                    if capacity >= 300:
                        color = 'darkgreen'
                        fill_color = 'lightgreen'
                    elif capacity >= 200:
                        color = 'orange'
                        fill_color = 'lightyellow'
                    else:
                        color = 'red'
                        fill_color = 'lightcoral'
                    
                    orders_served = feeder.get('orders_within_radius', feeder.get('orders', 0))
                    utilization = (orders_served / capacity * 100) if capacity > 0 else 0
                    
                    folium.Polygon(
                        locations=[(lat, lon) for lon, lat in coords],
                        popup=f"<b>Auxiliary Coverage Area</b><br><b>Pincode:</b> {pincode}<br><b>Area:</b> {area_name}<br><b>Warehouse ID:</b> AX{feeder['id']}<br><b>Capacity:</b> {capacity} orders/day<br><b>Current Orders:</b> {orders_served}<br><b>Utilization:</b> {utilization:.1f}%<br><b>Coverage:</b> Exact pincode boundary",
                        tooltip=f"📦 {pincode} - AX{feeder['id']} ({orders_served}/{capacity} orders)",
                        color=color,
                        weight=2,
                        fill=True,
                        fillColor=fill_color,
                        fillOpacity=0.15
                    ).add_to(pincode_coverage_layer)
        
        # Add main warehouse coverage areas (approximate based on nearby pincodes)
        covered_pincodes = set(f.get('pincode') for f in feeder_warehouses if f.get('pincode'))
        
        # For main warehouses, show remaining uncovered pincodes in their vicinity
        for big_wh in big_warehouses:
            hub_lat, hub_lon = big_wh['lat'], big_wh['lon']
            hub_code = big_wh.get('hub_code', f"HUB{big_wh['id']}")
            
            # Find nearby pincodes not covered by auxiliaries
            nearby_uncovered = []
            for pincode, boundary_data in pincode_boundaries.items():
                if pincode not in covered_pincodes:
                    centroid = boundary_data['centroid']
                    # Check if within ~10km of main warehouse
                    distance = ((hub_lat - centroid.y)**2 + (hub_lon - centroid.x)**2)**0.5 * 111
                    if distance <= 10:  # 10km radius for main warehouse coverage
                        nearby_uncovered.append((pincode, boundary_data, distance))
            
            # Add the closest uncovered pincodes to main warehouse coverage
            nearby_uncovered.sort(key=lambda x: x[2])  # Sort by distance
            
            for pincode, boundary_data, distance in nearby_uncovered[:8]:  # Max 8 pincodes per main warehouse
                polygon = boundary_data['polygon']
                area_name = boundary_data['area_name']
                
                if hasattr(polygon, 'exterior'):
                    coords = list(polygon.exterior.coords)
                    
                    folium.Polygon(
                        locations=[(lat, lon) for lon, lat in coords],
                        popup=f"<b>Main Warehouse Coverage</b><br><b>Pincode:</b> {pincode}<br><b>Area:</b> {area_name}<br><b>Hub:</b> {hub_code}<br><b>Distance:</b> {distance:.1f}km<br><b>Coverage:</b> Direct delivery from main warehouse<br><b>No auxiliary needed</b>",
                        tooltip=f"🏭 {pincode} - {hub_code} direct coverage ({distance:.1f}km)",
                        color='darkred',
                        weight=1,
                        fill=True,
                        fillColor='lightcoral',
                        fillOpacity=0.08
                    ).add_to(pincode_coverage_layer)
        
        pincode_coverage_layer.add_to(m)
        print(f"✅ Added pincode-based coverage areas for {len(feeder_warehouses)} auxiliaries")
        
    except Exception as e:
        print(f"⚠️ Could not load pincode boundaries: {e}")
        print("Keeping circle-based coverage as fallback")

def add_auxiliary_hub_connections(m, feeder_warehouses, big_warehouses):
    """Add connection lines from auxiliaries to their parent main hubs"""
    
    # Create auxiliary connections layer (visible by default to show hub assignments)
    connections_layer = folium.FeatureGroup(name="🔗 Auxiliary-Hub Assignments", show=True)
    
    for aux in feeder_warehouses:
        # Find parent hub
        parent_hub = None
        for hub in big_warehouses:
            if hub['id'] == aux['parent']:
                parent_hub = hub
                break
        
        if parent_hub:
            # Color coding based on auxiliary capacity/utilization
            capacity = aux.get('capacity', 200)
            orders = aux.get('orders', 0)
            utilization = (orders / capacity * 100) if capacity > 0 else 0
            
            if utilization >= 80:
                line_color = '#FF4444'  # Red - high utilization
                line_weight = 4
            elif utilization >= 60:
                line_color = '#FF8800'  # Orange - medium utilization
                line_weight = 3
            else:
                line_color = '#4CAF50'  # Green - low utilization
                line_weight = 2
            
            # Create connected auxiliary name format: ParentHub-AXid
            parent_code = parent_hub.get('hub_code', f"HUB{parent_hub['id']}")
            aux_connected_name = f"{parent_code}-AX{aux['id']}"
            
            # Create connection line with dotted style
            folium.PolyLine(
                locations=[
                    [parent_hub['lat'], parent_hub['lon']],
                    [aux['lat'], aux['lon']]
                ],
                color=line_color,
                weight=line_weight,
                opacity=0.8,
                dash_array='5, 5',  # Dotted line for auxiliary connections
                popup=f"<b>🏭→🏪 Hub Assignment</b><br><b>Main Hub:</b> {parent_code} ({parent_hub.get('hub_name', 'Main Hub')})<br><b>Auxiliary:</b> {aux_connected_name} ({aux.get('pincode', 'Unknown')})<br><b>Assignment Distance:</b> {aux.get('distance_to_parent', 0):.1f} km<br><b>Auxiliary Capacity:</b> {capacity} orders/day<br><b>Current Orders:</b> {orders}<br><b>Utilization:</b> {utilization:.1f}%<br><b>Service Area:</b> {aux.get('coverage_area', 'Local delivery')}<br><b>Assignment Logic:</b> Closest main hub for supply efficiency",
                tooltip=f"🏭 {parent_code} → 🏪 {aux_connected_name} | {utilization:.0f}% utilized"
            ).add_to(connections_layer)
    
    connections_layer.add_to(m)

def add_interhub_connections(m, big_warehouses):
    """Add interhub circuit routes based on realistic redistribution planning"""
    
    # Create interhub connections layer (hidden by default)
    interhub_layer = folium.FeatureGroup(name="🏭 Inter-Hub Relay Circuits", show=False)
    
    # Get realistic interhub vehicle assignments from calculate_interhub_vehicles
    from simple_analytics import calculate_interhub_vehicles
    total_vehicles, vehicle_assignments = calculate_interhub_vehicles(big_warehouses)
    
    # Create circuit-based connections instead of mesh network
    circuit_colors = ['#FF6B35', '#004E89', '#00A8CC', '#40BCD8', '#FFBE00']  # Different colors for each circuit
    
    for i, assignment in enumerate(vehicle_assignments):
        circuit_color = circuit_colors[i % len(circuit_colors)]
        circuit_name = assignment.get('circuit_name', f"Circuit {i+1}")
        vehicles_needed = assignment.get('vehicles_needed', 1)
        circuit_distance = assignment.get('circuit_distance', 0)
        redistribution_volume = assignment.get('redistribution_volume', 0)
        
        # Get hub codes from relay_route (backward compatibility)
        relay_route = assignment.get('relay_route', '')
        if relay_route:
            hub_codes = relay_route.split(' → ')
            hub_codes = [code.strip() for code in hub_codes if code.strip()]
            
            # Create circuit path by connecting consecutive hubs
            circuit_hubs = []
            for hub_code in hub_codes[:-1]:  # Exclude the last duplicate hub
                for hub in big_warehouses:
                    if hub.get('hub_code', f"HUB{hub['id']}") == hub_code:
                        circuit_hubs.append(hub)
                        break
            
            # Draw circuit connections
            for j in range(len(circuit_hubs)):
                current_hub = circuit_hubs[j]
                next_hub = circuit_hubs[(j + 1) % len(circuit_hubs)]  # Circular connection
                
                # Calculate segment distance
                segment_distance = ((current_hub['lat'] - next_hub['lat'])**2 + 
                                  (current_hub['lon'] - next_hub['lon'])**2)**0.5 * 111
                
                # Create directional circuit line
                folium.PolyLine(
                    locations=[
                        [current_hub['lat'], current_hub['lon']],
                        [next_hub['lat'], next_hub['lon']]
                    ],
                    color=circuit_color,
                    weight=4,
                    opacity=0.8,
                    dash_array='15, 5',  # Dashed line for circuit routes
                    popup=f"""<b>🚛 {circuit_name}</b><br>
                    <b>Route:</b> {current_hub.get('hub_code', 'HUB')} → {next_hub.get('hub_code', 'HUB')}<br>
                    <b>Vehicles:</b> {vehicles_needed} trucks<br>
                    <b>Segment Distance:</b> {segment_distance:.1f} km<br>
                    <b>Total Circuit:</b> {circuit_distance:.1f} km<br>
                    <b>Daily Volume:</b> {redistribution_volume} orders<br>
                    <b>Schedule:</b> 8:30 AM - 1:30 PM<br>
                    <b>Purpose:</b> Strategic redistribution for 4 PM last mile deadline""",
                    tooltip=f"🚛 {circuit_name} | {vehicles_needed} trucks | {redistribution_volume} orders/day"
                ).add_to(interhub_layer)
                
                # Add directional arrow marker at midpoint
                mid_lat = (current_hub['lat'] + next_hub['lat']) / 2
                mid_lon = (current_hub['lon'] + next_hub['lon']) / 2
                
                folium.Marker(
                    location=[mid_lat, mid_lon],
                    icon=folium.DivIcon(
                        html=f'<div style="color: {circuit_color}; font-size: 16px; text-shadow: 1px 1px 2px white;">→</div>',
                        icon_size=(20, 20),
                        icon_anchor=(10, 10)
                    ),
                    tooltip=f"Direction: {current_hub.get('hub_code', 'HUB')} → {next_hub.get('hub_code', 'HUB')}"
                ).add_to(interhub_layer)
    
    # Add circuit summary
    total_vehicles_count = sum([a.get('vehicles_needed', 0) for a in vehicle_assignments])
    circuit_summary = f"""
    <b>🚛 Interhub Fleet Summary</b><br>
    <b>Total Vehicles:</b> {total_vehicles_count} trucks<br>
    <b>Circuits:</b> {len(vehicle_assignments)}<br>
    <b>Operating Hours:</b> 8:30 AM - 1:30 PM<br>
    <b>Cost Structure:</b> ₹1,350 per vehicle per day (2 trips)<br>
    <b>Monthly Cost:</b> ₹{total_vehicles_count * 1350 * 30:,}
    """
    
    interhub_layer.add_to(m)
