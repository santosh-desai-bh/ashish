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

# PACKAGE DIMENSIONS (cubic centimeters converted to cubic meters)
PACKAGE_VOLUMES = {
    'Small': 125 / 1000000,      # 125 cm³ = 0.000125 m³
    'Medium': 1000 / 1000000,    # 1000 cm³ = 0.001 m³  
    'Large': 3375 / 1000000,     # 3375 cm³ = 0.003375 m³
    'XL': 10000 / 1000000,       # 10000 cm³ = 0.01 m³
    'XXL': 35000 / 1000000,      # 35000 cm³ = 0.035 m³
    'Unknown': 16000 / 1000000   # 16000 cm³ = 0.016 m³ (default assumption)
}

# CAPACITY SCALING - When orders exceed vehicle capacity, add more vehicles
CAPACITY_SCALING = {
    'orders_per_vehicle_threshold': 500,  # Above this, need additional vehicles
    'max_vehicles_per_hub': 3,           # Maximum vehicles per hub for auxiliaries
    'vehicle_cost_multiplier': 1.0       # Cost multiplier for additional vehicles (1.0 = same cost)
}

# CAPACITY EFFICIENCY FACTORS
LOADING_EFFICIENCY = {
    'space_utilization': 0.65,    # 65% space utilization due to irregular shapes
    'loading_time_factor': 0.8,   # 80% efficiency due to loading/unloading constraints
    'weight_distribution': 0.9,   # 90% efficiency for safe weight distribution
    'access_factor': 0.85         # 85% efficiency for practical access during delivery
}

# Combined loading efficiency
OVERALL_LOADING_EFFICIENCY = (
    LOADING_EFFICIENCY['space_utilization'] * 
    LOADING_EFFICIENCY['loading_time_factor'] * 
    LOADING_EFFICIENCY['weight_distribution'] * 
    LOADING_EFFICIENCY['access_factor']
)  # ≈ 40% overall efficiency

# VEHICLE CAPACITIES (Volume-based with realistic loading factors)
VEHICLE_SPECS = {
    'bike': {
        'theoretical_volume': 0.15,  # 150 liters theoretical capacity
        'practical_volume': 0.15 * OVERALL_LOADING_EFFICIENCY,  # ~60 liters practical
        'weight_limit_kg': 80,
        'allowed_sizes': ['Small', 'Medium', 'Large'],
        'size_capacity': {
            # Apply loading efficiency to theoretical calculations
            'Small': int((0.15 / PACKAGE_VOLUMES['Small']) * OVERALL_LOADING_EFFICIENCY),      # ~480 → realistic ~60-80
            'Medium': int((0.15 / PACKAGE_VOLUMES['Medium']) * OVERALL_LOADING_EFFICIENCY),    # ~60 → realistic ~40-50
            'Large': int((0.15 / PACKAGE_VOLUMES['Large']) * OVERALL_LOADING_EFFICIENCY),      # ~18 → realistic ~15-20
        },
        'practical_mixed_capacity': 80,  # Mixed package types - realistic limit
        'avg_orders_per_trip': 60        # Average considering package mix
    },
    'auto': {
        'theoretical_volume': 1.2,   # 1200 liters theoretical
        'practical_volume': 1.2 * OVERALL_LOADING_EFFICIENCY,  # ~480 liters practical
        'weight_limit_kg': 500,
        'allowed_sizes': ['Small', 'Medium', 'Large', 'XL'],
        'size_capacity': {
            'Small': int((1.2 / PACKAGE_VOLUMES['Small']) * OVERALL_LOADING_EFFICIENCY),       # ~3840 → realistic ~200-300
            'Medium': int((1.2 / PACKAGE_VOLUMES['Medium']) * OVERALL_LOADING_EFFICIENCY),     # ~480 → realistic ~120-150
            'Large': int((1.2 / PACKAGE_VOLUMES['Large']) * OVERALL_LOADING_EFFICIENCY),       # ~142 → realistic ~80-100
            'XL': int((1.2 / PACKAGE_VOLUMES['XL']) * OVERALL_LOADING_EFFICIENCY),             # ~48 → realistic ~25-35
        },
        'practical_mixed_capacity': 150,  # Mixed package types
        'avg_orders_per_trip': 120        # Average considering package mix
    },
    'mini_truck': {
        'theoretical_volume': 8.0,   # 8000 liters theoretical
        'practical_volume': 8.0 * OVERALL_LOADING_EFFICIENCY,  # ~3200 liters practical
        'weight_limit_kg': 1500,
        'allowed_sizes': ['Small', 'Medium', 'Large', 'XL', 'XXL'],
        'size_capacity': {
            'Small': int((8.0 / PACKAGE_VOLUMES['Small']) * OVERALL_LOADING_EFFICIENCY),       # ~25600 → realistic ~800-1200
            'Medium': int((8.0 / PACKAGE_VOLUMES['Medium']) * OVERALL_LOADING_EFFICIENCY),     # ~3200 → realistic ~400-600
            'Large': int((8.0 / PACKAGE_VOLUMES['Large']) * OVERALL_LOADING_EFFICIENCY),       # ~948 → realistic ~200-300
            'XL': int((8.0 / PACKAGE_VOLUMES['XL']) * OVERALL_LOADING_EFFICIENCY),             # ~320 → realistic ~80-120
            'XXL': int((8.0 / PACKAGE_VOLUMES['XXL']) * OVERALL_LOADING_EFFICIENCY),           # ~91 → realistic ~20-25 (matches your assumption!)
        },
        'practical_mixed_capacity': 300,  # Mixed package types
        'avg_orders_per_trip': 250        # Average considering package mix
    },
    'truck': {
        'theoretical_volume': 15.0,  # 15000 liters theoretical
        'practical_volume': 15.0 * OVERALL_LOADING_EFFICIENCY,  # ~6000 liters practical
        'weight_limit_kg': 3000,
        'allowed_sizes': ['Small', 'Medium', 'Large', 'XL', 'XXL'],
        'size_capacity': {
            'Small': int((15.0 / PACKAGE_VOLUMES['Small']) * OVERALL_LOADING_EFFICIENCY),      # ~48000 → realistic ~1500-2000
            'Medium': int((15.0 / PACKAGE_VOLUMES['Medium']) * OVERALL_LOADING_EFFICIENCY),    # ~6000 → realistic ~800-1200  
            'Large': int((15.0 / PACKAGE_VOLUMES['Large']) * OVERALL_LOADING_EFFICIENCY),      # ~1777 → realistic ~400-600
            'XL': int((15.0 / PACKAGE_VOLUMES['XL']) * OVERALL_LOADING_EFFICIENCY),            # ~600 → realistic ~150-200
            'XXL': int((15.0 / PACKAGE_VOLUMES['XXL']) * OVERALL_LOADING_EFFICIENCY),          # ~171 → realistic ~40-50
        },
        'practical_mixed_capacity': 500,  # Mixed package types
        'avg_orders_per_trip': 400        # Average considering package mix
    }
}

# WAREHOUSE CAPACITY ANALYSIS (Volume and operational efficiency based)
WAREHOUSE_CAPACITY_FACTORS = {
    'storage_density': 0.4,        # 40% of warehouse space usable for storage (rest for aisles, sorting, etc.)
    'storage_height_utilization': 0.7,  # 70% height utilization for safety and access
    'inventory_turnover': 0.8,     # 0.8 times per day (packages stored for ~1.25 days on average)
    'operational_efficiency': 0.8,  # 80% efficiency accounting for sorting, consolidation time
    'peak_capacity_buffer': 1.3    # 30% buffer for peak demand handling
}

# WAREHOUSE SPECIFICATIONS AND COSTS
WAREHOUSE_SPECS = {
    'main_microwarehouse': {
        'size_range_sqft': (700, 1000),     # 700-1000 sqft
        'monthly_rent_range': (30000, 40000), # ₹30-40k per month
        'avg_size_sqft': 850,               # Average size for calculations
        'avg_monthly_rent': 35000,          # Average rent
        'description': 'Main distribution hub with sorting and consolidation facilities'
    },
    'auxiliary_warehouse': {
        'size_range_sqft': (200, 500),      # 200-500 sqft
        'monthly_rent_range': (10000, 20000), # ₹10-20k per month
        'avg_size_sqft': 350,               # Average size for calculations
        'avg_monthly_rent': 15000,          # Average rent
        'description': 'Last-mile delivery point with basic storage and sorting'
    }
}

def calculate_realistic_warehouse_capacity(warehouse_sqft, package_mix_assumption=None, show_steps=False):
    """Calculate realistic warehouse capacity with detailed step-by-step breakdown"""
    
    # Default package mix assumption if not provided (based on typical e-commerce)
    if not package_mix_assumption:
        package_mix_assumption = {
            'Small': 0.3,    # 30% small packages
            'Medium': 0.25,  # 25% medium packages  
            'Large': 0.25,   # 25% large packages
            'XL': 0.15,      # 15% XL packages
            'XXL': 0.05      # 5% XXL packages
        }
    
    # Step-by-step calculation with detailed breakdown
    calculation_steps = []
    
    # Step 1: Calculate average package volume
    package_volume_calc = []
    total_weighted_volume = 0
    for size, ratio in package_mix_assumption.items():
        volume_m3 = PACKAGE_VOLUMES[size]
        volume_cm3 = volume_m3 * 1000000
        weighted_volume = volume_m3 * ratio
        total_weighted_volume += weighted_volume
        package_volume_calc.append({
            'size': size,
            'ratio': f"{ratio*100:.0f}%",
            'volume_cm3': f"{volume_cm3:.0f} cm³",
            'weighted_contribution': f"{weighted_volume*1000000:.0f} cm³"
        })
    
    avg_package_volume = total_weighted_volume
    calculation_steps.append({
        'step': 1,
        'description': 'Calculate Average Package Volume',
        'detail': package_volume_calc,
        'result': f"{avg_package_volume*1000000:.0f} cm³ per package"
    })
    
    # Step 2: Calculate warehouse dimensions and volume
    warehouse_area_m2 = warehouse_sqft * 0.092903  # sqft to m²
    warehouse_height_m = 4  # assume 4m height
    total_warehouse_volume_m3 = warehouse_area_m2 * warehouse_height_m
    
    calculation_steps.append({
        'step': 2,
        'description': 'Calculate Total Warehouse Volume',
        'detail': [
            {'component': 'Floor Area', 'value': f"{warehouse_sqft:,} sqft = {warehouse_area_m2:.1f} m²"},
            {'component': 'Height', 'value': f"{warehouse_height_m} m (standard warehouse height)"},
            {'component': 'Total Volume', 'value': f"{total_warehouse_volume_m3:.1f} m³"}
        ],
        'result': f"{total_warehouse_volume_m3:.1f} m³ total space"
    })
    
    # Step 3: Apply storage efficiency factors
    storage_efficiency_calc = []
    usable_volume = total_warehouse_volume_m3
    
    # Apply storage density (40% usable for storage)
    storage_density = WAREHOUSE_CAPACITY_FACTORS['storage_density']
    volume_after_density = usable_volume * storage_density
    storage_efficiency_calc.append({
        'factor': 'Storage Density',
        'percentage': f"{storage_density*100:.0f}%",
        'reason': 'Space for aisles, sorting areas, workstations',
        'volume_before': f"{usable_volume:.1f} m³",
        'volume_after': f"{volume_after_density:.1f} m³"
    })
    usable_volume = volume_after_density
    
    # Apply height utilization (70% of height)
    height_utilization = WAREHOUSE_CAPACITY_FACTORS['storage_height_utilization']
    volume_after_height = usable_volume * height_utilization
    storage_efficiency_calc.append({
        'factor': 'Height Utilization',
        'percentage': f"{height_utilization*100:.0f}%",
        'reason': 'Safe stacking height, access for picking',
        'volume_before': f"{usable_volume:.1f} m³",
        'volume_after': f"{volume_after_height:.1f} m³"
    })
    usable_volume = volume_after_height
    
    calculation_steps.append({
        'step': 3,
        'description': 'Apply Storage Efficiency Factors',
        'detail': storage_efficiency_calc,
        'result': f"{usable_volume:.1f} m³ usable storage volume"
    })
    
    # Step 4: Calculate theoretical package capacity
    theoretical_packages = int(usable_volume / avg_package_volume)
    calculation_steps.append({
        'step': 4,
        'description': 'Calculate Theoretical Package Storage',
        'detail': [
            {'calculation': 'Usable Volume ÷ Average Package Volume', 'value': f"{usable_volume:.1f} m³ ÷ {avg_package_volume*1000000:.0f} cm³"},
            {'result': 'Theoretical Storage Capacity', 'value': f"{theoretical_packages:,} packages"}
        ],
        'result': f"{theoretical_packages:,} packages can be stored"
    })
    
    # Step 5: Apply operational constraints for daily throughput
    operational_calc = []
    daily_throughput = theoretical_packages
    
    # Daily handling constraint (5% of stored packages can be processed daily)
    handling_factor = 0.05
    throughput_after_handling = daily_throughput * handling_factor
    operational_calc.append({
        'constraint': 'Daily Handling Capacity',
        'factor': f"{handling_factor*100:.0f}%",
        'reason': 'Staff can only process 5% of stored inventory per day',
        'before': f"{daily_throughput:,} packages stored",
        'after': f"{int(throughput_after_handling):,} packages/day processable"
    })
    daily_throughput = throughput_after_handling
    
    # Inventory turnover (0.8x per day)
    turnover = WAREHOUSE_CAPACITY_FACTORS['inventory_turnover']
    throughput_after_turnover = daily_throughput * turnover
    operational_calc.append({
        'constraint': 'Inventory Turnover',
        'factor': f"{turnover:.1f}x/day",
        'reason': 'Packages stay ~1.25 days (same-day + next-day)',
        'before': f"{int(daily_throughput):,} packages/day",
        'after': f"{int(throughput_after_turnover):,} packages/day"
    })
    daily_throughput = throughput_after_turnover
    
    # Operational efficiency (80%)
    op_efficiency = WAREHOUSE_CAPACITY_FACTORS['operational_efficiency']
    throughput_after_efficiency = daily_throughput * op_efficiency
    operational_calc.append({
        'constraint': 'Operational Efficiency',
        'factor': f"{op_efficiency*100:.0f}%",
        'reason': 'Time for sorting, consolidation, breaks',
        'before': f"{int(daily_throughput):,} packages/day",
        'after': f"{int(throughput_after_efficiency):,} packages/day"
    })
    daily_throughput = throughput_after_efficiency
    
    # Peak capacity buffer (30% buffer needed)
    buffer = WAREHOUSE_CAPACITY_FACTORS['peak_capacity_buffer']
    final_daily_capacity = daily_throughput / buffer
    operational_calc.append({
        'constraint': 'Peak Capacity Buffer',
        'factor': f"{(buffer-1)*100:.0f}% buffer needed",
        'reason': 'Handle demand spikes and variations',
        'before': f"{int(daily_throughput):,} packages/day",
        'after': f"{int(final_daily_capacity):,} packages/day final"
    })
    
    calculation_steps.append({
        'step': 5,
        'description': 'Apply Operational Constraints for Daily Throughput',
        'detail': operational_calc,
        'result': f"{int(final_daily_capacity):,} orders/day practical capacity"
    })
    
    result = {
        'theoretical_packages': theoretical_packages,
        'daily_capacity': int(final_daily_capacity),
        'usable_volume_m3': usable_volume,
        'avg_package_volume': avg_package_volume,
        'calculation_steps': calculation_steps if show_steps else None,
        'efficiency_details': WAREHOUSE_CAPACITY_FACTORS
    }
    
    return result

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
    if not INTER_HUB_CONFIG['enable_multi_node_routes'] or len(big_warehouses) < 2:
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
    
    # Handle different numbers of hubs
    if len(big_warehouses) == 2:
        # Simple point-to-point routes for 2 hubs
        hub1, hub2 = big_warehouses
        hub1_id, hub2_id = hub1['id'], hub2['id']
        if hub1_id in hub_distances and hub2_id in hub_distances[hub1_id]:
            route_info = hub_distances[hub1_id][hub2_id]
            routes.append({
                'route_sequence': [hub1_id, hub2_id],
                'total_distance': route_info['distance'],
                'total_time': route_info['time'],
                'hubs_served': 2,
                'efficiency_score': route_info['distance'],
                'route_type': 'point_to_point'
            })
    
    elif len(big_warehouses) == 3:
        # Triangle routes for 3 hubs (can do both directions)
        hub_ids = [h['id'] for h in big_warehouses]
        
        # Try both clockwise and counter-clockwise
        for route_sequence in [hub_ids, hub_ids[::-1]]:
            total_distance = 0
            total_time = 0
            valid_route = True
            
            for i in range(len(route_sequence)):
                next_i = (i + 1) % len(route_sequence)
                current_hub = route_sequence[i]
                next_hub = route_sequence[next_i]
                
                if current_hub in hub_distances and next_hub in hub_distances[current_hub]:
                    route_info = hub_distances[current_hub][next_hub]
                    total_distance += route_info['distance']
                    total_time += route_info['time']
                else:
                    valid_route = False
                    break
            
            if valid_route and total_distance <= INTER_HUB_CONFIG['max_route_distance']:
                routes.append({
                    'route_sequence': route_sequence + [route_sequence[0]],  # Complete circle
                    'total_distance': total_distance,
                    'total_time': total_time,
                    'hubs_served': 3,
                    'efficiency_score': total_distance / 3,
                    'route_type': 'triangular'
                })
    
    # Create circular routes (most efficient for multi-stop)
    elif len(big_warehouses) >= 4:
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
            'order_capacity': specs['practical_mixed_capacity'],
            'cost': VEHICLE_COSTS[vehicle_type],
            'allowed_sizes': specs['allowed_sizes'],
            'size_capacity': specs['size_capacity'],
            'volume_limit': specs['theoretical_volume'],
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
            'monthly_cost': customer_cost * 30,  # Convert daily to monthly cost
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
        
        # Get specs from centralized config - use practical mixed capacity
        vehicle_capacity = VEHICLE_SPECS[vehicle_type]['practical_mixed_capacity']
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
        
        # Calculate trip utilization and efficiency  
        total_trip_capacity = vehicles_needed * trips_per_vehicle * vehicle_capacity
        current_efficiency = (total_current_orders / total_trip_capacity) * 100 if total_current_orders > 0 else 0
        theoretical_efficiency = (total_theoretical_capacity / total_trip_capacity) * 100
        
        # Calculate cost per trip utilization
        cost_per_trip = daily_cost / (vehicles_needed * trips_per_vehicle)
        cost_per_order_current = cost_per_trip / (total_current_orders / (vehicles_needed * trips_per_vehicle)) if total_current_orders > 0 else 0
        
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
            'total_trips_per_day': vehicles_needed * trips_per_vehicle,
            'current_efficiency': f"{current_efficiency:.1f}%",
            'theoretical_efficiency': f"{theoretical_efficiency:.1f}%",
            'cost_per_trip': cost_per_trip,
            'cost_per_order_current': cost_per_order_current,
            'trip_utilization': f"{current_efficiency:.1f}% ({total_current_orders} orders in {vehicles_needed * trips_per_vehicle} trips)",
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
            
            # Get specs from centralized config - use practical mixed capacity
            relay_cost = VEHICLE_COSTS[relay_vehicle]
            relay_capacity = VEHICLE_SPECS[relay_vehicle]['practical_mixed_capacity']
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

def show_network_analysis(df_filtered, big_warehouses, feeder_warehouses, big_warehouse_count, total_feeders, total_orders_in_radius, coverage_percentage, delivery_radius=2, vehicle_mix='auto_heavy', target_capacity=None):
    """Show simplified network capacity analysis focused on key insights"""
    
    st.subheader("📊 Network Capacity Analysis")
    
    # Calculate capacity for each mile
    current_orders = len(df_filtered)
    
    # Get pickup hubs data for first mile capacity analysis
    if 'customer' in df_filtered.columns:
        pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat', 'customer']).size().reset_index(name='order_count')
    else:
        pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
    
    # First Mile Capacity: Based on pickup hub collection capability
    total_pickup_locations = len(pickup_hubs)
    # Assume each pickup location can handle ~150 orders/day with proper vehicles
    first_mile_capacity = total_pickup_locations * 150
    
    # Middle Mile Capacity: Hub + Hub-to-Auxiliary capacity
    total_hub_capacity = sum([hub.get('capacity', 500) for hub in big_warehouses])
    total_auxiliary_capacity = sum([feeder.get('capacity', 150) for feeder in feeder_warehouses])
    # Middle mile is limited by the minimum of hub sorting capacity and hub-auxiliary transport
    middle_mile_capacity = min(total_hub_capacity, total_auxiliary_capacity)
    
    # Last Mile Capacity: Auxiliary warehouse to customer delivery
    # Assume each auxiliary can deliver its full capacity per day
    last_mile_capacity = total_auxiliary_capacity
    
    # Network bottleneck is the minimum capacity across all miles
    network_bottleneck = min(first_mile_capacity, middle_mile_capacity, last_mile_capacity)
    
    # Show capacity breakdown
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🚚 First Mile")
        first_util = (current_orders / first_mile_capacity * 100) if first_mile_capacity > 0 else 0
        color = "🟢" if first_util < 70 else "🟡" if first_util < 90 else "🔴"
        st.metric("Collection Capacity", f"{first_util:.0f}%", f"{current_orders:,} of {first_mile_capacity:,}")
        st.write(f"{color} {total_pickup_locations} pickup locations")
        
    with col2:
        st.markdown("#### 🔄 Middle Mile") 
        middle_util = (current_orders / middle_mile_capacity * 100) if middle_mile_capacity > 0 else 0
        color = "🟢" if middle_util < 70 else "🟡" if middle_util < 90 else "🔴"
        st.metric("Hub-Auxiliary Flow", f"{middle_util:.0f}%", f"{current_orders:,} of {middle_mile_capacity:,}")
        st.write(f"{color} Hub: {total_hub_capacity:,}, Aux: {total_auxiliary_capacity:,}")
        
    with col3:
        st.markdown("#### 🏠 Last Mile")
        last_util = (current_orders / last_mile_capacity * 100) if last_mile_capacity > 0 else 0
        color = "🟢" if last_util < 70 else "🟡" if last_util < 90 else "🔴"
        st.metric("Delivery Capacity", f"{last_util:.0f}%", f"{current_orders:,} of {last_mile_capacity:,}")
        st.write(f"{color} {len(feeder_warehouses)} auxiliary warehouses")
    
    # Show network bottleneck
    st.markdown("#### 🚨 Network Bottleneck")
    bottleneck_name = "First Mile" if network_bottleneck == first_mile_capacity else "Middle Mile" if network_bottleneck == middle_mile_capacity else "Last Mile"
    bottleneck_util = (current_orders / network_bottleneck * 100) if network_bottleneck > 0 else 0
    
    if bottleneck_util < 70:
        st.success(f"✅ **{bottleneck_name}** is the bottleneck at {bottleneck_util:.0f}% utilization. Network can handle {network_bottleneck - current_orders:,} more orders.")
    elif bottleneck_util < 90:
        st.warning(f"⚠️ **{bottleneck_name}** is the bottleneck at {bottleneck_util:.0f}% utilization. Consider expanding {bottleneck_name.lower()} capacity soon.")
    else:
        st.error(f"🔴 **{bottleneck_name}** is the bottleneck at {bottleneck_util:.0f}% utilization. Urgent capacity expansion needed!")
    
    # Add warehouse rental costs and capacity details prominently
    st.markdown("### 🏭 Warehouse Specifications & Rental Costs")
    
    col1, col2 = st.columns(2)
    with col1:
        main_specs = WAREHOUSE_SPECS['main_microwarehouse']
        main_capacity = calculate_realistic_warehouse_capacity(main_specs['avg_size_sqft'])
        
        st.markdown("#### 🏢 Main Microwarehouses")
        st.metric("Size Range", f"{main_specs['size_range_sqft'][0]}-{main_specs['size_range_sqft'][1]} sqft", f"avg {main_specs['avg_size_sqft']} sqft")
        st.metric("Monthly Rent", f"₹{main_specs['monthly_rent_range'][0]:,}-{main_specs['monthly_rent_range'][1]:,}", f"avg ₹{main_specs['avg_monthly_rent']:,}")
        st.metric("Daily Capacity", f"{main_capacity['daily_capacity']:,} orders", f"per warehouse")
        st.info(f"📝 {main_specs['description']}")
        
    with col2:
        aux_specs = WAREHOUSE_SPECS['auxiliary_warehouse']
        aux_capacity = calculate_realistic_warehouse_capacity(aux_specs['avg_size_sqft'])
        
        st.markdown("#### 📦 Auxiliary Warehouses") 
        st.metric("Size Range", f"{aux_specs['size_range_sqft'][0]}-{aux_specs['size_range_sqft'][1]} sqft", f"avg {aux_specs['avg_size_sqft']} sqft")
        st.metric("Monthly Rent", f"₹{aux_specs['monthly_rent_range'][0]:,}-{aux_specs['monthly_rent_range'][1]:,}", f"avg ₹{aux_specs['avg_monthly_rent']:,}")
        st.metric("Daily Capacity", f"{aux_capacity['daily_capacity']:,} orders", f"per warehouse")
        st.info(f"📝 {aux_specs['description']}")
    
    # Capacity calculation insight
    st.markdown("#### 🔍 How We Calculate Daily Capacity")
    st.info(f"""
    **Key Insight**: Daily capacity ({main_capacity['daily_capacity']:,} orders for main, {aux_capacity['daily_capacity']:,} for auxiliary) is much lower than storage capacity ({main_capacity['theoretical_packages']:,} and {aux_capacity['theoretical_packages']:,} packages respectively).
    
    **Why?** Logistics warehouses are limited by **daily handling capacity** (5% of stored inventory), not storage space. The constraints are:
    - 40% storage density (aisles, sorting areas)
    - 70% height utilization (safe stacking)  
    - 5% daily handling capacity (staff limitations)
    - Inventory turnover and operational efficiency factors
    """)
    
    # Add cost analysis using existing functions
    st.markdown("### 💰 Network Cost Analysis")
    
    # Calculate costs using existing functions
    first_mile_cost, first_mile_details = calculate_first_mile_costs(pickup_hubs, big_warehouses)
    middle_mile_cost, middle_mile_details, inter_hub_details = calculate_middle_mile_costs(big_warehouses, feeder_warehouses)
    last_mile_cost, last_mile_details = calculate_last_mile_costs(df_filtered, big_warehouses, feeder_warehouses, delivery_radius, vehicle_mix)
    
    # Show cost breakdown
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🚚 First Mile Cost")
        daily_first_mile = first_mile_cost
        monthly_first_mile = daily_first_mile * 30
        first_mile_cpo = daily_first_mile / current_orders if current_orders > 0 else 0
        st.metric("Daily Cost", f"₹{daily_first_mile:,.0f}")
        st.write(f"Monthly: ₹{monthly_first_mile:,.0f}")
        st.write(f"CPO: ₹{first_mile_cpo:.1f}")
        
    with col2:
        st.markdown("#### 🔄 Middle Mile Cost")
        daily_middle_mile = middle_mile_cost / 30  # Convert monthly to daily
        middle_mile_cpo = daily_middle_mile / current_orders if current_orders > 0 else 0
        st.metric("Daily Cost", f"₹{daily_middle_mile:,.0f}")
        st.write(f"Monthly: ₹{middle_mile_cost:,.0f}")
        st.write(f"CPO: ₹{middle_mile_cpo:.1f}")
        
    with col3:
        st.markdown("#### 🏠 Last Mile Cost")
        daily_last_mile = last_mile_cost / 30  # Convert monthly to daily
        last_mile_cpo = daily_last_mile / current_orders if current_orders > 0 else 0
        st.metric("Daily Cost", f"₹{daily_last_mile:,.0f}")
        st.write(f"Monthly: ₹{last_mile_cost:,.0f}")
        st.write(f"CPO: ₹{last_mile_cpo:.1f}")
    
    # Total network cost
    total_daily_cost = daily_first_mile + daily_middle_mile + daily_last_mile
    total_monthly_cost = total_daily_cost * 30
    total_cpo = total_daily_cost / current_orders if current_orders > 0 else 0
    
    st.markdown("#### 📊 Total Network Cost")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Total", f"₹{total_daily_cost:,.0f}")
    with col2:
        st.metric("Monthly Total", f"₹{total_monthly_cost:,.0f}")
    with col3:
        st.metric("Cost Per Order", f"₹{total_cpo:.1f}")
    
    # Add comprehensive cost breakdown mixing warehouse rental + all mile costs
    st.markdown("---")
    st.markdown("### 🏢 COMPREHENSIVE COST BREAKDOWN: Warehouse Rent + Transportation")
    
    # Calculate warehouse rental costs
    main_warehouses_count = len(big_warehouses)
    auxiliary_warehouses_count = len(feeder_warehouses)
    
    main_wh_monthly_rent = main_warehouses_count * WAREHOUSE_SPECS['main_microwarehouse']['avg_monthly_rent']
    aux_wh_monthly_rent = auxiliary_warehouses_count * WAREHOUSE_SPECS['auxiliary_warehouse']['avg_monthly_rent']
    total_warehouse_rent = main_wh_monthly_rent + aux_wh_monthly_rent
    
    # Transportation costs (monthly)
    monthly_first_mile = daily_first_mile * 30
    monthly_middle_mile = daily_middle_mile * 30
    monthly_last_mile = daily_last_mile * 30
    total_transportation = monthly_first_mile + monthly_middle_mile + monthly_last_mile
    
    # Grand total
    grand_total_monthly = total_warehouse_rent + total_transportation
    grand_total_daily = grand_total_monthly / 30
    grand_total_cpo = grand_total_daily / current_orders if current_orders > 0 else 0
    
    # Create comprehensive breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏢 Warehouse Infrastructure Costs")
        st.metric("Main Warehouses", f"₹{main_wh_monthly_rent:,.0f}/month", f"{main_warehouses_count} × ₹{WAREHOUSE_SPECS['main_microwarehouse']['avg_monthly_rent']:,}")
        st.metric("Auxiliary Warehouses", f"₹{aux_wh_monthly_rent:,.0f}/month", f"{auxiliary_warehouses_count} × ₹{WAREHOUSE_SPECS['auxiliary_warehouse']['avg_monthly_rent']:,}")
        st.metric("Total Warehouse Rent", f"₹{total_warehouse_rent:,.0f}/month", f"Fixed Infrastructure Cost")
        
        # Warehouse cost per order
        warehouse_cpo = (total_warehouse_rent / 30) / current_orders if current_orders > 0 else 0
        st.write(f"**Warehouse CPO:** ₹{warehouse_cpo:.1f}")
        
    with col2:
        st.markdown("#### 🚛 Transportation Operations Costs")
        st.metric("First Mile Collection", f"₹{monthly_first_mile:,.0f}/month", f"Customer → Hub")
        st.metric("Middle Mile Distribution", f"₹{monthly_middle_mile:,.0f}/month", f"Hub → Auxiliary")
        st.metric("Last Mile Delivery", f"₹{monthly_last_mile:,.0f}/month", f"Warehouse → Customer")
        st.metric("Total Transportation", f"₹{total_transportation:,.0f}/month", f"Variable Operations Cost")
        
        # Transportation cost per order
        transport_cpo = (total_transportation / 30) / current_orders if current_orders > 0 else 0
        st.write(f"**Transport CPO:** ₹{transport_cpo:.1f}")
    
    # Grand total summary
    st.markdown("#### 💰 GRAND TOTAL: Complete Network Operating Cost")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Monthly Total", f"₹{grand_total_monthly:,.0f}", f"Rent + Transport")
    with col2:
        st.metric("Daily Total", f"₹{grand_total_daily:,.0f}", f"All-in Operating Cost")
    with col3:
        st.metric("Cost Per Order", f"₹{grand_total_cpo:.1f}", f"Complete CPO")
    with col4:
        warehouse_percentage = (total_warehouse_rent / grand_total_monthly) * 100
        st.metric("Rent vs Transport", f"{warehouse_percentage:.0f}%", f"Warehouse Rent Share")
    
    # Cost breakdown chart
    st.markdown("#### 📈 Cost Structure Analysis")
    
    # Show percentage breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Monthly Cost Distribution:**")
        warehouse_pct = (total_warehouse_rent / grand_total_monthly) * 100
        first_mile_pct = (monthly_first_mile / grand_total_monthly) * 100
        middle_mile_pct = (monthly_middle_mile / grand_total_monthly) * 100
        last_mile_pct = (monthly_last_mile / grand_total_monthly) * 100
        
        st.write(f"🏢 Warehouse Rent: {warehouse_pct:.1f}% (₹{total_warehouse_rent:,.0f})")
        st.write(f"🚚 First Mile: {first_mile_pct:.1f}% (₹{monthly_first_mile:,.0f})")
        st.write(f"🔄 Middle Mile: {middle_mile_pct:.1f}% (₹{monthly_middle_mile:,.0f})")
        st.write(f"🏠 Last Mile: {last_mile_pct:.1f}% (₹{monthly_last_mile:,.0f})")
        
    with col2:
        st.markdown("**Trip Frequency & Volume:**")
        
        # Calculate total trips across all segments
        pickup_hubs_count = len(pickup_hubs) if 'pickup_hubs' in locals() else 0
        
        # First mile trips (4-6 collections per hub per day)
        first_mile_trips_per_day = pickup_hubs_count * 5  # Average 5 trips
        
        # Middle mile trips (from middle mile details)
        middle_mile_trips_per_day = 0
        if middle_mile_details:
            middle_mile_trips_per_day = sum([detail.get('total_trips_per_day', 0) for detail in middle_mile_details])
        
        # Last mile trips (estimated from orders and vehicle capacity)
        avg_orders_per_trip = 15  # Conservative estimate for mixed delivery
        last_mile_trips_per_day = max(1, current_orders // avg_orders_per_trip)
        
        total_trips_per_day = first_mile_trips_per_day + middle_mile_trips_per_day + last_mile_trips_per_day
        
        st.write(f"🚚 First Mile: {first_mile_trips_per_day} trips/day")
        st.write(f"🔄 Middle Mile: {middle_mile_trips_per_day} trips/day")
        st.write(f"🏠 Last Mile: {last_mile_trips_per_day} trips/day")
        st.write(f"**Total Daily Trips: {total_trips_per_day}**")
        
        # Cost per trip
        cost_per_trip = grand_total_daily / total_trips_per_day if total_trips_per_day > 0 else 0
        st.write(f"**Avg Cost/Trip: ₹{cost_per_trip:.0f}**")
    
    # Scale analysis
    st.markdown("#### 📊 Scale Economics Analysis")
    st.info(f"""
    **Current Scale:** {current_orders:,} orders/day across {main_warehouses_count} main + {auxiliary_warehouses_count} auxiliary warehouses
    
    **Cost Structure:**
    - **Fixed Costs (Rent):** ₹{total_warehouse_rent:,.0f}/month ({warehouse_percentage:.0f}%) - doesn't change with volume
    - **Variable Costs (Transport):** ₹{total_transportation:,.0f}/month ({100-warehouse_percentage:.0f}%) - scales with orders
    
    **Scale Benefits:** As order volume increases, warehouse rent cost per order decreases while transport costs remain relatively stable. At 2x volume, total CPO would drop to ~₹{grand_total_cpo*0.75:.1f} (25% improvement).
    """)
    
    # Add the ultimate comprehensive table with EVERYTHING
    st.markdown("---")
    st.markdown("### 📋 ULTIMATE NETWORK SUMMARY: All Costs + Capacity + Utilization")
    
    # Calculate all capacity metrics
    total_pickup_locations = len(pickup_hubs)
    first_mile_capacity = total_pickup_locations * 150  # 150 orders per pickup location
    total_hub_capacity = sum([hub.get('capacity', 500) for hub in big_warehouses])
    total_auxiliary_capacity = sum([feeder.get('capacity', 150) for feeder in feeder_warehouses])
    middle_mile_capacity = min(total_hub_capacity, total_auxiliary_capacity)
    last_mile_capacity = total_auxiliary_capacity
    network_bottleneck = min(first_mile_capacity, middle_mile_capacity, last_mile_capacity)
    
    # Calculate utilization percentages
    first_util = (current_orders / first_mile_capacity * 100) if first_mile_capacity > 0 else 0
    middle_util = (current_orders / middle_mile_capacity * 100) if middle_mile_capacity > 0 else 0
    last_util = (current_orders / last_mile_capacity * 100) if last_mile_capacity > 0 else 0
    bottleneck_util = (current_orders / network_bottleneck * 100) if network_bottleneck > 0 else 0
    
    # Create comprehensive summary table
    import pandas as pd
    
    summary_data = {
        'Network Component': [
            '🏢 Main Warehouses',
            '📦 Auxiliary Warehouses', 
            '🚚 First Mile Collection',
            '🔄 Middle Mile Distribution',
            '🏠 Last Mile Delivery',
            '💰 TOTAL NETWORK'
        ],
        'Count/Capacity': [
            f"{main_warehouses_count} warehouses",
            f"{auxiliary_warehouses_count} warehouses",
            f"{first_mile_capacity:,} orders/day",
            f"{middle_mile_capacity:,} orders/day",
            f"{last_mile_capacity:,} orders/day",
            f"{network_bottleneck:,} orders/day (bottleneck)"
        ],
        'Current Utilization': [
            f"Fixed Infrastructure",
            f"Fixed Infrastructure", 
            f"{first_util:.1f}% ({current_orders}/{first_mile_capacity:,})",
            f"{middle_util:.1f}% ({current_orders}/{middle_mile_capacity:,})",
            f"{last_util:.1f}% ({current_orders}/{last_mile_capacity:,})",
            f"{bottleneck_util:.1f}% ({current_orders}/{network_bottleneck:,})"
        ],
        'Monthly Cost': [
            f"₹{main_wh_monthly_rent:,.0f}",
            f"₹{aux_wh_monthly_rent:,.0f}",
            f"₹{monthly_first_mile:,.0f}",
            f"₹{monthly_middle_mile:,.0f}",
            f"₹{monthly_last_mile:,.0f}",
            f"₹{grand_total_monthly:,.0f}"
        ],
        'Cost Per Order': [
            f"₹{(main_wh_monthly_rent/30)/current_orders:.1f}" if current_orders > 0 else "₹0.0",
            f"₹{(aux_wh_monthly_rent/30)/current_orders:.1f}" if current_orders > 0 else "₹0.0",
            f"₹{daily_first_mile/current_orders:.1f}" if current_orders > 0 else "₹0.0",
            f"₹{daily_middle_mile/current_orders:.1f}" if current_orders > 0 else "₹0.0",
            f"₹{daily_last_mile/current_orders:.1f}" if current_orders > 0 else "₹0.0",
            f"₹{grand_total_cpo:.1f}"
        ],
        'Key Details': [
            f"{WAREHOUSE_SPECS['main_microwarehouse']['avg_size_sqft']} sqft avg",
            f"{WAREHOUSE_SPECS['auxiliary_warehouse']['avg_size_sqft']} sqft avg",
            f"{total_pickup_locations} pickup locations",
            f"{main_warehouses_count} hubs → {auxiliary_warehouses_count} aux",
            f"{delivery_radius}km delivery radius",
            f"Bottleneck: {'First Mile' if network_bottleneck == first_mile_capacity else 'Middle Mile' if network_bottleneck == middle_mile_capacity else 'Last Mile'}"
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    
    # Display the comprehensive table
    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Network Component": st.column_config.TextColumn("Network Component", width="medium"),
            "Count/Capacity": st.column_config.TextColumn("Count/Capacity", width="medium"),
            "Current Utilization": st.column_config.TextColumn("Current Utilization", width="medium"),
            "Monthly Cost": st.column_config.TextColumn("Monthly Cost", width="medium"),
            "Cost Per Order": st.column_config.TextColumn("Cost Per Order", width="small"),
            "Key Details": st.column_config.TextColumn("Key Details", width="medium")
        }
    )
    
    # Add executive summary
    st.markdown("#### 🎯 Executive Summary")
    bottleneck_name = "First Mile" if network_bottleneck == first_mile_capacity else "Middle Mile" if network_bottleneck == middle_mile_capacity else "Last Mile"
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Network Performance:**")
        if bottleneck_util < 70:
            status_color = "🟢"
            status_text = "Healthy"
        elif bottleneck_util < 90:
            status_color = "🟡" 
            status_text = "Warning"
        else:
            status_color = "🔴"
            status_text = "Critical"
            
        st.write(f"• Network Status: {status_color} {status_text}")
        st.write(f"• Current Orders: {current_orders:,}/day")
        st.write(f"• Network Capacity: {network_bottleneck:,}/day")
        st.write(f"• Bottleneck: {bottleneck_name} ({bottleneck_util:.1f}%)")
        st.write(f"• Spare Capacity: {network_bottleneck - current_orders:,} orders")
        
    with col2:
        st.markdown("**💰 Cost Performance:**")
        st.write(f"• Total Monthly Cost: ₹{grand_total_monthly:,.0f}")
        st.write(f"• Cost Per Order: ₹{grand_total_cpo:.1f}")
        st.write(f"• Fixed Costs: {warehouse_percentage:.0f}% (₹{total_warehouse_rent:,.0f})")
        st.write(f"• Variable Costs: {100-warehouse_percentage:.0f}% (₹{total_transportation:,.0f})")
        st.write(f"• Infrastructure: {main_warehouses_count + auxiliary_warehouses_count} warehouses")
    
    return  # Return after showing ultimate comprehensive analysis
    
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
    
    # Use target capacity from user input instead of making assumptions
    current_orders = len(df_filtered)
    
    if target_capacity is not None and target_capacity > current_orders:
        full_capacity_orders = target_capacity
    else:
        # Fallback to current orders if no target specified
        full_capacity_orders = current_orders
    
    # Calculate actual network capacity based on infrastructure built for display
    total_hub_capacity = sum([hub.get('capacity', 500) for hub in big_warehouses])
    total_feeder_capacity = sum([feeder.get('capacity', 150) for feeder in feeder_warehouses])
    
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
        
        # Add capacity assumptions to current cost breakdown
        pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
        first_mile_capacity_note = f"{len(pickup_hubs)} pickup hubs"
        middle_mile_capacity_note = f"{len(middle_mile_details)} routes, avg {sum([d['total_trips_per_day'] for d in middle_mile_details])//len(middle_mile_details) if middle_mile_details else 0} trips/day"
        last_mile_capacity_note = f"{current_vehicle_mix} mix"
        
        current_data = {
            "Mile": ["First Mile", "Middle Mile", "Last Mile", "**TOTAL**"],
            "Monthly Cost": [f"₹{monthly_first_mile:,.0f}", f"₹{middle_mile_cost:,.0f}", f"₹{last_mile_cost:,.0f}", f"**₹{total_logistics_cost:,.0f}**"],
            "CPO": [f"₹{first_mile_daily_cpo:.1f}", f"₹{middle_mile_daily_cpo:.1f}", f"₹{last_mile_daily_cpo:.1f}", f"**₹{total_daily_cpo:.1f}**"],
            "Capacity Used": [first_mile_capacity_note, middle_mile_capacity_note, last_mile_capacity_note, f"**{current_orders:,} orders**"]
        }
        st.table(pd.DataFrame(current_data))
        st.write(f"🎯 **Current Orders:** {current_orders:,}")
        st.write(f"📊 **Network Utilization:** {(current_orders/full_capacity_orders*100):.1f}%")
    
    with col2:
        st.markdown("#### 🚀 Full Capacity Scenario")
        # Calculate correct CPO for full capacity - daily cost per order
        full_first_mile_daily_cpo = (full_capacity_first_mile / 30) / full_capacity_orders if full_capacity_orders > 0 else 0
        full_middle_mile_daily_cpo = (full_capacity_middle_mile / 30) / full_capacity_orders if full_capacity_orders > 0 else 0
        full_last_mile_daily_cpo = (full_capacity_last_mile / 30) / full_capacity_orders if full_capacity_orders > 0 else 0
        full_total_daily_cpo = full_first_mile_daily_cpo + full_middle_mile_daily_cpo + full_last_mile_daily_cpo
        
        # Add capacity assumptions to full capacity breakdown
        full_first_mile_capacity_note = f"Same {len(pickup_hubs)} hubs, higher frequency"
        full_middle_mile_capacity_note = f"Same routes, {sum([d['total_trips_per_day'] for d in middle_mile_details]) if middle_mile_details else 0} trips/day max"
        full_last_mile_capacity_note = f"Scaled {current_vehicle_mix} mix"
        
        full_capacity_data = {
            "Mile": ["First Mile", "Middle Mile", "Last Mile", "**TOTAL**"],
            "Monthly Cost": [f"₹{full_capacity_first_mile:,.0f}", f"₹{full_capacity_middle_mile:,.0f}", f"₹{full_capacity_last_mile:,.0f}", f"**₹{full_capacity_total:,.0f}**"],
            "CPO": [f"₹{full_first_mile_daily_cpo:.1f}", f"₹{full_middle_mile_daily_cpo:.1f}", f"₹{full_last_mile_daily_cpo:.1f}", f"**₹{full_total_daily_cpo:.1f}**"],
            "Capacity Used": [full_first_mile_capacity_note, full_middle_mile_capacity_note, full_last_mile_capacity_note, f"**{full_capacity_orders:,} orders**"]
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
    
    # Move the capacity assumptions table to be more prominent right after warehouse specs
    st.markdown("### 📊 Detailed Capacity Assumptions")
    st.markdown("*Complete breakdown of all assumptions used in cost and capacity calculations*")
    
    # Create capacity assumptions table
    capacity_assumptions_data = []
    
    # Vehicle capacity assumptions
    for vehicle_type, specs in VEHICLE_SPECS.items():
        theoretical_vol = int(specs['theoretical_volume'] * 1000)
        practical_vol = int(specs['practical_volume'] * 1000)
        efficiency_loss = f"{((theoretical_vol - practical_vol) / theoretical_vol * 100):.0f}%"
        
        capacity_assumptions_data.append({
            "Cost Component": f"{vehicle_type.replace('_', ' ').title()} Vehicle",
            "Theoretical Capacity": f"{theoretical_vol}L / {specs['practical_mixed_capacity']} orders theoretical",
            "Practical Capacity": f"{practical_vol}L / {specs['avg_orders_per_trip']} orders average",
            "Efficiency Loss": f"{efficiency_loss} (Space: 65%, Load: 80%, Weight: 90%, Access: 85%)",
            "Daily Cost": f"₹{VEHICLE_COSTS[vehicle_type]:,}/day",
            "Usage": "First Mile, Middle Mile, Inter-Hub routes"
        })
    
    # Main microwarehouse capacity assumptions
    main_wh_specs = WAREHOUSE_SPECS['main_microwarehouse']
    main_wh_capacity = calculate_realistic_warehouse_capacity(main_wh_specs['avg_size_sqft'])
    capacity_assumptions_data.append({
        "Cost Component": "Main Microwarehouse",
        "Theoretical Capacity": f"{main_wh_specs['size_range_sqft'][0]}-{main_wh_specs['size_range_sqft'][1]} sqft, {main_wh_capacity['theoretical_packages']:,} packages storage",
        "Practical Capacity": f"{main_wh_capacity['daily_capacity']:,} orders/day (avg {main_wh_specs['avg_size_sqft']} sqft)",
        "Efficiency Loss": f"Storage: 40%, Height: 70%, Handling: 5%, Turnover: 0.8x/day, Buffer: 30%",
        "Daily Cost": f"₹{main_wh_specs['monthly_rent_range'][0]:,}-{main_wh_specs['monthly_rent_range'][1]:,}/month (avg ₹{main_wh_specs['avg_monthly_rent']:,})",
        "Usage": "Hub operations with sorting and consolidation"
    })
    
    # Auxiliary warehouse capacity assumptions  
    aux_wh_specs = WAREHOUSE_SPECS['auxiliary_warehouse']
    aux_wh_capacity = calculate_realistic_warehouse_capacity(aux_wh_specs['avg_size_sqft'])
    capacity_assumptions_data.append({
        "Cost Component": "Auxiliary Warehouse",
        "Theoretical Capacity": f"{aux_wh_specs['size_range_sqft'][0]}-{aux_wh_specs['size_range_sqft'][1]} sqft, {aux_wh_capacity['theoretical_packages']:,} packages storage",
        "Practical Capacity": f"{aux_wh_capacity['daily_capacity']:,} orders/day (avg {aux_wh_specs['avg_size_sqft']} sqft)",
        "Efficiency Loss": f"Same constraints as main warehouse",
        "Daily Cost": f"₹{aux_wh_specs['monthly_rent_range'][0]:,}-{aux_wh_specs['monthly_rent_range'][1]:,}/month (avg ₹{aux_wh_specs['avg_monthly_rent']:,})",
        "Usage": "Last-mile delivery points with basic storage"
    })
    
    # Package size assumptions
    capacity_assumptions_data.append({
        "Cost Component": "Package Mix",
        "Theoretical Capacity": "Small(30%) + Medium(25%) + Large(25%) + XL(15%) + XXL(5%)",
        "Practical Capacity": f"Avg: {sum([PACKAGE_VOLUMES[size] * ratio for size, ratio in {'Small': 0.3, 'Medium': 0.25, 'Large': 0.25, 'XL': 0.15, 'XXL': 0.05}.items()]) * 1000000:.0f} cm³/package",
        "Efficiency Loss": "Volume-based vehicle selection and trip planning",
        "Daily Cost": "Impacts vehicle selection and trip efficiency",
        "Usage": "All vehicle capacity and cost calculations"
    })
    
    st.dataframe(pd.DataFrame(capacity_assumptions_data), use_container_width=True)
    
    # Step-by-Step Capacity Calculation
    with st.expander("🔍 **Step-by-Step Capacity Calculation Breakdown**", expanded=False):
        st.markdown("### How We Calculate Warehouse Capacity")
        st.markdown("*This shows exactly how we arrive at the daily capacity numbers for warehouses*")
        
        # Show calculation for both warehouse types
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Main Microwarehouse (850 sqft avg)")
            main_calc = calculate_realistic_warehouse_capacity(850, show_steps=True)
            
            for step in main_calc['calculation_steps']:
                st.markdown(f"**Step {step['step']}: {step['description']}**")
                if isinstance(step['detail'], list) and len(step['detail']) > 0:
                    if 'size' in step['detail'][0]:  # Package volume step
                        for item in step['detail']:
                            st.write(f"• {item['size']}: {item['ratio']} × {item['volume_cm3']} = {item['weighted_contribution']}")
                    elif 'factor' in step['detail'][0]:  # Storage efficiency step  
                        for item in step['detail']:
                            st.write(f"• {item['factor']}: {item['percentage']} - {item['reason']}")
                            st.write(f"  {item['volume_before']} → {item['volume_after']}")
                    elif 'constraint' in step['detail'][0]:  # Operational constraints
                        for item in step['detail']:
                            st.write(f"• {item['constraint']}: {item['factor']} - {item['reason']}")
                            st.write(f"  {item['before']} → {item['after']}")
                    else:  # Other steps
                        for item in step['detail']:
                            if 'component' in item:
                                st.write(f"• {item['component']}: {item['value']}")
                            elif 'calculation' in item:
                                st.write(f"• {item['calculation']}: {item['value']}")
                
                st.success(f"**Result:** {step['result']}")
                st.write("")
        
        with col2:
            st.markdown("#### Auxiliary Warehouse (350 sqft avg)")
            aux_calc = calculate_realistic_warehouse_capacity(350, show_steps=True)
            
            for step in aux_calc['calculation_steps']:
                st.markdown(f"**Step {step['step']}: {step['description']}**")
                if isinstance(step['detail'], list) and len(step['detail']) > 0:
                    if 'size' in step['detail'][0]:  # Package volume step
                        for item in step['detail']:
                            st.write(f"• {item['size']}: {item['ratio']} × {item['volume_cm3']} = {item['weighted_contribution']}")
                    elif 'factor' in step['detail'][0]:  # Storage efficiency step  
                        for item in step['detail']:
                            st.write(f"• {item['factor']}: {item['percentage']} - {item['reason']}")
                            st.write(f"  {item['volume_before']} → {item['volume_after']}")
                    elif 'constraint' in step['detail'][0]:  # Operational constraints
                        for item in step['detail']:
                            st.write(f"• {item['constraint']}: {item['factor']} - {item['reason']}")
                            st.write(f"  {item['before']} → {item['after']}")
                    else:  # Other steps
                        for item in step['detail']:
                            if 'component' in item:
                                st.write(f"• {item['component']}: {item['value']}")
                            elif 'calculation' in item:
                                st.write(f"• {item['calculation']}: {item['value']}")
                
                st.success(f"**Result:** {step['result']}")
                st.write("")
        
        st.markdown("---")
        st.info("**Key Insight:** The daily capacity is much lower than storage capacity because logistics warehouses need to handle sorting, consolidation, and have operational constraints. The 5% daily handling capacity is the key limiting factor.")
    
    # Detailed Capacity Analysis
    with st.expander("📦 **Detailed Volume & Capacity Analysis**", expanded=False):
        show_detailed_capacity_analysis(big_warehouses, feeder_warehouses)
    
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
        
        # Trip Capacity Utilization Analysis
        st.markdown("#### 🚛 Trip Capacity Utilization (Middle Mile Focus)")
        st.markdown("*This is where most costs are - transport between hubs and auxiliaries*")
        
        trip_utilization_data = []
        for detail in middle_mile_details:
            # Get detailed capacity assumptions for this vehicle type
            vehicle_type = detail['vehicle_type']
            vehicle_specs = VEHICLE_SPECS[vehicle_type]
            
            # Calculate capacity assumptions
            theoretical_capacity = int(vehicle_specs['theoretical_volume'] * 1000)  # liters
            practical_capacity = int(vehicle_specs['practical_volume'] * 1000)  # liters
            efficiency_loss = f"{((theoretical_capacity - practical_capacity) / theoretical_capacity * 100):.0f}%"
            
            trip_utilization_data.append({
                "Hub → Auxiliaries": detail['route'],
                "Vehicle": detail['vehicle_type'].replace('_', ' ').title(),
                "Theoretical Vol": f"{theoretical_capacity}L",
                "Practical Vol": f"{practical_capacity}L ({efficiency_loss} loss)",
                "Trip Capacity": f"{detail['vehicle_capacity']} orders",
                "Daily Trips": detail['total_trips_per_day'],
                "Current Load": f"{detail['current_orders']} orders",
                "Utilization": detail['current_efficiency'],
                "Cost/Trip": f"₹{detail['cost_per_trip']:,.0f}",
                "Capacity Assumptions": f"Space: 65%, Load: 80%, Weight: 90%, Access: 85% = {OVERALL_LOADING_EFFICIENCY*100:.0f}% overall"
            })
        
        if trip_utilization_data:
            st.dataframe(pd.DataFrame(trip_utilization_data), use_container_width=True)
            
            # Key insights about trip utilization
            total_trips = sum([detail['total_trips_per_day'] for detail in middle_mile_details])
            avg_utilization = sum([float(detail['current_efficiency'].replace('%', '')) for detail in middle_mile_details]) / len(middle_mile_details)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Daily Trips", total_trips, help="All hub-to-auxiliary trips per day")
            with col2:
                st.metric("Avg Trip Utilization", f"{avg_utilization:.0f}%", help="Average capacity used per trip")
            with col3:
                cost_per_order = sum([detail['daily_cost'] for detail in middle_mile_details]) / sum([detail['current_orders'] for detail in middle_mile_details]) if sum([detail['current_orders'] for detail in middle_mile_details]) > 0 else 0
                st.metric("Middle Mile CPO", f"₹{cost_per_order:.1f}", help="Cost per order for hub-auxiliary transport")

def show_detailed_capacity_analysis(big_warehouses, feeder_warehouses):
    """Show detailed volume-based capacity analysis for warehouses and vehicles"""
    
    st.markdown("### 📦 Volume-Based Capacity Analysis")
    st.markdown("*Realistic capacity calculations accounting for package sizes, loading efficiency, and warehouse constraints*")
    
    # Vehicle Capacity Analysis
    st.markdown("#### 🚛 Vehicle Capacity Breakdown")
    st.markdown("**Loading Efficiency Factors:**")
    
    efficiency_data = []
    for factor, value in LOADING_EFFICIENCY.items():
        efficiency_data.append({
            "Factor": factor.replace('_', ' ').title(),
            "Efficiency": f"{value*100:.0f}%",
            "Impact": {
                'space_utilization': "Irregular package shapes, packing gaps",
                'loading_time_factor': "Time constraints for loading/unloading", 
                'weight_distribution': "Safe weight distribution for stability",
                'access_factor': "Easy access during delivery stops"
            }[factor]
        })
    
    st.dataframe(pd.DataFrame(efficiency_data), use_container_width=True)
    st.info(f"**Overall Loading Efficiency: {OVERALL_LOADING_EFFICIENCY*100:.1f}%** - This is applied to all theoretical vehicle capacities")
    
    # Vehicle capacity table
    st.markdown("#### 🚐 Vehicle Capacity by Package Type")
    vehicle_capacity_data = []
    
    for vehicle_type, specs in VEHICLE_SPECS.items():
        for package_size in specs['allowed_sizes']:
            if package_size in specs['size_capacity']:
                theoretical = int(specs['theoretical_volume'] / PACKAGE_VOLUMES[package_size])
                practical = specs['size_capacity'][package_size]
                
                vehicle_capacity_data.append({
                    "Vehicle": vehicle_type.replace('_', ' ').title(),
                    "Package Size": package_size,
                    "Package Volume": f"{PACKAGE_VOLUMES[package_size]*1000000:.0f} cm³",
                    "Theoretical Capacity": theoretical,
                    "Practical Capacity": practical,
                    "Efficiency Impact": f"{(practical/theoretical*100):.0f}%" if theoretical > 0 else "N/A"
                })
    
    st.dataframe(pd.DataFrame(vehicle_capacity_data), use_container_width=True)
    
    # Mixed capacity summary
    st.markdown("#### 📊 Practical Mixed-Package Capacity")
    mixed_capacity_data = []
    for vehicle_type, specs in VEHICLE_SPECS.items():
        mixed_capacity_data.append({
            "Vehicle Type": vehicle_type.replace('_', ' ').title(),
            "Theoretical Volume": f"{specs['theoretical_volume']*1000:.0f}L",
            "Practical Volume": f"{specs['practical_volume']*1000:.0f}L",
            "Mixed Capacity": f"{specs['practical_mixed_capacity']} orders",
            "Avg Orders/Trip": f"{specs['avg_orders_per_trip']} orders",
            "Daily Cost": f"₹{VEHICLE_COSTS[vehicle_type]:,}"
        })
    
    st.dataframe(pd.DataFrame(mixed_capacity_data), use_container_width=True)
    
    # Warehouse Capacity Analysis
    if big_warehouses or feeder_warehouses:
        st.markdown("#### 🏭 Warehouse Capacity Analysis")
        
        # Sample warehouse capacity calculation
        sample_warehouse_sizes = [5000, 8000, 12000, 16000]  # sqft
        warehouse_analysis_data = []
        
        for sqft in sample_warehouse_sizes:
            capacity_analysis = calculate_realistic_warehouse_capacity(sqft)
            warehouse_analysis_data.append({
                "Warehouse Size": f"{sqft:,} sqft",
                "Usable Volume": f"{capacity_analysis['usable_volume_m3']:.0f} m³",
                "Theoretical Packages": f"{capacity_analysis['theoretical_packages']:,}",
                "Daily Capacity": f"{capacity_analysis['daily_capacity']:,} orders",
                "Orders per sqft": f"{capacity_analysis['daily_capacity']/sqft:.2f}",
                "Category": "Large" if capacity_analysis['daily_capacity'] >= 800 else "Medium" if capacity_analysis['daily_capacity'] >= 400 else "Small"
            })
        
        st.dataframe(pd.DataFrame(warehouse_analysis_data), use_container_width=True)
        
        # Warehouse efficiency factors
        st.markdown("**Warehouse Efficiency Factors:**")
        warehouse_factors_data = []
        for factor, value in WAREHOUSE_CAPACITY_FACTORS.items():
            warehouse_factors_data.append({
                "Factor": factor.replace('_', ' ').title(),
                "Value": f"{value*100:.0f}%" if factor != 'inventory_turnover' else f"{value}x/day",
                "Description": {
                    'storage_density': "Usable space (rest for aisles, sorting areas)",
                    'storage_height_utilization': "Safe stacking height utilization", 
                    'inventory_turnover': "Daily inventory turnover rate",
                    'operational_efficiency': "Sorting, consolidation efficiency",
                    'peak_capacity_buffer': "Buffer capacity for demand peaks"
                }[factor]
            })
        
        st.dataframe(pd.DataFrame(warehouse_factors_data), use_container_width=True)
