import streamlit as st
import pandas as pd
import math

# ============================================================================
# CENTRAL LOGISTICS CONFIGURATION - EDIT HERE TO SEE EFFECTS
# ============================================================================

# ============================================================================
# VEHICLE COSTS - MODIFY THESE VALUES TO SEE IMMEDIATE COST IMPACT
# ============================================================================
VEHICLE_COSTS = {
    'bike': 700,         # Bike daily cost - good for <80 orders, short distances
    'auto': 900,         # Auto daily cost - good for 80-120 orders, medium distances  
    'mini_truck': 1350,  # Mini truck daily cost - most common for hub operations
    'truck': 1800        # Truck daily cost - for high capacity and long distances
}

# CAPACITY SCALING - When orders exceed vehicle capacity, add more vehicles
CAPACITY_SCALING = {
    'orders_per_vehicle_threshold': 500,  # Above this, need additional vehicles
    'max_vehicles_per_hub': 3,           # Maximum vehicles per hub for auxiliaries
    'vehicle_cost_multiplier': 1.0       # Cost multiplier for additional vehicles (1.0 = same cost)
}

# VEHICLE CAPACITIES (Orders per trip and volume limits)
VEHICLE_SPECS = {
    'bike': {
        'order_capacity': 80,
        'volume_limit': 0.3,  # cubic meters
        'allowed_sizes': ['Small', 'Medium', 'Large'],
        'size_capacity': {'Small': 100, 'Medium': 60, 'Large': 40}
    },
    'auto': {
        'order_capacity': 120,
        'volume_limit': 1.5,  # cubic meters
        'allowed_sizes': ['Small', 'Medium', 'Large', 'XL'],
        'size_capacity': {'Small': 150, 'Medium': 80, 'Large': 50, 'XL': 20}
    },
    'mini_truck': {
        'order_capacity': 400,
        'volume_limit': 6.0,  # cubic meters
        'allowed_sizes': ['Small', 'Medium', 'Large', 'XL', 'XXL'],
        'size_capacity': {'Small': 500, 'Medium': 300, 'Large': 200, 'XL': 80, 'XXL': 40}
    },
    'truck': {
        'order_capacity': 600,
        'volume_limit': 10.0,  # cubic meters
        'allowed_sizes': ['Small', 'Medium', 'Large', 'XL', 'XXL'],
        'size_capacity': {'Small': 800, 'Medium': 500, 'Large': 300, 'XL': 120, 'XXL': 60}
    }
}

# PACKAGE DIMENSIONS (cubic meters per package)
PACKAGE_VOLUMES = {
    'Small': 0.001,    # 10cm x 10cm x 10cm
    'Medium': 0.003375, # 15cm x 15cm x 15cm
    'Large': 0.008,    # 20cm x 20cm x 20cm
    'XL': 0.027,       # 30cm x 30cm x 30cm
    'XXL': 0.064       # 40cm x 40cm x 40cm
}

# HUB-AUXILIARY CONFIGURATION
HUB_AUX_CONFIG = {
    'max_trips_per_day': 4,          # Maximum trips one vehicle can do per day
    'vehicle_selection_rules': {
        'small': {'capacity_threshold': 200, 'distance_threshold': 10, 'vehicle': 'auto'},
        'medium': {'capacity_threshold': 600, 'distance_threshold': 20, 'vehicle': 'mini_truck'},
        'large': {'capacity_threshold': 1000, 'distance_threshold': 30, 'vehicle': 'truck'}
    }
}

# FIRST MILE TRIP CONSOLIDATION CONFIGURATION
FIRST_MILE_CONFIG = {
    'proximity_radius_km': 6.0,      # Cluster pickup hubs within this radius
    'max_trip_radius_km': 6.0,       # Maximum radius for single trip coverage
    'min_consolidation_orders': 20   # Minimum orders to force consolidation
}

# INTER-HUB RELAY CONFIGURATION  
INTER_HUB_CONFIG = {
    'trips_per_day': 2,              # Relay trips between main hubs per day
    'enable_multi_node_routes': True, # Enable multi-stop routes for efficiency
    'max_stops_per_route': 4,        # Maximum stops in one relay trip
    'max_route_distance': 80,        # Maximum total distance for multi-stop route (km)
    'max_route_time': 120,           # Maximum total time for multi-stop route (minutes)
    'distance_rules': {
        'short': {'max_distance': 15, 'vehicle': 'auto'},      # Increased for multi-stop
        'medium': {'max_distance': 40, 'vehicle': 'mini_truck'}, # Increased for multi-stop
        'long': {'max_distance': 80, 'vehicle': 'truck'}      # For full circuit routes
    }
}

# LAST MILE CONFIGURATION
LAST_MILE_CONFIG = {
    'cost_per_order_bike': 25,    # INR per order for bike delivery
    'cost_per_order_auto': 35,    # INR per order for auto delivery
    'vehicle_mix_options': {
        'auto_heavy': {'auto': 0.7, 'bike': 0.3},      # 70% auto, 30% bike
        'balanced': {'auto': 0.5, 'bike': 0.5},        # 50% auto, 50% bike  
        'bike_heavy': {'auto': 0.3, 'bike': 0.7}       # 30% auto, 70% bike
    },
    'default_mix': 'auto_heavy',  # Default vehicle mix
    'distance_rules': {
        'bike_preferred': 3,      # Under 3km prefer bikes
        'auto_preferred': 7       # Over 7km prefer autos
    }
}

# HUB NAMING CONVENTION - Based on actual geographic placement
HUB_NAMES = {
    1: 'CTR',  # Central Hub
    2: 'EST',  # East Hub  
    3: 'WST',  # West Hub
    4: 'NTH',  # North Hub
    5: 'STH',  # South Hub
    6: 'NE',   # Northeast Hub
    7: 'NW',   # Northwest Hub
    8: 'SE'    # Southeast Hub
}

# HUB DISTANCE MATRIX (from your adjacency matrix) - time in minutes, distance in km
HUB_DISTANCE_MATRIX = {
    'Mahadevapura': {  # WHF in our system
        'Hebbal': {'time': 51, 'distance': 17.9},
        'Chandra Layout': {'time': 77, 'distance': 29.2}, 
        'Banashankari': {'time': 91, 'distance': 28.7},
        'Kudlu': {'time': 64, 'distance': 20},
        'Domlur': {'time': 41, 'distance': 11.9}
    },
    'Hebbal': {  # Could be mapped to our system
        'Chandra Layout': {'time': 44, 'distance': 16.9},
        'Banashankari': {'time': 78, 'distance': 31},
        'Kudlu': {'time': 88, 'distance': 32.5},
        'Domlur': {'time': 51, 'distance': 17.9}
    },
    'Chandra Layout': {  # Could be mapped to our system
        'Banashankari': {'time': 46, 'distance': 17.7},
        'Kudlu': {'time': 62, 'distance': 22.2},
        'Domlur': {'time': 63, 'distance': 22.5}
    },
    'Banashankari': {  # Could be mapped to our system
        'Kudlu': {'time': 45, 'distance': 20},
        'Domlur': {'time': 60, 'distance': 16.9}
    },
    'Kudlu': {  # Could be mapped to our system
        'Domlur': {'time': 42, 'distance': 13.8}
    }
}

# HUB COLOR CODING FOR MAP
HUB_COLORS = {
    'CTR': 'orange',    # Central - Orange
    'EST': 'blue',      # East - Blue  
    'WST': 'green',     # West - Green
    'NTH': 'purple',    # North - Purple
    'STH': 'darkred',   # South - Dark Red
    'NE': 'cadetblue',  # Northeast - Cadet Blue
    'NW': 'darkgreen',  # Northwest - Dark Green
    'SE': 'pink',       # Southeast - Pink
    'SW': 'lightred'    # Southwest - Light Red
}

# ============================================================================

def get_openstreetmap_distance(lat1, lon1, lat2, lon2):
    """Get driving distance and time between two points using OpenStreetMap routing"""
    try:
        import requests
        import time
        
        # Use OSRM (Open Source Routing Machine) for routing
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == 'Ok' and 'routes' in data:
                route = data['routes'][0]
                distance_km = route['distance'] / 1000  # Convert meters to km
                time_min = route['duration'] / 60       # Convert seconds to minutes
                return {'distance': distance_km, 'time': time_min}
        
        # Fallback to straight-line distance if API fails
        distance_km = ((lat1 - lat2)**2 + (lon1 - lon2)**2)**0.5 * 111
        time_min = distance_km * 2  # Estimate 2 minutes per km for city driving
        return {'distance': distance_km, 'time': time_min}
        
    except Exception as e:
        # Fallback calculation
        distance_km = ((lat1 - lat2)**2 + (lon1 - lon2)**2)**0.5 * 111
        time_min = distance_km * 2
        return {'distance': distance_km, 'time': time_min}

def calculate_optimal_multi_node_routes(big_warehouses):
    """Calculate optimal multi-node relay routes using real road distances"""
    if not INTER_HUB_CONFIG['enable_multi_node_routes'] or len(big_warehouses) < 3:
        return []
    
    import itertools
    
    # Build distance matrix between all hubs using OpenStreetMap
    hub_distances = {}
    for i, hub1 in enumerate(big_warehouses):
        hub1_id = hub1['id']
        hub_distances[hub1_id] = {}
        for j, hub2 in enumerate(big_warehouses):
            if i != j:
                hub2_id = hub2['id']
                route_info = get_openstreetmap_distance(
                    hub1['lat'], hub1['lon'], 
                    hub2['lat'], hub2['lon']
                )
                hub_distances[hub1_id][hub2_id] = route_info
    
    # Generate efficient multi-node routes
    routes = []
    
    # Create circular routes (most efficient for multi-stop)
    if len(big_warehouses) >= 4:
        # Try different starting points for circular routes
        hub_ids = [h['id'] for h in big_warehouses]
        for start_hub in hub_ids:
            remaining_hubs = [h for h in hub_ids if h != start_hub]
            
            # Find nearest neighbor circuit
            current_hub = start_hub
            route_sequence = [start_hub]
            total_distance = 0
            total_time = 0
            
            while remaining_hubs:
                # Find nearest unvisited hub
                nearest_hub = min(remaining_hubs, 
                                key=lambda h: hub_distances[current_hub][h]['distance'])
                
                distance_info = hub_distances[current_hub][nearest_hub]
                total_distance += distance_info['distance']
                total_time += distance_info['time']
                
                route_sequence.append(nearest_hub)
                remaining_hubs.remove(nearest_hub)
                current_hub = nearest_hub
                
                # Check constraints
                if (total_distance > INTER_HUB_CONFIG['max_route_distance'] or 
                    total_time > INTER_HUB_CONFIG['max_route_time'] or
                    len(route_sequence) >= INTER_HUB_CONFIG['max_stops_per_route']):
                    break
            
            # Add return to start for circular route
            if len(route_sequence) >= 3:
                return_info = hub_distances[current_hub][start_hub]
                total_distance += return_info['distance']
                total_time += return_info['time']
                route_sequence.append(start_hub)  # Complete the circle
                
                if (total_distance <= INTER_HUB_CONFIG['max_route_distance'] and 
                    total_time <= INTER_HUB_CONFIG['max_route_time']):
                    
                    routes.append({
                        'route_sequence': route_sequence,
                        'total_distance': total_distance,
                        'total_time': total_time,
                        'hubs_served': len(route_sequence) - 1,  # Exclude return to start
                        'efficiency_score': total_distance / (len(route_sequence) - 1),
                        'route_type': 'circular'
                    })
    
    # Also create efficient point-to-point routes for remaining connections
    hub_ids = [h['id'] for h in big_warehouses]
    for i, hub1_id in enumerate(hub_ids):
        for j, hub2_id in enumerate(hub_ids):
            if i < j:  # Avoid duplicates
                route_info = hub_distances[hub1_id][hub2_id]
                if route_info['distance'] <= INTER_HUB_CONFIG['distance_rules']['medium']['max_distance']:
                    routes.append({
                        'route_sequence': [hub1_id, hub2_id],
                        'total_distance': route_info['distance'],
                        'total_time': route_info['time'],
                        'hubs_served': 2,
                        'efficiency_score': route_info['distance'] / 2,
                        'route_type': 'point_to_point'
                    })
    
    # Select best routes (prioritize circular routes for efficiency)
    routes.sort(key=lambda x: (x['route_type'] != 'circular', x['efficiency_score']))
    
    return routes[:6]  # Return top 6 most efficient routes

# ============================================================================

def calculate_first_mile_costs(pickup_hubs, big_warehouses):
    """Calculate optimized first mile costs using smart scheduling with package size optimization"""
    
    # Use centralized configuration
    vehicle_specs = {}
    for vehicle_type, specs in VEHICLE_SPECS.items():
        vehicle_specs[vehicle_type] = {
            'order_capacity': specs['order_capacity'],
            'cost': VEHICLE_COSTS[vehicle_type],
            'allowed_sizes': specs['allowed_sizes'],
            'size_capacity': specs['size_capacity'],
            'volume_limit': specs['volume_limit'],
            'suitable_for': ['small_customers'] if vehicle_type == 'bike' else 
                           ['medium_customers'] if vehicle_type == 'auto' else 
                           ['large_customers']
        }
    
    package_volumes = PACKAGE_VOLUMES
    
    total_first_mile_cost = 0
    first_mile_details = []
    
    # Group pickup hubs by customer for smart scheduling
    customer_hubs = {}
    for _, hub in pickup_hubs.iterrows():
        customer = str(hub.get('customer', 'Unknown'))  # Convert to string to avoid Series issues
        if customer not in customer_hubs:
            customer_hubs[customer] = []
        customer_hubs[customer].append(hub.to_dict())  # Convert Series to dict
    
    for customer, hubs in customer_hubs.items():
        # Calculate total orders and analyze package size distribution for this customer
        total_customer_orders = sum([hub['order_count'] for hub in hubs])
        
        # Analyze package size distribution across all hubs for this customer
        customer_package_profile = analyze_customer_package_profile(customer, hubs)
        
        # Smart vehicle selection based on customer profile, order volume, and package sizes
        customer_lower = str(customer).lower()
        if 'herbalife' in customer_lower or 'nutrition' in customer_lower:
            customer_type = 'B2B_Large'
            preferred_vehicle = 'mini_truck'  # Always use mini truck for B2B large
            consolidation_factor = 0.9
        elif 'trent' in customer_lower or 'westside' in customer_lower or any(retail in customer_lower for retail in ['retail', 'store', 'mart']):
            customer_type = 'B2B_Retail'
            # Check if XL/XXL packages require larger vehicles
            if customer_package_profile['has_xl_xxl']:
                preferred_vehicle = 'mini_truck' if total_customer_orders > 100 else 'auto'
            else:
                preferred_vehicle = 'auto' if total_customer_orders <= 40 else 'mini_truck'
            consolidation_factor = 0.7
        else:
            customer_type = 'General'
            # Package size determines minimum vehicle requirement
            if customer_package_profile['has_xxl']:
                preferred_vehicle = 'mini_truck'
            elif customer_package_profile['has_xl']:
                preferred_vehicle = 'auto'
            elif total_customer_orders <= 30:
                preferred_vehicle = 'bike'
            elif total_customer_orders <= 45:
                preferred_vehicle = 'auto'
            else:
                preferred_vehicle = 'mini_truck'
            consolidation_factor = 0.6
        
        # Smart scheduling with package size optimization
        customer_cost = 0
        scheduled_trips = []
        
        if len(hubs) == 1:
            # Single hub - optimize based on package constraints
            hub = hubs[0]
            orders = hub['order_count']
            
            # Analyze package size distribution for this hub
            hub_package_profile = get_hub_package_profile(hub)
            
            # Find nearest big warehouse
            min_distance = float('inf')
            nearest_warehouse = None
            for warehouse in big_warehouses:
                distance = ((hub['pickup_lat'] - warehouse['lat'])**2 + (hub['pickup_long'] - warehouse['lon'])**2)**0.5 * 111
                if distance < min_distance:
                    min_distance = distance
                    nearest_warehouse = warehouse
            
            # Determine optimal vehicle based on package constraints
            optimal_vehicle = determine_optimal_vehicle_for_packages(
                orders, hub_package_profile, vehicle_specs, preferred_vehicle
            )
            
            trips_needed = 1  # Single trip optimization
            vehicle_type = optimal_vehicle['type']
            cost_per_trip = vehicle_specs[vehicle_type]['cost']
            
            # Calculate efficiency based on both order count and package volume
            order_efficiency = min(orders / vehicle_specs[vehicle_type]['order_capacity'], 1.0)
            volume_efficiency = calculate_volume_efficiency(hub_package_profile, vehicle_specs[vehicle_type], package_volumes)
            overall_efficiency = min(order_efficiency, volume_efficiency)
            
            hub_cost = trips_needed * cost_per_trip
            customer_cost += hub_cost
            
            scheduled_trips.append({
                'trip_id': f"{customer[:10]}_T1",
                'hubs': [hub['pickup']],
                'orders': orders,
                'vehicle': vehicle_type,
                'cost': hub_cost,
                'order_efficiency': f"{order_efficiency*100:.1f}%",
                'volume_efficiency': f"{volume_efficiency*100:.1f}%",
                'overall_efficiency': f"{overall_efficiency*100:.1f}%",
                'distance': min_distance,
                'warehouse': f"IF Hub {nearest_warehouse['id']}" if nearest_warehouse else "Unknown",
                'package_profile': hub_package_profile,
                'vehicle_rationale': f"Selected {vehicle_type} for {hub_package_profile['dominant_size']} packages"
            })
            
        else:
            # Multiple hubs - proximity-based clubbing with smart consolidation
            # First, create proximity clusters based on geographic distance
            proximity_clusters = create_proximity_clusters(hubs, max_cluster_radius_km=FIRST_MILE_CONFIG['proximity_radius_km'])
            
            trip_counter = 1
            for cluster in proximity_clusters:
                # For each cluster, group by nearest warehouse
                warehouse_groups = {}
                
                for hub in cluster:
                    # Find nearest warehouse for each hub
                    min_distance = float('inf')
                    nearest_warehouse = None
                    for warehouse in big_warehouses:
                        distance = ((hub['pickup_lat'] - warehouse['lat'])**2 + (hub['pickup_long'] - warehouse['lon'])**2)**0.5 * 111
                        if distance < min_distance:
                            min_distance = distance
                            nearest_warehouse = warehouse
                    
                    warehouse_id = nearest_warehouse['id'] if nearest_warehouse else 'unknown'
                    if warehouse_id not in warehouse_groups:
                        warehouse_groups[warehouse_id] = []
                    warehouse_groups[warehouse_id].append({
                        'hub': hub,
                        'distance': min_distance,
                        'warehouse': nearest_warehouse,
                        'package_profile': get_hub_package_profile(hub)
                    })
                
                # Optimize trips for each warehouse group within the proximity cluster
                for warehouse_id, group_hubs in warehouse_groups.items():
                    remaining_hubs = group_hubs.copy()
                    
                    while remaining_hubs:
                        # Start with the hub having most orders (anchor point)
                        remaining_hubs.sort(key=lambda x: x['hub']['order_count'], reverse=True)
                        
                        # Get anchor hub (highest volume)
                        anchor_hub = remaining_hubs[0]
                        current_trip_hubs_info = [anchor_hub]
                        remaining_hubs.remove(anchor_hub)
                        
                        # Add nearby hubs within proximity radius
                        max_trip_radius_km = FIRST_MILE_CONFIG['max_trip_radius_km']  # Maximum radius for a single trip
                        hubs_to_remove = []
                        
                        for hub_info in remaining_hubs:
                            # Calculate distance from anchor hub
                            distance_from_anchor = calculate_distance(
                                anchor_hub['hub']['pickup_lat'], anchor_hub['hub']['pickup_long'],
                                hub_info['hub']['pickup_lat'], hub_info['hub']['pickup_long']
                            )
                            
                            if distance_from_anchor <= max_trip_radius_km:
                                current_trip_hubs_info.append(hub_info)
                                hubs_to_remove.append(hub_info)
                        
                        # Remove hubs added to current trip
                        for hub_info in hubs_to_remove:
                            remaining_hubs.remove(hub_info)
                        
                        # Now optimize vehicle selection for this proximity-based trip
                        total_trip_orders = sum([h['hub']['order_count'] for h in current_trip_hubs_info])
                        combined_package_profile = combine_package_profiles([h['package_profile'] for h in current_trip_hubs_info])
                        
                        # Smart vehicle selection based on actual order volume (not customer type)
                        optimal_vehicle = determine_optimal_vehicle_by_volume(
                            total_trip_orders, combined_package_profile, vehicle_specs
                        )
                        
                        vehicle_type = optimal_vehicle['type']
                        cost_per_trip = vehicle_specs[vehicle_type]['cost']
                        
                        # Calculate trip details
                        current_trip_orders = total_trip_orders
                        current_trip_volume = sum([calculate_hub_volume(h['package_profile'], package_volumes) for h in current_trip_hubs_info])
                        current_trip_hubs = [h['hub']['pickup'] for h in current_trip_hubs_info]
                        current_trip_distance = max([h['distance'] for h in current_trip_hubs_info])
                        
                        # Calculate efficiency
                        order_capacity = vehicle_specs[vehicle_type]['order_capacity']
                        volume_capacity = vehicle_specs[vehicle_type]['volume_limit']
                        order_efficiency = min(current_trip_orders / order_capacity, 1.0) if order_capacity > 0 else 0
                        volume_efficiency = min(current_trip_volume / volume_capacity, 1.0) if volume_capacity > 0 else 0
                        overall_efficiency = min(order_efficiency, volume_efficiency)
                        
                        trip_cost = cost_per_trip
                        customer_cost += trip_cost
                        
                        # Calculate trip geographic span
                        trip_span_km = 0
                        if len(current_trip_hubs_info) > 1:
                            coords = [(h['hub']['pickup_lat'], h['hub']['pickup_long']) for h in current_trip_hubs_info]
                            max_distance = 0
                            for i, coord1 in enumerate(coords):
                                for j, coord2 in enumerate(coords):
                                    if i < j:
                                        dist = calculate_distance(coord1[0], coord1[1], coord2[0], coord2[1])
                                        max_distance = max(max_distance, dist)
                            trip_span_km = max_distance
                        
                        scheduled_trips.append({
                            'trip_id': f"{customer[:10]}_T{trip_counter}",
                            'hubs': current_trip_hubs,
                            'orders': current_trip_orders,
                            'vehicle': vehicle_type,
                            'cost': trip_cost,
                            'order_efficiency': f"{order_efficiency*100:.1f}%",
                            'volume_efficiency': f"{volume_efficiency*100:.1f}%",
                            'overall_efficiency': f"{overall_efficiency*100:.1f}%",
                            'distance': current_trip_distance,
                            'trip_span_km': f"{trip_span_km:.1f}",
                            'warehouse': f"IF Hub {warehouse_id}",
                            'volume_used': f"{current_trip_volume:.2f}m³",
                            'package_mix': get_package_mix_summary(current_trip_hubs),
                            'proximity_optimized': len(current_trip_hubs) > 1,
                            'vehicle_rationale': optimal_vehicle['rationale']
                        })
                        
                        trip_counter += 1
        
        total_first_mile_cost += customer_cost
        
        # Add customer summary to details
        first_mile_details.append({
            'customer': customer,
            'customer_type': customer_type,
            'total_orders': total_customer_orders,
            'total_hubs': len(hubs),
            'total_trips': len(scheduled_trips),
            'total_cost': customer_cost,
            'cost_per_order': customer_cost / total_customer_orders if total_customer_orders > 0 else 0,
            'preferred_vehicle': preferred_vehicle,
            'consolidation_factor': consolidation_factor,
            'package_profile': customer_package_profile,
            'scheduled_trips': scheduled_trips
        })
    
    return total_first_mile_cost, first_mile_details

def analyze_customer_package_profile(customer, hubs):
    """Analyze package size distribution for a customer across all their hubs"""
    # This would need actual package_size data from the dataset
    # For now, we'll create intelligent defaults based on customer type
    
    customer_lower = str(customer).lower()
    if 'herbalife' in customer_lower or 'nutrition' in customer_lower:
        return {
            'dominant_size': 'Medium',
            'has_xl_xxl': False,
            'has_xl': False,
            'has_xxl': False,
            'size_distribution': {'Small': 0.2, 'Medium': 0.6, 'Large': 0.2}
        }
    elif 'trent' in customer_lower or 'westside' in customer_lower:
        return {
            'dominant_size': 'Large',
            'has_xl_xxl': True,
            'has_xl': True,
            'has_xxl': False,
            'size_distribution': {'Small': 0.1, 'Medium': 0.3, 'Large': 0.4, 'XL': 0.2}
        }
    else:
        return {
            'dominant_size': 'Medium',
            'has_xl_xxl': False,
            'has_xl': False,
            'has_xxl': False,
            'size_distribution': {'Small': 0.3, 'Medium': 0.5, 'Large': 0.2}
        }

def get_hub_package_profile(hub):
    """Get package profile for a specific hub"""
    # Extract from hub data if available, otherwise use customer defaults
    hub_name = str(hub.get('pickup', '')).lower()
    
    # Smart defaults based on hub characteristics
    if any(keyword in hub_name for keyword in ['warehouse', 'distribution', 'dc']):
        return {
            'dominant_size': 'Large',
            'has_xl_xxl': True,
            'has_xl': True,
            'has_xxl': True,
            'size_distribution': {'Small': 0.1, 'Medium': 0.2, 'Large': 0.3, 'XL': 0.3, 'XXL': 0.1}
        }
    elif any(keyword in hub_name for keyword in ['store', 'retail', 'shop']):
        return {
            'dominant_size': 'Medium',
            'has_xl_xxl': True,
            'has_xl': True,
            'has_xxl': False,
            'size_distribution': {'Small': 0.2, 'Medium': 0.4, 'Large': 0.3, 'XL': 0.1}
        }
    else:
        return {
            'dominant_size': 'Small',
            'has_xl_xxl': False,
            'has_xl': False,
            'has_xxl': False,
            'size_distribution': {'Small': 0.4, 'Medium': 0.4, 'Large': 0.2}
        }

def determine_optimal_vehicle_for_packages(orders, package_profile, vehicle_specs, preferred_vehicle):
    """Determine optimal vehicle based on order count and package constraints"""
    
    # First check package size constraints
    if package_profile['has_xxl']:
        min_required_vehicle = 'mini_truck'
    elif package_profile['has_xl']:
        min_required_vehicle = 'auto'
    else:
        min_required_vehicle = 'bike'
    
    # Vehicle hierarchy
    vehicle_hierarchy = ['bike', 'auto', 'mini_truck']
    
    # Get minimum vehicle index
    min_vehicle_idx = vehicle_hierarchy.index(min_required_vehicle)
    preferred_vehicle_idx = vehicle_hierarchy.index(preferred_vehicle)
    
    # Use the higher requirement between package constraint and preferred vehicle
    selected_vehicle_idx = max(min_vehicle_idx, preferred_vehicle_idx)
    selected_vehicle = vehicle_hierarchy[selected_vehicle_idx]
    
    return {
        'type': selected_vehicle,
        'rationale': f"Package sizes require {min_required_vehicle}, customer profile suggests {preferred_vehicle}"
    }

def calculate_volume_efficiency(package_profile, vehicle_spec, package_volumes):
    """Calculate how efficiently the vehicle volume is used"""
    total_volume_needed = 0
    
    for size, percentage in package_profile['size_distribution'].items():
        if size in package_volumes:
            # Estimate number of packages of this size (simplified)
            estimated_packages = percentage * 100  # Assume 100 total packages for calculation
            total_volume_needed += estimated_packages * package_volumes[size]
    
    volume_efficiency = min(total_volume_needed / vehicle_spec['volume_limit'], 1.0) if vehicle_spec['volume_limit'] > 0 else 0
    return volume_efficiency

def calculate_hub_volume(package_profile, package_volumes):
    """Calculate total volume for a hub based on its package profile"""
    total_volume = 0
    
    for size, percentage in package_profile['size_distribution'].items():
        if size in package_volumes:
            # Estimate packages (simplified - in real implementation, use actual data)
            estimated_packages = percentage * 50  # Assume 50 packages per hub
            total_volume += estimated_packages * package_volumes[size]
    
    return total_volume

def vehicle_can_handle_packages(vehicle_spec, package_profile):
    """Check if vehicle can handle the package sizes"""
    for size in package_profile['size_distribution'].keys():
        if size not in vehicle_spec['allowed_sizes']:
            return False
    return True

def combine_package_profiles(profiles):
    """Combine multiple package profiles for trip optimization"""
    combined = {
        'dominant_size': 'Medium',
        'has_xl_xxl': any(p['has_xl_xxl'] for p in profiles),
        'has_xl': any(p['has_xl'] for p in profiles),
        'has_xxl': any(p['has_xxl'] for p in profiles),
        'size_distribution': {}
    }
    
    # Average the size distributions
    all_sizes = set()
    for profile in profiles:
        all_sizes.update(profile['size_distribution'].keys())
    
    for size in all_sizes:
        total_percentage = sum(p['size_distribution'].get(size, 0) for p in profiles)
        combined['size_distribution'][size] = total_percentage / len(profiles)
    
    # Determine dominant size
    if combined['size_distribution']:
        combined['dominant_size'] = max(combined['size_distribution'], key=combined['size_distribution'].get)
    
    return combined

def get_package_mix_summary(hub_names):
    """Get a summary of package mix for display"""
    # Simplified - in real implementation, analyze actual package data
    if len(hub_names) > 1:
        return "Mixed sizes"
    else:
        return "Standard mix"

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers"""
    return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5 * 111

def create_proximity_clusters(hubs, max_cluster_radius_km=FIRST_MILE_CONFIG['proximity_radius_km']):
    """Create proximity-based clusters of hubs for efficient trip planning"""
    if not hubs:
        return []
    
    clusters = []
    remaining_hubs = hubs.copy()
    
    while remaining_hubs:
        # Start a new cluster with the first remaining hub
        cluster_seed = remaining_hubs.pop(0)
        current_cluster = [cluster_seed]
        
        # Find all hubs within radius of the seed
        hubs_to_remove = []
        for hub in remaining_hubs:
            distance = calculate_distance(
                cluster_seed['pickup_lat'], cluster_seed['pickup_long'],
                hub['pickup_lat'], hub['pickup_long']
            )
            
            if distance <= max_cluster_radius_km:
                current_cluster.append(hub)
                hubs_to_remove.append(hub)
        
        # Remove clustered hubs from remaining list
        for hub in hubs_to_remove:
            remaining_hubs.remove(hub)
        
        clusters.append(current_cluster)
    
    return clusters

def determine_optimal_vehicle_by_volume(total_orders, package_profile, vehicle_specs):
    """Determine optimal vehicle based purely on order volume and package constraints"""
    
    # First check package size constraints
    if package_profile['has_xxl']:
        min_required_vehicle = 'mini_truck'
    elif package_profile['has_xl']:
        min_required_vehicle = 'auto'
    else:
        min_required_vehicle = 'bike'
    
    # Then check volume requirements with updated capacities
    if total_orders <= 80 and min_required_vehicle == 'bike':
        volume_recommended = 'bike'
    elif total_orders <= 120 and min_required_vehicle in ['bike', 'auto']:
        volume_recommended = 'auto'
    else:
        volume_recommended = 'mini_truck'
    
    # Vehicle hierarchy for selection
    vehicle_hierarchy = ['bike', 'auto', 'mini_truck']
    
    # Use the higher requirement between package constraint and volume requirement
    min_vehicle_idx = vehicle_hierarchy.index(min_required_vehicle)
    volume_vehicle_idx = vehicle_hierarchy.index(volume_recommended)
    
    selected_vehicle_idx = max(min_vehicle_idx, volume_vehicle_idx)
    selected_vehicle = vehicle_hierarchy[selected_vehicle_idx]
    
    return {
        'type': selected_vehicle,
        'rationale': f"Volume: {total_orders} orders requires {volume_recommended}, packages require {min_required_vehicle}"
    }

def get_package_indicator(package_profile):
    """Get visual indicator for package profile"""
    if package_profile['has_xxl']:
        return "📦📦📦 (Has XXL)"
    elif package_profile['has_xl']:
        return "📦📦 (Has XL)"
    else:
        return "📦 (S/M/L only)"

def calculate_middle_mile_costs(big_warehouses, feeder_warehouses):
    """Calculate middle mile costs for same-day delivery operations with realistic circuits"""
    
    # Same-day delivery middle mile specs (optimized for speed, not bulk)
    hub_to_feeder_vehicle = {
        'capacity': 80,   # orders per circuit (smaller for same-day speed)
        'cost': 1200,     # cost per circuit (shorter routes, faster vehicles)
        'circuits_per_day': 2  # 2 circuits per day for same-day delivery
    }
    
    # Inter-hub relay specs (for load balancing and overflow)
    inter_hub_relay = {
        'capacity': 60,   # orders per relay trip
        'cost': 1500,     # cost per relay trip
        'frequency': 2    # 2 relays per day between main hub pairs
    }
    
    total_middle_mile_cost = 0
    middle_mile_details = []
    
    # Hub to Auxiliary warehouse distribution costs (one vehicle per hub doing multiple trips)
    # Group auxiliaries by parent hub
    hub_auxiliaries = {}
    for aux in feeder_warehouses:
        parent_id = aux['parent']
        if parent_id not in hub_auxiliaries:
            hub_auxiliaries[parent_id] = []
        hub_auxiliaries[parent_id].append(aux)
    
    for hub_id, auxiliaries in hub_auxiliaries.items():
        parent_hub = next((hub for hub in big_warehouses if hub['id'] == hub_id), None)
        if not parent_hub:
            continue
            
        # Use centralized hub naming
        hub_code = HUB_NAMES.get(hub_id, f'HUB{hub_id}')
        
        # Calculate total workload for this hub's auxiliaries
        total_current_orders = sum([aux.get('coverage_orders', aux.get('orders_within_radius', 0)) for aux in auxiliaries])
        total_theoretical_capacity = sum([aux['capacity'] for aux in auxiliaries])
        
        # One vehicle per hub doing multiple trips
        # Determine vehicle type using centralized configuration
        avg_distance = sum([aux['distance_to_parent'] for aux in auxiliaries]) / len(auxiliaries)
        max_distance = max([aux['distance_to_parent'] for aux in auxiliaries])
        
        # Apply vehicle selection rules from config
        if total_theoretical_capacity <= HUB_AUX_CONFIG['vehicle_selection_rules']['small']['capacity_threshold'] and \
           max_distance <= HUB_AUX_CONFIG['vehicle_selection_rules']['small']['distance_threshold']:
            vehicle_type = HUB_AUX_CONFIG['vehicle_selection_rules']['small']['vehicle']
        elif total_theoretical_capacity <= HUB_AUX_CONFIG['vehicle_selection_rules']['medium']['capacity_threshold'] and \
             max_distance <= HUB_AUX_CONFIG['vehicle_selection_rules']['medium']['distance_threshold']:
            vehicle_type = HUB_AUX_CONFIG['vehicle_selection_rules']['medium']['vehicle']
        else:
            vehicle_type = HUB_AUX_CONFIG['vehicle_selection_rules']['large']['vehicle']
        
        # Get specs from centralized config
        vehicle_capacity = VEHICLE_SPECS[vehicle_type]['order_capacity']
        base_vehicle_cost = VEHICLE_COSTS[vehicle_type]
        
        # Calculate vehicles needed based on capacity scaling
        vehicles_needed = math.ceil(total_theoretical_capacity / CAPACITY_SCALING['orders_per_vehicle_threshold'])
        vehicles_needed = max(1, min(vehicles_needed, CAPACITY_SCALING['max_vehicles_per_hub']))
        
        # Calculate trips needed per vehicle based on current orders (for costing)
        total_capacity_available = vehicles_needed * vehicle_capacity
        trips_per_vehicle = math.ceil(total_current_orders / (vehicles_needed * vehicle_capacity)) if total_current_orders > 0 else 1
        trips_per_vehicle = max(1, min(trips_per_vehicle, HUB_AUX_CONFIG['max_trips_per_day']))
        
        # Calculate cost (multiple vehicles doing trips)
        cost_per_vehicle = trips_per_vehicle * base_vehicle_cost * CAPACITY_SCALING['vehicle_cost_multiplier']
        daily_cost = vehicles_needed * cost_per_vehicle
        monthly_cost = daily_cost * 30
        total_middle_mile_cost += monthly_cost
        
        # Calculate efficiency  
        total_trip_capacity = vehicles_needed * trips_per_vehicle * vehicle_capacity
        current_efficiency = (total_current_orders / total_trip_capacity) * 100 if total_current_orders > 0 else 0
        theoretical_efficiency = (total_theoretical_capacity / total_trip_capacity) * 100
        
        # Add details for this hub's auxiliary network
        aux_names = []
        for i, aux in enumerate(auxiliaries, 1):
            aux_name = f"{hub_code}-AX{i}"
            aux_names.append(aux_name)
            # Update auxiliary warehouse with new naming
            aux['hub_code'] = hub_code
            aux['aux_name'] = aux_name
            aux['vehicle_assigned'] = vehicle_type
        
        middle_mile_details.append({
            'hub_code': hub_code,
            'route': f"{hub_code} → {', '.join(aux_names)}",
            'auxiliaries_count': len(auxiliaries),
            'avg_distance_km': avg_distance,
            'max_distance_km': max_distance,
            'current_orders': total_current_orders,
            'theoretical_capacity': total_theoretical_capacity,
            'vehicles_needed': vehicles_needed,
            'vehicle_type': vehicle_type,
            'vehicle_capacity': vehicle_capacity,
            'trips_per_vehicle': trips_per_vehicle,
            'total_daily_capacity': total_trip_capacity,
            'current_efficiency': f"{current_efficiency:.1f}%",
            'theoretical_efficiency': f"{theoretical_efficiency:.1f}%",
            'daily_cost': daily_cost,
            'monthly_cost': monthly_cost,
            'auxiliaries': aux_names,
            'scaling_reason': f"Needs {vehicles_needed} vehicle(s) for {total_theoretical_capacity} capacity (>500 threshold)"
        })
    
    # Inter-hub relay costs (optimized multi-node routes using OpenStreetMap)
    inter_hub_cost = 0
    inter_hub_details = []
    
    if len(big_warehouses) > 1:
        print("🗺️ Calculating optimal inter-hub routes using OpenStreetMap...")
        
        # Calculate optimal multi-node routes
        optimal_routes = calculate_optimal_multi_node_routes(big_warehouses)
        
        for route_info in optimal_routes:
            route_sequence = route_info['route_sequence']
            total_distance = route_info['total_distance']
            total_time = route_info['total_time']
            route_type = route_info['route_type']
            
            # Determine vehicle type based on total route distance
            if total_distance <= INTER_HUB_CONFIG['distance_rules']['short']['max_distance']:
                relay_vehicle = INTER_HUB_CONFIG['distance_rules']['short']['vehicle']
            elif total_distance <= INTER_HUB_CONFIG['distance_rules']['medium']['max_distance']:
                relay_vehicle = INTER_HUB_CONFIG['distance_rules']['medium']['vehicle']
            else:
                relay_vehicle = INTER_HUB_CONFIG['distance_rules']['long']['vehicle']
            
            # Get specs from centralized config
            relay_cost = VEHICLE_COSTS[relay_vehicle]
            relay_capacity = VEHICLE_SPECS[relay_vehicle]['order_capacity']
            trips_per_day = INTER_HUB_CONFIG['trips_per_day']
            
            # Calculate cost
            daily_relay_cost = trips_per_day * relay_cost
            monthly_relay_cost = daily_relay_cost * 30
            inter_hub_cost += monthly_relay_cost
            
            # Create route description
            hub_codes = [HUB_NAMES.get(hid, f"HUB{hid}") for hid in route_sequence]
            
            if route_type == 'circular':
                route_desc = ' → '.join(hub_codes)
                purpose = f"Circular route connecting {len(route_sequence)-1} hubs"
                examples = f"Efficient multi-stop: {hub_codes[0]} → {hub_codes[1]} → {hub_codes[2]} → back to {hub_codes[0]}"
            else:
                route_desc = f"{hub_codes[0]} ↔ {hub_codes[1]}"
                purpose = "Direct point-to-point connection"
                examples = f"Enables: {hub_codes[0]} pickups → {hub_codes[1]} delivery"
            
            inter_hub_details.append({
                'route': route_desc,
                'route_type': route_type.replace('_', ' ').title(),
                'hubs_connected': len(route_sequence) if route_type == 'point_to_point' else len(route_sequence) - 1,
                'total_distance_km': total_distance,
                'total_time_min': total_time,
                'vehicle_type': relay_vehicle,
                'trips_per_day': trips_per_day,
                'capacity_per_trip': relay_capacity,
                'trip_cost': relay_cost,
                'relay_purpose': purpose,
                'daily_cost': daily_relay_cost,
                'monthly_cost': monthly_relay_cost,
                'examples': examples,
                'efficiency_score': route_info['efficiency_score']
            })
        
        print(f"✅ Created {len(optimal_routes)} optimized relay routes using OpenStreetMap routing")
    
    total_middle_mile_cost += inter_hub_cost
    
    return total_middle_mile_cost, middle_mile_details, inter_hub_details

def calculate_last_mile_costs(df_filtered, big_warehouses, feeder_warehouses, delivery_radius=2, vehicle_mix='auto_heavy'):
    """Calculate last mile delivery costs from closest warehouse (hub or feeder) for each order"""
    
    # Get vehicle mix configuration
    mix_config = LAST_MILE_CONFIG['vehicle_mix_options'].get(vehicle_mix, LAST_MILE_CONFIG['vehicle_mix_options']['auto_heavy'])
    bike_percentage = mix_config['bike']
    auto_percentage = mix_config['auto']
    
    # Cost per order for each vehicle type
    bike_cost_per_order = LAST_MILE_CONFIG['cost_per_order_bike']
    auto_cost_per_order = LAST_MILE_CONFIG['cost_per_order_auto']
    
    # Calculate for ALL orders in the dataset
    total_orders = len(df_filtered)
    
    if total_orders == 0:
        return 0, []
    
    # Combine all warehouses (hubs + feeders) for closest warehouse calculation
    all_warehouses = []
    
    # Add hub warehouses
    for hub in big_warehouses:
        all_warehouses.append({
            'lat': hub['lat'],
            'lon': hub['lon'],
            'type': 'hub',
            'id': hub.get('id', 'unknown'),
            'name': hub.get('hub_code', f"HUB{hub.get('id', '?')}")
        })
    
    # Add feeder warehouses
    for feeder in feeder_warehouses:
        all_warehouses.append({
            'lat': feeder['lat'],
            'lon': feeder['lon'],
            'type': 'feeder',
            'id': feeder.get('id', 'unknown'),
            'name': feeder.get('aux_name', f"AX{feeder.get('id', '?')}")
        })
    
    # Calculate delivery distance from closest warehouse for each order
    all_distances = []
    orders_per_warehouse = {'hub': 0, 'feeder': 0}
    warehouse_assignments = {}
    
    for _, order in df_filtered.iterrows():
        order_lat, order_lon = order['order_lat'], order['order_long']
        
        # Find closest warehouse (hub or feeder)
        min_distance = float('inf')
        closest_warehouse = None
        
        for warehouse in all_warehouses:
            distance = ((order_lat - warehouse['lat'])**2 + (order_lon - warehouse['lon'])**2)**0.5 * 111
            if distance < min_distance:
                min_distance = distance
                closest_warehouse = warehouse
        
        if closest_warehouse:
            all_distances.append(min_distance)
            orders_per_warehouse[closest_warehouse['type']] += 1
            
            # Track which warehouse serves this order
            wh_key = f"{closest_warehouse['type']}_{closest_warehouse['name']}"
            if wh_key not in warehouse_assignments:
                warehouse_assignments[wh_key] = {'orders': 0, 'distances': []}
            warehouse_assignments[wh_key]['orders'] += 1
            warehouse_assignments[wh_key]['distances'].append(min_distance)
        else:
            # Fallback if no warehouse found
            all_distances.append(delivery_radius * 0.7)
    
    avg_distance_all = sum(all_distances) / len(all_distances) if all_distances else delivery_radius * 0.7
    
    # Apply distance-based vehicle mix adjustments
    if avg_distance_all <= LAST_MILE_CONFIG['distance_rules']['bike_preferred']:
        adjusted_bike_percentage = min(0.8, bike_percentage + 0.2)
        adjusted_auto_percentage = 1.0 - adjusted_bike_percentage
    elif avg_distance_all >= LAST_MILE_CONFIG['distance_rules']['auto_preferred']:
        adjusted_auto_percentage = min(0.8, auto_percentage + 0.2)
        adjusted_bike_percentage = 1.0 - adjusted_auto_percentage
    else:
        adjusted_bike_percentage = bike_percentage
        adjusted_auto_percentage = auto_percentage
    
    # Calculate total orders per vehicle type
    total_bike_orders = int(total_orders * adjusted_bike_percentage)
    total_auto_orders = total_orders - total_bike_orders
    
    # Calculate total monthly costs for all orders
    total_bike_monthly_cost = total_bike_orders * bike_cost_per_order * 30  # 30 days
    total_auto_monthly_cost = total_auto_orders * auto_cost_per_order * 30  # 30 days
    total_last_mile_cost = total_bike_monthly_cost + total_auto_monthly_cost
    
    # Calculate weighted average cost per order
    avg_cost_per_order = (total_bike_orders * bike_cost_per_order + total_auto_orders * auto_cost_per_order) / total_orders
    
    # Create summary details for display
    last_mile_details = [{
        'feeder_id': 'CLOSEST_WAREHOUSE',
        'hub_code': 'NETWORK',
        'aux_name': 'ALL_WAREHOUSES',
        'orders': total_orders,
        'orders_from_hubs': orders_per_warehouse['hub'],
        'orders_from_feeders': orders_per_warehouse['feeder'],
        'bike_orders': total_bike_orders,
        'auto_orders': total_auto_orders,
        'bike_percentage': adjusted_bike_percentage * 100,
        'auto_percentage': adjusted_auto_percentage * 100,
        'avg_distance': avg_distance_all,
        'max_distance': max(all_distances) if all_distances else delivery_radius,
        'bike_monthly_cost': total_bike_monthly_cost,
        'auto_monthly_cost': total_auto_monthly_cost,
        'total_monthly_cost': total_last_mile_cost,
        'avg_cost_per_order': avg_cost_per_order,
        'vehicle_mix_used': vehicle_mix,
        'warehouse_breakdown': warehouse_assignments
    }]
    
    return total_last_mile_cost, last_mile_details

def show_network_analysis(df_filtered, big_warehouses, feeder_warehouses, big_warehouse_count, total_feeders, total_orders_in_radius, coverage_percentage, delivery_radius=2, vehicle_mix='auto_heavy'):
    """Show comprehensive network analysis including detailed cost breakdown"""
    
    st.subheader("📊 Blowhorn IF Network Analysis")
    
    # Get pickup hubs data for cost calculation with customer information
    if 'customer' in df_filtered.columns:
        pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat', 'customer']).size().reset_index(name='order_count')
    else:
        pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
        pickup_hubs['customer'] = 'Unknown Customer'  # Add default customer column
    
    # Calculate costs
    first_mile_cost, first_mile_details = calculate_first_mile_costs(pickup_hubs, big_warehouses)
    middle_mile_cost, middle_mile_details, inter_hub_details = calculate_middle_mile_costs(big_warehouses, feeder_warehouses)
    last_mile_cost, last_mile_details = calculate_last_mile_costs(df_filtered, big_warehouses, feeder_warehouses, delivery_radius, vehicle_mix)
    
    # Create cost overview with 4 columns including last mile
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 💰 Daily First Mile Costs")
        st.metric("Total Daily Cost", f"₹{first_mile_cost:,.0f}")
        st.metric("Monthly Cost", f"₹{first_mile_cost * 30:,.0f}")
        st.write(f"**Pickup Hubs:** {len(pickup_hubs)}")
        st.write(f"**Avg Cost per Hub:** ₹{first_mile_cost / len(pickup_hubs):,.0f}")
    
    with col2:
        st.markdown("### 🚛 Same-Day Middle Mile Costs")
        hub_feeder_cost = middle_mile_cost - (sum([detail['monthly_cost'] for detail in inter_hub_details]) if inter_hub_details else 0)
        st.metric("Hub-Feeder Circuits", f"₹{hub_feeder_cost:,.0f}")
        if inter_hub_details:
            inter_hub_monthly = sum([detail['monthly_cost'] for detail in inter_hub_details])
            st.metric("Inter-Hub Relays", f"₹{inter_hub_monthly:,.0f}")
        st.metric("Total Middle Mile", f"₹{middle_mile_cost:,.0f}")
    
    with col3:
        st.markdown("### 🏍️ Last Mile Costs")
        st.metric("Monthly Last Mile", f"₹{last_mile_cost:,.0f}")
        
        # Display delivery source breakdown and vehicle mix
        if last_mile_details and last_mile_details[0]:
            detail = last_mile_details[0]
            total_orders = detail['orders']
            hub_orders = detail.get('orders_from_hubs', 0)
            feeder_orders = detail.get('orders_from_feeders', 0)
            
            # Show delivery sources
            st.write(f"**🏭 From Hubs:** {hub_orders:,} orders ({hub_orders/total_orders*100:.0f}%)")
            st.write(f"**📦 From Feeders:** {feeder_orders:,} orders ({feeder_orders/total_orders*100:.0f}%)")
            
            # Show vehicle mix
            bike_percent = detail['bike_percentage']
            auto_percent = detail['auto_percentage']
            st.write(f"**🏍️ Bikes:** {bike_percent:.0f}%")
            st.write(f"**🛺 Autos:** {auto_percent:.0f}%")
            
            # Show per-order cost
            avg_cost_per_order = detail['avg_cost_per_order']
            st.write(f"**Cost/Order:** ₹{avg_cost_per_order:.1f}")
        else:
            st.write("**Delivery Mix:** Not calculated")
    
    with col4:
        st.markdown("### 📈 Total Network")
        monthly_first_mile = first_mile_cost * 30
        total_logistics_cost = monthly_first_mile + middle_mile_cost + last_mile_cost
        st.metric("Total Monthly", f"₹{total_logistics_cost:,.0f}")
        
        # Correct CPO calculation: daily cost per order
        daily_total_cost = first_mile_cost + (middle_mile_cost / 30) + (last_mile_cost / 30)
        cost_per_order = daily_total_cost / len(df_filtered) if len(df_filtered) > 0 else 0
        st.metric("Current CPO", f"₹{cost_per_order:.1f}")
    
    # Leg-wise CPO Analysis - Current vs Full Capacity
    st.markdown("### 📊 Leg-wise CPO Analysis: Current Orders vs Full Capacity")
    
    # Calculate actual network capacity based on infrastructure built
    total_hub_capacity = sum([hub.get('capacity', 500) for hub in big_warehouses])
    total_feeder_capacity = sum([feeder.get('capacity', 150) for feeder in feeder_warehouses])
    current_orders = len(df_filtered)
    
    # True network capacity is the minimum bottleneck (hubs or feeders)
    network_capacity = min(total_hub_capacity, total_feeder_capacity)
    
    # Full capacity scenario uses the actual network capacity we built
    full_capacity_orders = network_capacity
    
    # Cost calculations at full capacity
    if current_orders > 0 and full_capacity_orders > current_orders:
        # First mile scales with order volume (more pickups needed)
        first_mile_scale_factor = full_capacity_orders / current_orders
        
        # Middle mile stays same (fixed infrastructure can handle the volume)
        # This is the key insight - middle mile doesn't scale linearly!
        
        # Last mile scales linearly with orders (more deliveries needed)
        last_mile_scale_factor = full_capacity_orders / current_orders
        
        # Calculate full capacity costs
        full_capacity_first_mile = (first_mile_cost * 30) * first_mile_scale_factor
        full_capacity_middle_mile = middle_mile_cost  # SAME - infrastructure handles it
        full_capacity_last_mile = last_mile_cost * last_mile_scale_factor
        full_capacity_total = full_capacity_first_mile + full_capacity_middle_mile + full_capacity_last_mile
        
    else:
        # Already at or beyond capacity
        full_capacity_first_mile = first_mile_cost * 30
        full_capacity_middle_mile = middle_mile_cost
        full_capacity_last_mile = last_mile_cost
        full_capacity_total = full_capacity_first_mile + full_capacity_middle_mile + full_capacity_last_mile
        
    # Create comparison table
    col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Current Scenario")
            # Calculate correct CPO - daily cost per order
            first_mile_daily_cpo = (monthly_first_mile / 30) / current_orders if current_orders > 0 else 0
            middle_mile_daily_cpo = (middle_mile_cost / 30) / current_orders if current_orders > 0 else 0  
            last_mile_daily_cpo = (last_mile_cost / 30) / current_orders if current_orders > 0 else 0
            total_daily_cpo = first_mile_daily_cpo + middle_mile_daily_cpo + last_mile_daily_cpo
            
            current_data = {
                "Mile": ["First Mile", "Middle Mile", "Last Mile", "**TOTAL**"],
                "Monthly Cost": [f"₹{monthly_first_mile:,.0f}", f"₹{middle_mile_cost:,.0f}", f"₹{last_mile_cost:,.0f}", f"**₹{total_logistics_cost:,.0f}**"],
                "CPO": [f"₹{first_mile_daily_cpo:.1f}", f"₹{middle_mile_daily_cpo:.1f}", f"₹{last_mile_daily_cpo:.1f}", f"**₹{total_daily_cpo:.1f}**"]
            }
            st.table(pd.DataFrame(current_data))
            st.write(f"🎯 **Current Orders:** {current_orders:,}")
            st.write(f"📊 **Network Utilization:** {(current_orders/network_capacity*100):.1f}%")
        
        with col2:
            st.markdown("#### 🚀 Full Capacity Scenario")
            # Calculate correct CPO for full capacity - daily cost per order
            full_first_mile_daily_cpo = (full_capacity_first_mile / 30) / full_capacity_orders if full_capacity_orders > 0 else 0
            full_middle_mile_daily_cpo = (full_capacity_middle_mile / 30) / full_capacity_orders if full_capacity_orders > 0 else 0
            full_last_mile_daily_cpo = (full_capacity_last_mile / 30) / full_capacity_orders if full_capacity_orders > 0 else 0
            full_total_daily_cpo = full_first_mile_daily_cpo + full_middle_mile_daily_cpo + full_last_mile_daily_cpo
            
            full_capacity_data = {
                "Mile": ["First Mile", "Middle Mile", "Last Mile", "**TOTAL**"],
                "Monthly Cost": [f"₹{full_capacity_first_mile:,.0f}", f"₹{full_capacity_middle_mile:,.0f}", f"₹{full_capacity_last_mile:,.0f}", f"**₹{full_capacity_total:,.0f}**"],
                "CPO": [f"₹{full_first_mile_daily_cpo:.1f}", f"₹{full_middle_mile_daily_cpo:.1f}", f"₹{full_last_mile_daily_cpo:.1f}", f"**₹{full_total_daily_cpo:.1f}**"]
            }
            st.table(pd.DataFrame(full_capacity_data))
            st.write(f"🎯 **Full Capacity Orders:** {full_capacity_orders:,}")
            st.write(f"💰 **CPO Improvement:** ₹{total_daily_cpo - full_total_daily_cpo:.1f} ({((total_daily_cpo - full_total_daily_cpo)/total_daily_cpo*100):.1f}% reduction)")
    
    
    # Simplified Key Metrics for Investors
    st.markdown("### 📊 Network Performance Metrics")
    
    # Key operational metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 Operational Summary")
        
        # Calculate key metrics
        total_trips = sum([detail['total_trips'] for detail in first_mile_details])
        total_customers = len(first_mile_details)
        avg_orders_per_trip = current_orders / total_trips if total_trips > 0 else 0
        avg_cost_per_trip = (first_mile_cost * 30) / total_trips if total_trips > 0 else 0
        
        # Simple metrics table
        metrics_data = {
            "Metric": ["Total Customers", "Daily Trips", "Avg Orders/Trip", "Avg Cost/Trip"],
            "Value": [f"{total_customers}", f"{total_trips}", f"{avg_orders_per_trip:.0f}", f"₹{avg_cost_per_trip:.0f}"]
        }
        st.table(pd.DataFrame(metrics_data))
    
    with col2:
        st.markdown("#### 🚛 Vehicle Breakdown") 
        
        # Calculate vehicle usage
        vehicle_usage = {'bike': 0, 'auto': 0, 'mini_truck': 0}
        for detail in first_mile_details:
            vehicle_usage[detail['preferred_vehicle']] += detail['total_trips']
        
        total_vehicle_trips = sum(vehicle_usage.values())
        
        # Vehicle usage table
        vehicle_data = []
        for vehicle, trips in vehicle_usage.items():
            if trips > 0:
                percentage = (trips / total_vehicle_trips) * 100
                vehicle_data.append({
                    "Vehicle": vehicle.replace('_', ' ').title(),
                    "Trips": f"{trips}",
                    "Percentage": f"{percentage:.0f}%"
                })
        
        if vehicle_data:
            st.table(pd.DataFrame(vehicle_data))
    
    # Simplified Customer Performance Table
    st.markdown("### 💼 Customer Performance Summary")
    
    # Create clean customer summary table
    customer_summary = []
    for detail in first_mile_details:
        customer_summary.append({
            'Customer': detail['customer'][:20] + '...' if len(detail['customer']) > 20 else detail['customer'],
            'Orders': f"{detail['total_orders']:,}",
            'Trips': f"{detail['total_trips']}",
            'CPO': f"₹{detail['cost_per_order']:.1f}",
            'Monthly Cost': f"₹{detail['monthly_cost']:,.0f}"
        })
    
    if customer_summary:
        st.table(pd.DataFrame(customer_summary))
    
    # Network utilization summary
    st.markdown("### 📊 Network Utilization Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🏭 Hub Utilization")
        avg_hub_utilization = (current_orders / total_hub_capacity) * 100 if total_hub_capacity > 0 else 0
        utilization_data = {
            "Metric": ["Hub Capacity", "Current Orders", "Utilization"],
            "Value": [f"{total_hub_capacity:,}", f"{current_orders:,}", f"{avg_hub_utilization:.1f}%"]
        }
        st.table(pd.DataFrame(utilization_data))
    
    with col2:
        st.markdown("#### 📦 Feeder Capacity")  
        avg_feeder_utilization = (current_orders / total_feeder_capacity) * 100 if total_feeder_capacity > 0 else 0
        feeder_data = {
            "Metric": ["Feeder Capacity", "Current Orders", "Utilization"],
            "Value": [f"{total_feeder_capacity:,}", f"{current_orders:,}", f"{avg_feeder_utilization:.1f}%"]
        }
        st.table(pd.DataFrame(feeder_data))
    
    with col3:
        st.markdown("#### 💰 Cost Efficiency")
        total_monthly_cost = monthly_first_mile + middle_mile_cost + last_mile_cost
        efficiency_data = {
            "Metric": ["Monthly Cost", "Orders", "CPO"],
            "Value": [f"₹{total_monthly_cost:,.0f}", f"{current_orders:,}", f"₹{total_daily_cpo:.1f}"]
        }
        st.table(pd.DataFrame(efficiency_data))
    
    # Middle Mile Summary
    st.markdown("### 🔄 Middle Mile Summary")
    
    if middle_mile_details:
        middle_mile_summary_data = {
            "Metric": ["Active Routes", "Monthly Cost", "Avg Cost/Route"],
            "Value": [
                f"{len(middle_mile_details)}",
                f"₹{middle_mile_cost:,.0f}",
                f"₹{middle_mile_cost/len(middle_mile_details):,.0f}"
            ]
        }
        st.table(pd.DataFrame(middle_mile_summary_data))
