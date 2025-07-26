import streamlit as st
import pandas as pd
import folium

# Cost constants
WAREHOUSE_COSTS = {
    'main_warehouse_monthly_rent': 35000,
    'auxiliary_warehouse_monthly_rent': 15000,
    'main_warehouse_capacity': 600,
    'auxiliary_warehouse_capacity': 200
}

PEOPLE_COSTS = {
    'main_warehouse_staff_monthly': 25000,  # Manager + 2 staff
    'auxiliary_warehouse_staff_monthly': 12000,  # 1 staff member
}

VEHICLE_COSTS = {
    'auto_per_trip': 900,
    'mini_truck_per_trip': 1350,
    'truck_per_trip': 1800,
    'trips_per_day_first_mile': 4,
    'trips_per_day_middle_mile': 3,
    'trips_per_day_last_mile': 8
}

VEHICLE_SPECS = {
    'auto': {'capacity': 45, 'icon': '🛺', 'name': 'Auto', 'delivery_types': 'XL and equivalents', 'max_daily': 45},  # Max 45 XL orders/day
    'bike': {'capacity': 25, 'icon': '🏍️', 'name': 'Bike', 'delivery_types': 'S/M/L orders', 'max_daily': 25},  # Max 25 S/M/L orders/day
    'mini_truck': {'capacity': 300, 'icon': '🚚', 'name': 'Mini Truck'},  # 300 XL orders capacity
    'truck': {'capacity': 500, 'icon': '🚛', 'name': 'Truck'}  # 500 XL orders capacity
}

def calculate_simple_costs(main_warehouse_count, auxiliary_warehouse_count, total_daily_orders):
    """Calculate simple monthly operational costs"""
    
    # Fixed 5 main warehouses for Bengaluru (warehouse count doesn't change with demand)
    fixed_main_warehouses = 5
    
    # Warehouse rental costs (fixed main warehouse count)
    warehouse_rent = (fixed_main_warehouses * WAREHOUSE_COSTS['main_warehouse_monthly_rent'] + 
                     auxiliary_warehouse_count * WAREHOUSE_COSTS['auxiliary_warehouse_monthly_rent'])
    
    # People costs (fixed main warehouse count)
    people_costs = (fixed_main_warehouses * PEOPLE_COSTS['main_warehouse_staff_monthly'] + 
                   auxiliary_warehouse_count * PEOPLE_COSTS['auxiliary_warehouse_staff_monthly'])
    
    # Transportation costs (corrected with realistic vehicle capacities)
    # First mile: Customer pickups to main warehouse (much more efficient now)
    # Average capacity across vehicle mix is higher now (Auto: 50, Mini: 300, Truck: 500)
    avg_vehicle_capacity = 200  # Conservative average across vehicle mix
    first_mile_trips_per_day = max(1, total_daily_orders / avg_vehicle_capacity)
    first_mile_monthly = first_mile_trips_per_day * VEHICLE_COSTS['mini_truck_per_trip'] * 30
    
    # Middle mile: Main to auxiliary (inventory restocking) + interhub transfers
    auxiliary_restock_trips_per_day = auxiliary_warehouse_count * 2  # 2 trips per auxiliary per day
    auxiliary_restock_monthly = auxiliary_restock_trips_per_day * VEHICLE_COSTS['mini_truck_per_trip'] * 30
    
    # Interhub transfer costs (realistic 8-9 vehicles for 5 warehouses in Bengaluru)
    # Based on proven methodology: hub-and-spoke redistribution with traffic constraints
    # Cost structure: ₹1,350 for 2 trips total (not per trip)
    interhub_vehicles = 8  # Realistic vehicle count from user's mid mile planner
    interhub_cost_per_day = 1350  # ₹1,350 for 2 trips per day per vehicle
    interhub_monthly = interhub_vehicles * interhub_cost_per_day * 30
    
    middle_mile_monthly = auxiliary_restock_monthly + interhub_monthly
    
    # Last mile: Auxiliary to customer delivery
    last_mile_trips_per_day = max(1, total_daily_orders / 20)  # 20 orders per delivery trip
    last_mile_monthly = last_mile_trips_per_day * VEHICLE_COSTS['auto_per_trip'] * 30
    
    total_transportation = first_mile_monthly + middle_mile_monthly + last_mile_monthly
    
    # Total monthly costs
    total_monthly = warehouse_rent + people_costs + total_transportation
    
    # Cost per order
    monthly_orders = total_daily_orders * 30
    cost_per_order = total_monthly / monthly_orders if monthly_orders > 0 else 0
    
    return {
        'warehouse_rent': warehouse_rent,
        'people_costs': people_costs,
        'transportation_costs': total_transportation,
        'first_mile_cost': first_mile_monthly,
        'middle_mile_cost': middle_mile_monthly,
        'last_mile_cost': last_mile_monthly,
        'total_monthly': total_monthly,
        'cost_per_order': cost_per_order
    }

def calculate_auxiliary_vehicles(auxiliary_warehouses, main_warehouses):
    """Calculate vehicle requirements for auxiliary restocking - one vehicle per hub serves nearby auxiliaries"""
    
    vehicle_assignments = []
    total_vehicles = {'mini_truck': 0, 'truck': 0}
    
    # Group auxiliaries by parent hub
    hub_groups = {}
    for aux in auxiliary_warehouses:
        parent_hub_id = aux.get('parent', 'Unknown')
        if parent_hub_id not in hub_groups:
            hub_groups[parent_hub_id] = []
        hub_groups[parent_hub_id].append(aux)
    
    # Calculate vehicles needed per hub (not per auxiliary)
    for hub_id, auxiliaries in hub_groups.items():
        if not auxiliaries:
            continue
            
        # Calculate total capacity needed for all auxiliaries under this hub
        total_hub_aux_capacity = sum([aux.get('capacity', 200) for aux in auxiliaries])
        aux_count = len(auxiliaries)
        
        # Find the hub info
        hub_info = next((hub for hub in main_warehouses if hub['id'] == hub_id), None)
        hub_code = hub_info.get('hub_code', f'HUB{hub_id}') if hub_info else f'HUB{hub_id}'
        
        # Calculate average distance to auxiliaries from this hub
        distances = [aux.get('distance_to_parent', 8) for aux in auxiliaries]
        avg_distance = sum(distances) / len(distances) if distances else 8
        max_distance = max(distances) if distances else 8
        
        # Determine vehicle type based on total load and distance
        if total_hub_aux_capacity <= 800 and max_distance <= 10:
            # Light load and short distance -> 1-2 Mini Trucks
            vehicle_type = 'mini_truck'
            vehicle_capacity = 300  # Orders per trip
            trips_per_day = 3  # Max trips per vehicle per day
            max_orders_per_vehicle_per_day = vehicle_capacity * trips_per_day  # 900 orders/day max
            
            vehicles_needed = max(1, min(2, (total_hub_aux_capacity + max_orders_per_vehicle_per_day - 1) // max_orders_per_vehicle_per_day))
        else:
            # Heavy load or long distance -> 1 Truck
            vehicle_type = 'truck'
            vehicle_capacity = 500  # Orders per trip
            trips_per_day = 2  # Trucks make fewer but larger trips
            max_orders_per_vehicle_per_day = vehicle_capacity * trips_per_day  # 1000 orders/day max
            
            vehicles_needed = 1  # One truck per hub is usually sufficient
        
        total_vehicles[vehicle_type] += vehicles_needed
        
        vehicle_assignments.append({
            'hub_id': hub_id,
            'hub_code': hub_code,
            'auxiliaries_served': aux_count,
            'total_capacity': total_hub_aux_capacity,
            'avg_distance': avg_distance,
            'max_distance': max_distance,
            'vehicle_type': vehicle_type,
            'vehicles_needed': vehicles_needed,
            'auxiliary_list': [aux.get('id', 'Unknown') for aux in auxiliaries]
        })
    
    return total_vehicles, vehicle_assignments

def calculate_interhub_vehicles(main_warehouses):
    """Calculate vehicle requirements for mid mile redistribution using hub-and-spoke with 4 PM deadline"""
    
    vehicle_assignments = []
    total_vehicles = {'truck': 0}
    
    total_hubs = len(main_warehouses)
    
    if total_hubs <= 2:
        return total_vehicles, vehicle_assignments
    
    # Hub-and-spoke redistribution model (proven methodology)
    # After first mile consolidation, strategic transfers between 6 warehouses by 4 PM
    total_daily_orders = sum([hub.get('orders', 0) for hub in main_warehouses])
    
    # Redistribution percentage: 20-25% of orders need repositioning for optimal last mile
    redistribution_percentage = 0.22  # 22% redistribution rate (optimized from user experience)
    daily_redistribution_orders = int(total_daily_orders * redistribution_percentage)
    
    # Hub analysis for inventory positioning
    hub_data = []
    total_pickup_volume = 0
    total_delivery_demand = 0
    
    for i, hub in enumerate(main_warehouses):
        hub_orders = hub.get('orders', 0)
        
        # Hub characteristics based on location and catchment area
        # Some hubs are naturally pickup-heavy (industrial areas), others delivery-heavy (residential)
        if i == 0:  # Primary consolidation hub
            pickup_ratio = 0.65  # High pickup concentration
        elif i <= 2:  # Secondary industrial hubs
            pickup_ratio = 0.55
        else:  # Residential/delivery-focused hubs
            pickup_ratio = 0.35
            
        pickup_volume = int(hub_orders * pickup_ratio)
        delivery_demand = int(hub_orders * (1.0 - pickup_ratio))
        imbalance = pickup_volume - delivery_demand
        
        hub_data.append({
            'hub': hub,
            'hub_id': i + 1,
            'pickup_volume': pickup_volume,
            'delivery_demand': delivery_demand,
            'imbalance': imbalance,
            'hub_code': hub.get('hub_code', f"W{i+1}"),
            'priority': 'primary' if i == 0 else 'secondary'
        })
        
        total_pickup_volume += pickup_volume
        total_delivery_demand += delivery_demand
    
    # Create efficient redistribution routes (multi-hub circuits)
    # Strategy: Optimize circuits for 5 main warehouses (fixed network)
    
    if total_hubs >= 5:
        # Circuit 1: Primary hub + 2 nearby warehouses (high volume circuit)
        circuit1_hubs = [hub_data[0], hub_data[1], hub_data[2]]  # W1 → W2 → W3 → W1
        
        # Circuit 2: Remaining 2 warehouses (secondary circuit)  
        circuit2_hubs = [hub_data[3], hub_data[4]]  # W4 → W5 → W4
        
        circuits = [circuit1_hubs, circuit2_hubs]
    elif total_hubs >= 3:
        # Single circuit for smaller networks (3-4 hubs)
        circuits = [hub_data]
    else:
        # Very small network - direct transfers
        circuits = [hub_data]
    
    # Calculate vehicle requirements for each circuit
    for circuit_idx, circuit_hubs in enumerate(circuits):
        if len(circuit_hubs) < 2:
            continue
            
        circuit_name = f"Circuit {circuit_idx + 1}"
        
        # Calculate redistribution volume for this circuit
        circuit_total_orders = sum([h['pickup_volume'] + h['delivery_demand'] for h in circuit_hubs])
        circuit_redistribution = int(circuit_total_orders * 0.25)  # 25% internal redistribution
        
        # Efficient routing: Each truck makes circuit covering all hubs
        # Time constraint: Must complete redistribution by 4 PM for last mile planning
        
        # Calculate circuit distance
        circuit_distance = 0
        hub_route = []
        for i in range(len(circuit_hubs)):
            current_hub = circuit_hubs[i]['hub']
            next_hub = circuit_hubs[(i + 1) % len(circuit_hubs)]['hub']
            
            # Distance between consecutive hubs
            segment_distance = ((current_hub['lat'] - next_hub['lat'])**2 + 
                              (current_hub['lon'] - next_hub['lon'])**2)**0.5 * 111
            circuit_distance += segment_distance
            hub_route.append(circuit_hubs[i]['hub_code'])
        
        # Complete the circuit
        circuit_route = " → ".join(hub_route) + f" → {hub_route[0]}"
        
        # Realistic vehicle calculation based on Bengaluru traffic and proven methodology
        # Based on user's mid mile planner: 8:30 AM to 1:30 PM operations (5 hours available)
        truck_capacity = 500  # Orders per trip
        available_hours = 5  # 8:30 AM to 1:30 PM window (before 4 PM last mile planning)
        
        # Realistic Bengaluru traffic parameters from user experience
        loading_unloading_time_per_hub = 0.75  # 45 minutes per hub (realistic for city operations)
        total_loading_time = len(circuit_hubs) * loading_unloading_time_per_hub
        
        # Bengaluru traffic speed: Much slower than theoretical 25 km/h
        city_traffic_speed = 15  # 15 km/h average in Bengaluru traffic during mid mile hours
        travel_time_hours = circuit_distance / city_traffic_speed
        
        # Add buffer time for delays, congestion, route optimization
        buffer_time = 0.5  # 30 minutes buffer per circuit
        total_circuit_time = travel_time_hours + total_loading_time + buffer_time
        
        # Realistic trips per truck (much more conservative)
        max_trips_per_truck = max(1, int(available_hours / total_circuit_time))
        max_trips_per_truck = min(max_trips_per_truck, 1)  # In reality, mostly 1 trip per truck due to constraints
        
        # Vehicle requirement calculation matching user's 9-10 vehicle experience
        # For 5 warehouses, need more vehicles due to:
        # 1. Bengaluru traffic congestion
        # 2. Loading/unloading realities  
        # 3. 4 PM deadline pressure
        # 4. Operational buffer requirements
        
        if circuit_idx == 0:  # Primary circuit (3 hubs) - needs more vehicles
            base_vehicles = 2  # Base requirement for primary circuit
            volume_factor = max(1, circuit_redistribution // 400)  # Additional vehicles for volume
            vehicles_needed = base_vehicles + volume_factor
        else:  # Secondary circuit (2 hubs) - still needs multiple vehicles
            base_vehicles = 1
            volume_factor = max(1, circuit_redistribution // 600)  
            vehicles_needed = base_vehicles + volume_factor
        
        # Apply Bengaluru reality multiplier (from user's 9-10 vehicle experience)
        bengaluru_reality_factor = 1.8  # Traffic and operational complexity factor
        vehicles_needed = int(vehicles_needed * bengaluru_reality_factor)
        vehicles_needed = max(vehicles_needed, 2)  # Minimum 2 vehicles per circuit for reliability
        
        total_vehicles['truck'] += vehicles_needed
        
        vehicle_assignments.append({
            'circuit_name': circuit_name,
            'circuit_hubs': [h['hub_code'] for h in circuit_hubs],
            'redistribution_volume': circuit_redistribution,
            'circuit_distance': circuit_distance,
            'circuit_time_hours': total_circuit_time,
            'max_trips_per_truck': max_trips_per_truck,
            'vehicles_needed': vehicles_needed,
            'vehicle_type': 'truck',
            'deadline_constraint': '4 PM',
            # Backward compatibility keys
            'relay_group': circuit_idx + 1,
            'relay_route': circuit_route,
            'hub_count': len(circuit_hubs),
            'total_circuit_distance': circuit_distance,
            'daily_transfer_orders': circuit_redistribution
        })
    
    return total_vehicles, vehicle_assignments

def analyze_order_mix(df_filtered=None):
    """Analyze order mix to determine optimal bike vs auto allocation"""
    # Simulated order distribution based on typical logistics patterns
    # In real implementation, this would analyze actual order size data
    return {
        'xl_equivalent_ratio': 0.4,  # 40% XL/heavy orders need autos
        'sml_ratio': 0.6,           # 60% S/M/L orders can use bikes
        'bike_efficiency_factor': 1.3  # Bikes are 30% more efficient for S/M/L deliveries
    }

def distance_based_vehicle_allocation(orders_xl, orders_sml, avg_delivery_distance):
    """Distance and weight optimized allocation: Bikes for short distance S/M/L, autos for long/heavy"""
    
    # Vehicle capacities and characteristics
    auto_capacity = 45  # XL orders per day
    bike_capacity = 25  # S/M/L orders per day
    
    # Distance thresholds
    bike_max_distance = 3.0  # Bikes effective up to 3km
    auto_preferred_distance = 5.0  # Autos better for 5km+
    
    vehicles = []
    
    # Allocate S/M/L orders based on distance
    if orders_sml > 0:
        if avg_delivery_distance <= bike_max_distance:
            # Short distance: Use bikes (cost-effective, agile)
            bike_count = (orders_sml + bike_capacity - 1) // bike_capacity
            for i in range(bike_count):
                allocated_sml = min(bike_capacity, orders_sml - i * bike_capacity)
                vehicles.append({
                    'type': 'bike',
                    'xl_orders': 0,
                    'sml_orders': allocated_sml,
                    'total_orders': allocated_sml,
                    'utilization': allocated_sml / bike_capacity,
                    'rationale': f'Short distance ({avg_delivery_distance:.1f}km) - bikes optimal'
                })
        elif avg_delivery_distance <= auto_preferred_distance:
            # Medium distance: Mixed allocation (bikes for lighter, autos for efficiency)
            bike_orders = int(orders_sml * 0.7)  # 70% bikes for agility
            auto_sml_orders = orders_sml - bike_orders  # 30% autos for efficiency
            
            if bike_orders > 0:
                bike_count = (bike_orders + bike_capacity - 1) // bike_capacity
                for i in range(bike_count):
                    allocated_sml = min(bike_capacity, bike_orders - i * bike_capacity)
                    vehicles.append({
                        'type': 'bike',
                        'xl_orders': 0,
                        'sml_orders': allocated_sml,
                        'total_orders': allocated_sml,
                        'utilization': allocated_sml / bike_capacity,
                        'rationale': f'Medium distance ({avg_delivery_distance:.1f}km) - bikes for agility'
                    })
            
            if auto_sml_orders > 0:
                # Autos carrying S/M/L orders have higher capacity utilization
                auto_sml_capacity = 35  # Autos can carry more S/M/L than XL
                auto_count = (auto_sml_orders + auto_sml_capacity - 1) // auto_sml_capacity
                for i in range(auto_count):
                    allocated_sml = min(auto_sml_capacity, auto_sml_orders - i * auto_sml_capacity)
                    vehicles.append({
                        'type': 'auto',
                        'xl_orders': 0,
                        'sml_orders': allocated_sml,
                        'total_orders': allocated_sml,
                        'utilization': allocated_sml / auto_capacity,
                        'rationale': f'Medium distance ({avg_delivery_distance:.1f}km) - autos for efficiency'
                    })
        else:
            # Long distance: Prefer autos (more efficient for longer routes)
            auto_sml_capacity = 35  # Higher capacity for S/M/L in autos
            auto_count = (orders_sml + auto_sml_capacity - 1) // auto_sml_capacity
            for i in range(auto_count):
                allocated_sml = min(auto_sml_capacity, orders_sml - i * auto_sml_capacity)
                vehicles.append({
                    'type': 'auto',
                    'xl_orders': 0,
                    'sml_orders': allocated_sml,
                    'total_orders': allocated_sml,
                    'utilization': allocated_sml / auto_capacity,
                    'rationale': f'Long distance ({avg_delivery_distance:.1f}km) - autos preferred'
                })
    
    # Allocate XL orders to autos (only autos can handle XL)
    if orders_xl > 0:
        auto_count = (orders_xl + auto_capacity - 1) // auto_capacity
        for i in range(auto_count):
            allocated_xl = min(auto_capacity, orders_xl - i * auto_capacity)
            vehicles.append({
                'type': 'auto',
                'xl_orders': allocated_xl,
                'sml_orders': 0,
                'total_orders': allocated_xl,
                'utilization': allocated_xl / auto_capacity,
                'rationale': 'XL orders - only autos capable'
            })
    
    # Count vehicles by type
    auto_vehicles = sum(1 for v in vehicles if v['type'] == 'auto')
    bike_vehicles = sum(1 for v in vehicles if v['type'] == 'bike')
    
    return auto_vehicles, bike_vehicles, vehicles

def calculate_last_mile_vehicles(auxiliary_warehouses, main_warehouses, total_daily_orders, df_filtered=None):
    """Calculate vehicle requirements for last mile operations with direct delivery optimization"""
    
    vehicle_assignments = []
    total_vehicles = {'auto': 0, 'bike': 0}
    
    # Analyze order mix for optimal vehicle selection
    order_mix = analyze_order_mix(df_filtered)
    
    # Find orders that can be delivered directly from main hubs (not covered by auxiliaries)
    direct_delivery_orders = 0
    if df_filtered is not None and auxiliary_warehouses:
        for _, order in df_filtered.iterrows():
            order_lat, order_lon = order['order_lat'], order['order_long']
            
            # Check if order is within 3km of any auxiliary
            covered_by_aux = False
            for aux in auxiliary_warehouses:
                distance = ((order_lat - aux['lat'])**2 + (order_lon - aux['lon'])**2)**0.5 * 111
                if distance <= 3:  # 3km auxiliary coverage
                    covered_by_aux = True
                    break
            
            # If not covered by auxiliary, check if within 8km of main hub for direct delivery
            if not covered_by_aux:
                for main_hub in main_warehouses:
                    distance = ((order_lat - main_hub['lat'])**2 + (order_lon - main_hub['lon'])**2)**0.5 * 111
                    if distance <= 8:  # 8km main hub coverage
                        direct_delivery_orders += 1
                        break
    
    # Allocate vehicles for direct delivery from main hubs
    main_hub_vehicles = {'auto': 0, 'bike': 0}
    if direct_delivery_orders > 0:
        xl_direct = int(direct_delivery_orders * order_mix['xl_equivalent_ratio'])
        sml_direct = direct_delivery_orders - xl_direct
        
        # Main hubs typically serve longer distances (5-8km average)
        main_hub_avg_distance = 6.0  # Average 6km delivery distance from main hubs
        
        # Use distance-based allocation for direct delivery
        auto_count, bike_count, allocation_details = distance_based_vehicle_allocation(xl_direct, sml_direct, main_hub_avg_distance)
        main_hub_vehicles['auto'] = auto_count
        main_hub_vehicles['bike'] = bike_count
        
        total_vehicles['auto'] += auto_count
        total_vehicles['bike'] += bike_count
    
    # Calculate remaining orders for auxiliary delivery
    aux_orders = total_daily_orders - direct_delivery_orders
    
    # Distribute remaining orders among auxiliaries proportionally
    total_aux_capacity = sum([aux.get('capacity', 200) for aux in auxiliary_warehouses])
    
    for aux in auxiliary_warehouses:
        aux_capacity = aux.get('capacity', 200)
        
        # Calculate orders this auxiliary handles (from remaining orders)
        if total_aux_capacity > 0 and aux_orders > 0:
            aux_order_share = int((aux_capacity / total_aux_capacity) * aux_orders)
        else:
            aux_order_share = 0
        
        if aux_order_share > 0:
            # Split orders based on size analysis
            xl_orders = int(aux_order_share * order_mix['xl_equivalent_ratio'])
            sml_orders = aux_order_share - xl_orders
            
            # Calculate average delivery distance for this auxiliary
            aux_delivery_radius = aux.get('delivery_radius', 3)
            avg_delivery_distance = aux_delivery_radius * 0.7  # Average distance within radius
            
            # Use distance-based allocation for this auxiliary
            auto_vehicles, bike_vehicles, allocation_details = distance_based_vehicle_allocation(xl_orders, sml_orders, avg_delivery_distance)
            
            total_vehicles['auto'] += auto_vehicles
            total_vehicles['bike'] += bike_vehicles
            
            vehicle_assignments.append({
                'auxiliary_id': aux.get('id', 'Unknown'),
                'capacity': aux_capacity,
                'orders_handled': aux_order_share,
                'xl_orders': xl_orders,
                'sml_orders': sml_orders,
                'auto_vehicles': auto_vehicles,
                'bike_vehicles': bike_vehicles,
                'allocation_details': allocation_details,
                'primary_vehicle': 'auto' if auto_vehicles >= bike_vehicles else 'bike',
                'total_vehicles': auto_vehicles + bike_vehicles
            })
        else:
            # No orders for this auxiliary
            vehicle_assignments.append({
                'auxiliary_id': aux.get('id', 'Unknown'),
                'capacity': aux_capacity,
                'orders_handled': 0,
                'xl_orders': 0,
                'sml_orders': 0,
                'auto_vehicles': 0,
                'bike_vehicles': 0,
                'allocation_details': [],
                'primary_vehicle': 'auto',
                'total_vehicles': 0
            })
    
    # Add main hub direct delivery info
    vehicle_assignments.append({
        'hub_direct_delivery': True,
        'orders_handled': direct_delivery_orders,
        'auto_vehicles': main_hub_vehicles['auto'],
        'bike_vehicles': main_hub_vehicles['bike'],
        'total_vehicles': main_hub_vehicles['auto'] + main_hub_vehicles['bike']
    })
    
    return total_vehicles, vehicle_assignments

def calculate_first_mile_vehicles(df_filtered, scaling_factor=1):
    """Calculate vehicle requirements for first mile operations"""
    
    # Get pickup data scaled to target capacity
    pickup_volumes = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size()
    
    vehicle_assignments = []
    total_vehicles = {'auto': 0, 'mini_truck': 0, 'truck': 0}
    
    for pickup_location, volume in pickup_volumes.items():
        scaled_volume = int(volume * scaling_factor)
        
        # Determine vehicle type based on daily volume with realistic XL capacities
        if scaled_volume <= 50:  # Up to 50 orders -> Auto (1 trip)
            vehicle_type = 'auto'
            trips_needed = max(1, (scaled_volume + 49) // 50)  # Ceiling division
        elif scaled_volume <= 300:  # 51-300 orders -> Mini Truck
            vehicle_type = 'mini_truck' 
            trips_needed = max(1, (scaled_volume + 299) // 300)  # Ceiling division
        else:  # 300+ orders -> Truck
            vehicle_type = 'truck'
            trips_needed = max(1, (scaled_volume + 499) // 500)  # Ceiling division
        
        # Calculate vehicles needed (max 4 trips per vehicle per day for efficiency)
        vehicles_needed = max(1, (trips_needed + 3) // 4)  # Max 4 trips per vehicle per day
        
        total_vehicles[vehicle_type] += vehicles_needed
        
        vehicle_assignments.append({
            'pickup': pickup_location[0] if isinstance(pickup_location, tuple) else pickup_location,
            'volume': scaled_volume,
            'vehicle_type': vehicle_type,
            'vehicles_needed': vehicles_needed
        })
    
    return total_vehicles, vehicle_assignments

def create_first_mile_vehicle_layer(vehicle_assignments, vehicle_counts):
    """Create a toggleable first mile vehicle layer"""
    
    # Calculate total vehicles for layer name
    total_vehicles = sum(vehicle_counts.values())
    
    first_mile_layer = folium.FeatureGroup(
        name=f"🚛 First Mile Vehicles ({total_vehicles} total)", 
        show=False  # Hidden by default
    )
    
    # Add vehicle markers for each pickup location
    for assignment in vehicle_assignments:
        pickup = assignment['pickup']
        volume = assignment['volume']
        vehicle_type = assignment['vehicle_type']
        vehicles_needed = assignment['vehicles_needed']
        
        # Get pickup coordinates (simplified - you may need to match with pickup data)
        # For now, we'll add a summary marker
        vehicle_info = VEHICLE_SPECS[vehicle_type]
        
        # Create popup with vehicle details
        popup_html = f"""
        <b>🚛 First Mile Operation</b><br>
        <b>Pickup Location:</b> {pickup}<br>
        <b>Daily Volume:</b> {volume} orders<br>
        <b>Vehicle Type:</b> {vehicle_info['icon']} {vehicle_info['name']}<br>
        <b>Vehicles Needed:</b> {vehicles_needed}<br>
        <b>Capacity:</b> {vehicle_info['capacity']} orders/trip<br>
        <b>Daily Trips:</b> {max(1, volume // vehicle_info['capacity'])}
        """
        
        # Add invisible marker with vehicle info (will be enhanced with actual coordinates)
        folium.Marker(
            location=[12.9716, 77.5946],  # Default Bangalore center
            popup=popup_html,
            tooltip=f"🚛 {vehicle_info['name']} - {volume} orders/day",
            icon=folium.Icon(color='orange', icon='truck', prefix='fa')
        ).add_to(first_mile_layer)
    
    # Add fleet summary in the layer
    fleet_summary = f"""
    <b>🚛 First Mile Fleet Summary</b><br>
    """
    
    for vehicle_type, count in vehicle_counts.items():
        if count > 0:
            vehicle_info = VEHICLE_SPECS[vehicle_type]
            fleet_summary += f"""
            <b>{vehicle_info['icon']} {count}x {vehicle_info['name']}</b><br>
            Capacity: {vehicle_info['capacity']} orders/trip<br>
            """
    
    return first_mile_layer

def show_simple_cost_analysis(main_warehouses, auxiliary_warehouses, total_daily_orders):
    """Display simple cost analysis in Streamlit"""
    
    main_count = len(main_warehouses)
    aux_count = len(auxiliary_warehouses)
    
    costs = calculate_simple_costs(main_count, aux_count, total_daily_orders)
    
    st.subheader("💰 Monthly Cost Analysis")
    
    # Create three columns for cost breakdown
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🏢 Warehouse Rent", 
            f"₹{costs['warehouse_rent']:,.0f}",
            help=f"Main: 5 × ₹35k (fixed), Aux: {aux_count} × ₹15k"
        )
        
    with col2:
        st.metric(
            "👥 People Costs", 
            f"₹{costs['people_costs']:,.0f}",
            help=f"Main: 5 × ₹25k (fixed), Aux: {aux_count} × ₹12k"
        )
        
    with col3:
        st.metric(
            "🚛 Transportation", 
            f"₹{costs['transportation_costs']:,.0f}",
            help="First mile + Middle mile + Last mile"
        )
    
    # Transportation breakdown
    st.subheader("🚛 Transportation Cost Breakdown")
    
    trans_col1, trans_col2, trans_col3 = st.columns(3)
    
    with trans_col1:
        st.metric(
            "📦 First Mile",
            f"₹{costs['first_mile_cost']:,.0f}",
            help="Customer pickups to main warehouses"
        )
        
    with trans_col2:
        st.metric(
            "🔗 Middle Mile", 
            f"₹{costs['middle_mile_cost']:,.0f}",
            help="Main warehouses to auxiliary warehouses"
        )
        
    with trans_col3:
        st.metric(
            "🏠 Last Mile",
            f"₹{costs['last_mile_cost']:,.0f}",
            help="Final delivery to customers"
        )
    
    # Total cost summary
    st.subheader("📊 Cost Summary")
    
    summary_col1, summary_col2 = st.columns(2)
    
    with summary_col1:
        st.metric(
            "💸 Total Monthly Cost",
            f"₹{costs['total_monthly']:,.0f}",
            help="All operational costs combined"
        )
        
    with summary_col2:
        st.metric(
            "📈 Cost per Order",
            f"₹{costs['cost_per_order']:.1f}",
            help="Total monthly cost ÷ monthly orders"
        )
    
    # Cost efficiency insights
    st.info(f"""
    **💡 Cost Efficiency Insights:**
    - **Fixed Network:** 5 main warehouses + {aux_count} auxiliaries (optimized for Bengaluru)
    - **Daily Capacity:** {total_daily_orders:,} orders ({total_daily_orders//5:,} orders/main warehouse)
    - **Monthly Volume:** {total_daily_orders * 30:,} orders
    - **Cost Structure:** {costs['warehouse_rent']/costs['total_monthly']*100:.0f}% rent, {costs['people_costs']/costs['total_monthly']*100:.0f}% people, {costs['transportation_costs']/costs['total_monthly']*100:.0f}% transport
    """)

def calculate_network_for_volume(monthly_orders):
    """Calculate complete network configuration for a given monthly order volume"""
    
    # Convert to daily orders for network calculations
    daily_orders = monthly_orders // 30
    
    # Dynamic main warehouse calculation based on order density
    # Rule: 1 main warehouse per 500-700 monthly orders, minimum 2, maximum 5
    main_warehouses_needed = max(2, min(5, (monthly_orders + 599) // 600))
    
    # Dynamic auxiliary calculation based on order density and coverage requirements
    # Rule: 1 auxiliary per 300-400 monthly orders for good coverage
    auxiliary_warehouses_needed = max(3, min(15, (monthly_orders + 349) // 350))
    
    # Calculate vehicle requirements using realistic allocation for monthly volumes
    # First Mile - Based on pickup density (much smaller scale)
    first_mile_vehicles = {
        'auto': max(2, (monthly_orders // 15000) * 2),  # 2 autos per 15k monthly orders
        'mini_truck': max(3, (monthly_orders // 20000) * 3),  # 3 mini trucks per 20k monthly orders  
        'truck': max(1, (monthly_orders // 30000) * 1)  # 1 truck per 30k monthly orders
    }
    
    # Auxiliary Restocking - Based on number of hubs (not linear)
    auxiliary_vehicles = {
        'mini_truck': main_warehouses_needed,  # 1 mini truck per main hub
        'truck': max(0, main_warehouses_needed - 3)  # Additional trucks for larger networks
    }
    
    # Interhub Vehicles - Relay system based on hub count
    interhub_vehicles = {
        'truck': max(1, main_warehouses_needed // 3)  # 1 truck per 3-hub relay group
    }
    
    # Last Mile - Most volume-sensitive (monthly orders basis)
    # Based on order mix: 40% XL (autos), 60% S/M/L (bikes+autos)
    xl_orders_monthly = monthly_orders * 0.4
    sml_orders_monthly = monthly_orders * 0.6
    
    # Last mile allocation with distance considerations (monthly capacity)
    last_mile_vehicles = {
        'auto': max(2, int(xl_orders_monthly // 1350) + int(sml_orders_monthly * 0.3 // 1050)),  # Monthly capacity per auto ~1350 XL
        'bike': max(3, int(sml_orders_monthly * 0.7 // 750))  # Monthly capacity per bike ~750 S/M/L
    }
    
    return {
        'main_warehouses': main_warehouses_needed,
        'auxiliary_warehouses': auxiliary_warehouses_needed,
        'first_mile_vehicles': first_mile_vehicles,
        'auxiliary_vehicles': auxiliary_vehicles, 
        'interhub_vehicles': interhub_vehicles,
        'last_mile_vehicles': last_mile_vehicles
    }

def calculate_dynamic_costs(network_config, monthly_orders):
    """Calculate costs based on actual network configuration"""
    
    # Warehouse rental costs
    main_warehouse_rent = network_config['main_warehouses'] * 35000  # ₹35k per main warehouse
    auxiliary_warehouse_rent = network_config['auxiliary_warehouses'] * 15000  # ₹15k per auxiliary
    total_warehouse_rent = main_warehouse_rent + auxiliary_warehouse_rent
    
    # People costs
    main_warehouse_staff = network_config['main_warehouses'] * 25000  # ₹25k per main warehouse
    auxiliary_warehouse_staff = network_config['auxiliary_warehouses'] * 12000  # ₹12k per auxiliary
    total_people_costs = main_warehouse_staff + auxiliary_warehouse_staff
    
    # Transportation costs - based on actual vehicle requirements
    
    # First mile costs
    first_mile_cost = (
        network_config['first_mile_vehicles']['auto'] * 900 * 4 * 30 +  # Auto: ₹900/trip, 4 trips/day
        network_config['first_mile_vehicles']['mini_truck'] * 1350 * 3 * 30 +  # Mini truck: ₹1350/trip, 3 trips/day
        network_config['first_mile_vehicles']['truck'] * 1800 * 3 * 30  # Truck: ₹1800/trip, 3 trips/day
    )
    
    # Middle mile costs (auxiliary restocking + interhub)
    auxiliary_restock_cost = (
        network_config['auxiliary_vehicles']['mini_truck'] * 1350 * 3 * 30 +
        network_config['auxiliary_vehicles']['truck'] * 1800 * 2 * 30
    )
    
    interhub_cost = network_config['interhub_vehicles']['truck'] * 1800 * 2 * 30
    
    middle_mile_cost = auxiliary_restock_cost + interhub_cost
    
    # Last mile costs
    last_mile_cost = (
        network_config['last_mile_vehicles']['auto'] * 900 * 3 * 30 +  # Auto: 3 trips/day
        network_config['last_mile_vehicles']['bike'] * 400 * 5 * 30   # Bike: ₹400/trip, 5 trips/day
    )
    
    total_transportation = first_mile_cost + middle_mile_cost + last_mile_cost
    
    # Total monthly cost
    total_monthly_cost = total_warehouse_rent + total_people_costs + total_transportation
    
    # Cost per order
    cost_per_order = total_monthly_cost / monthly_orders if monthly_orders > 0 else 0
    
    return {
        'warehouse_rent': total_warehouse_rent,
        'people_costs': total_people_costs,
        'first_mile_cost': first_mile_cost,
        'middle_mile_cost': middle_mile_cost,
        'last_mile_cost': last_mile_cost,
        'total_transportation': total_transportation,
        'total_monthly': total_monthly_cost,
        'cost_per_order': cost_per_order
    }

def show_margin_analysis(main_warehouses, auxiliary_warehouses):
    """Show margin improvement analysis with dynamic network scaling from 45k to 100k orders"""
    
    st.subheader("Margin Analysis")
    
    # Variable revenue per order based on volume (economies of scale for pricing)
    def get_revenue_per_order(monthly_orders):
        # Higher volumes get better rates due to enterprise customers
        if monthly_orders >= 90000:
            return 85  # Large enterprise customers
        elif monthly_orders >= 70000:
            return 82  # Mid-tier enterprise
        elif monthly_orders >= 50000:
            return 79  # Growing enterprise
        else:
            return 76  # Smaller customers
    
    base_revenue_per_order = 78
    
    # Order volume range
    order_volumes = list(range(45000, 105000, 5000))  # 45k to 100k in steps of 5k
    
    margins = []
    revenues = []
    costs = []
    margin_percentages = []
    network_details = []
    
    for monthly_orders in order_volumes:
        # Calculate dynamic network configuration for this volume
        network_config = calculate_network_for_volume(monthly_orders)
        
        # Calculate costs based on actual network requirements
        cost_data = calculate_dynamic_costs(network_config, monthly_orders)
        
        # Calculate revenue and margin with variable ARPO
        current_arpo = get_revenue_per_order(monthly_orders)
        monthly_revenue = monthly_orders * current_arpo
        monthly_margin = monthly_revenue - cost_data['total_monthly']
        margin_percentage = (monthly_margin / monthly_revenue) * 100 if monthly_revenue > 0 else 0
        
        # Store for plotting
        revenues.append(monthly_revenue / 1000000)  # Convert to millions for readability
        costs.append(cost_data['total_monthly'] / 1000000)
        margins.append(monthly_margin / 1000000)
        margin_percentages.append(margin_percentage)
        
        # Store network details for analysis
        network_details.append({
            'monthly_orders': monthly_orders,
            'network_config': network_config,
            'cost_data': cost_data,
            'arpo': current_arpo
        })
    
    # Create DataFrame for plotting using Streamlit's built-in charting
    import pandas as pd
    
    df_margin = pd.DataFrame({
        'Daily Orders': [f"{vol//1000}k" for vol in order_volumes],
        'Monthly Revenue (₹M)': revenues,
        'Monthly Cost (₹M)': costs,
        'Margin %': margin_percentages
    })
    
    
    # Key insights
    min_margin = margin_percentages[0]
    max_margin = margin_percentages[-1]
    margin_improvement = max_margin - min_margin
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Margin @ 45k orders/day",
            f"{min_margin:.1f}%",
            help="Initial margin percentage at lower volume"
        )
    
    with col2:
        st.metric(
            "Margin @ 100k orders/day", 
            f"{max_margin:.1f}%",
            f"+{margin_improvement:.1f}%",
            help="Margin improvement with scale"
        )
    
    with col3:
        break_even_orders = None
        for i, margin in enumerate(margins):
            if margin > 0:
                break_even_orders = order_volumes[i]
                break
        
        if break_even_orders:
            st.metric(
                "Break-even Volume",
                f"{break_even_orders//1000}k orders/day",
                help="Daily orders needed to achieve profitability"
            )
        else:
            st.metric("Break-even", "Below 45k", help="Break-even point is below the analyzed range")
    
    # Summary insights
    st.success(f"""
    **🚀 Scale Economics Impact:**
    - **Fixed Costs Advantage**: Infrastructure costs remain largely fixed while revenue scales linearly
    - **Margin Improvement**: {margin_improvement:.1f} percentage points gain from 45k to 100k orders
    - **Revenue at Scale**: ₹{revenues[-1]:.1f}M monthly revenue at 100k orders/day
    - **Cost Efficiency**: Transportation cost per order decreases with higher vehicle utilization
    """)
    
    # Volume-based cost scaling analysis - variable cost items affected by order volumes
    st.markdown("---")
    st.markdown("**📊 Volume-Based Cost Scaling Impact**")
    
    # Analyze how variable cost items change with volume scaling
    scaling_analysis = []
    base_volume = 45000  # Base case: 45k orders/month
    peak_volume = 100000  # Peak case: 100k orders/month
    
    # Get base and peak configurations
    base_config = calculate_network_for_volume(base_volume)
    peak_config = calculate_network_for_volume(peak_volume)
    base_costs = calculate_dynamic_costs(base_config, base_volume)
    peak_costs = calculate_dynamic_costs(peak_config, peak_volume)
    
    # Key insight: Last mile cost per order reduction due to route density
    base_last_mile_cpo = base_costs['last_mile_cost'] / base_volume
    peak_last_mile_cpo = peak_costs['last_mile_cost'] / peak_volume
    
    # Vehicle-specific delivery efficiency improvements with volume scaling
    # Auto: ₹900 per trip, from 22 to 45 deliveries per trip
    # Bike: ₹400 per trip, from 12 to 25 deliveries per trip (proportional scaling)
    auto_current_deliveries = 22
    auto_improved_deliveries = 45
    bike_current_deliveries = 12  # Proportionally lower base for bikes
    bike_improved_deliveries = 25  # Bikes' maximum capacity from VEHICLE_SPECS
    
    # Calculate the cost improvement for each volume tier  
    for monthly_orders in [45000, 55000, 65000, 75000, 85000, 95000, 100000]:
        # Use the same calculation logic as the main cost analysis
        daily_orders = monthly_orders // 30
        config = calculate_network_for_volume(monthly_orders)
        
        # Use simple cost calculation (same as main analysis) instead of dynamic costs
        main_count = config['main_warehouses'] 
        aux_count = config['auxiliary_warehouses']
        costs = calculate_simple_costs(main_count, aux_count, daily_orders)
        
        # Current last mile cost per order (combination of autos and bikes)
        current_last_mile_cpo = costs['last_mile_cost'] / monthly_orders
        
        # Volume scaling progress (0 to 1 as orders go from 45k to 100k)
        volume_progress = min(1.0, (monthly_orders - 45000) / (100000 - 45000))
        
        # Progressive delivery efficiency for each vehicle type
        auto_deliveries_per_trip = auto_current_deliveries + volume_progress * (auto_improved_deliveries - auto_current_deliveries)
        bike_deliveries_per_trip = bike_current_deliveries + volume_progress * (bike_improved_deliveries - bike_current_deliveries)
        
        # Order mix: 40% XL (autos only), 60% S/M/L (mixed auto/bike)
        xl_orders = monthly_orders * 0.4  # XL orders - autos only
        sml_orders = monthly_orders * 0.6  # S/M/L orders - mixed allocation
        
        # Calculate vehicle-specific cost improvements
        # Auto cost improvement: ₹900 trip cost with improving deliveries per trip
        auto_current_cost_per_delivery = 900 / auto_current_deliveries  # ₹40.9
        auto_improved_cost_per_delivery = 900 / auto_deliveries_per_trip
        auto_savings_per_delivery = auto_current_cost_per_delivery - auto_improved_cost_per_delivery
        
        # Bike cost improvement: ₹400 trip cost with improving deliveries per trip  
        bike_current_cost_per_delivery = 400 / bike_current_deliveries  # ₹33.3
        bike_improved_cost_per_delivery = 400 / bike_deliveries_per_trip
        bike_savings_per_delivery = bike_current_cost_per_delivery - bike_improved_cost_per_delivery
        
        # Mixed allocation for S/M/L orders (70% bikes, 30% autos based on distance)
        sml_bike_ratio = 0.7
        sml_auto_ratio = 0.3
        
        # Total last mile savings per order
        auto_order_savings = (xl_orders * auto_savings_per_delivery + sml_orders * sml_auto_ratio * auto_savings_per_delivery) / monthly_orders
        bike_order_savings = (sml_orders * sml_bike_ratio * bike_savings_per_delivery) / monthly_orders
        
        last_mile_savings_per_order = auto_order_savings + bike_order_savings
        improved_last_mile_cpo = current_last_mile_cpo - last_mile_savings_per_order
        
        # Cost savings
        last_mile_savings_per_order = current_last_mile_cpo - improved_last_mile_cpo
        monthly_last_mile_savings = last_mile_savings_per_order * monthly_orders
        
        # Variable cost items affected by scaling
        # 1. Vehicle utilization improvement (spread fixed vehicle costs over more orders)
        vehicle_utilization_savings = (costs['first_mile_cost'] + costs['middle_mile_cost']) * 0.05 * volume_progress
        
        # 2. Fixed warehouse costs spread over more orders
        fixed_cost_advantage_per_order = (costs['warehouse_rent'] + costs['people_costs']) / monthly_orders
        
        # Total cost per order with scaling improvements
        original_cpo = costs['cost_per_order']
        improved_cpo = original_cpo - last_mile_savings_per_order - (vehicle_utilization_savings / monthly_orders)
        
        # Revenue and margin with scaling
        arpo = get_revenue_per_order(monthly_orders)
        improved_margin_per_order = arpo - improved_cpo
        improved_margin_percentage = (improved_margin_per_order / arpo) * 100
        
        # Calculate individual cost components per order for better breakdown
        warehouse_cost_per_order = costs['warehouse_rent'] / monthly_orders
        people_cost_per_order = costs['people_costs'] / monthly_orders
        transport_cost_per_order = costs['transportation_costs'] / monthly_orders
        improved_transport_cost_per_order = transport_cost_per_order - last_mile_savings_per_order - (vehicle_utilization_savings / monthly_orders)
        
        scaling_analysis.append({
            'Volume': f"{monthly_orders//1000}k",
            'Auto Del/Trip': f"{auto_deliveries_per_trip:.0f}",
            'Bike Del/Trip': f"{bike_deliveries_per_trip:.0f}",
            'Warehouse CPO': f"₹{warehouse_cost_per_order:.1f}",
            'People CPO': f"₹{people_cost_per_order:.1f}",
            'Transport CPO': f"₹{transport_cost_per_order:.1f} → ₹{improved_transport_cost_per_order:.1f}",
            'Original CPO': f"₹{original_cpo:.1f}",
            'Improved CPO': f"₹{improved_cpo:.1f}",
            'Savings/Order': f"₹{original_cpo - improved_cpo:.1f}",
            'Improved Margin %': f"{improved_margin_percentage:.1f}%"
        })
    
    scaling_df = pd.DataFrame(scaling_analysis)
    st.dataframe(scaling_df, use_container_width=True)
    
    # Key variable cost insights
    st.info(f"""
    **🎯 Variable Cost Scaling Benefits:**
    
    **Last Mile Route Density (Key Driver):**
    
    **Autos (XL + 30% S/M/L orders):**
    - At 45k orders: ~22 deliveries per ₹900 trip = ₹40.9 per delivery
    - At 100k orders: ~45 deliveries per ₹900 trip = ₹20.0 per delivery  
    - **51% reduction** in auto delivery cost
    
    **Bikes (70% S/M/L orders):**
    - At 45k orders: ~12 deliveries per ₹400 trip = ₹33.3 per delivery
    - At 100k orders: ~25 deliveries per ₹400 trip = ₹16.0 per delivery
    - **52% reduction** in bike delivery cost
    
    **Combined Impact:**
    - Proportional scaling across both vehicle types as route density improves
    - Higher order volumes → closer deliveries → more deliveries per trip
    
    **Vehicle Utilization Scaling:**
    - First/Middle mile vehicles achieve 5-10% better utilization at higher volumes
    - Fixed vehicle costs spread across more orders
    
    **Fixed Cost Distribution:**
    - Warehouse rent & staff costs become smaller percentage of total cost per order
    - Infrastructure investment leveraged across growing order base
    
    **Total Impact:** ₹{scaling_analysis[0]['Original CPO'][1:]} → ₹{scaling_analysis[-1]['Improved CPO'][1:]} per order (45k → 100k volume)
    """)