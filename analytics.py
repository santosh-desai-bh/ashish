import streamlit as st
import pandas as pd
import math

def calculate_first_mile_costs(pickup_hubs, big_warehouses):
    """Calculate optimized first mile costs using smart scheduling with package size optimization"""
    
    # Enhanced vehicle specs with package size constraints
    vehicle_specs = {
        'bike': {
            'order_capacity': 25, 
            'cost': 700, 
            'allowed_sizes': ['Small', 'Medium', 'Large'],
            'size_capacity': {'Small': 30, 'Medium': 20, 'Large': 15},  # Max items per size
            'volume_limit': 0.5,  # cubic meters
            'suitable_for': ['small_customers']
        },
        'auto': {
            'order_capacity': 40, 
            'cost': 900, 
            'allowed_sizes': ['Small', 'Medium', 'Large', 'XL'],
            'size_capacity': {'Small': 50, 'Medium': 35, 'Large': 25, 'XL': 15},
            'volume_limit': 2.0,  # cubic meters
            'suitable_for': ['medium_customers']
        },
        'mini_truck': {
            'order_capacity': 750, 
            'cost': 1350, 
            'allowed_sizes': ['Small', 'Medium', 'Large', 'XL', 'XXL'],
            'size_capacity': {'Small': 800, 'Medium': 600, 'Large': 400, 'XL': 200, 'XXL': 100},
            'volume_limit': 8.0,  # cubic meters
            'suitable_for': ['large_customers']
        }
    }
    
    # Package size volume mapping (cubic meters per package)
    package_volumes = {
        'Small': 0.01,
        'Medium': 0.03, 
        'Large': 0.06,
        'XL': 0.15,
        'XXL': 0.30
    }
    
    total_first_mile_cost = 0
    first_mile_details = []
    
    # Group pickup hubs by customer for smart scheduling
    customer_hubs = {}
    for _, hub in pickup_hubs.iterrows():
        customer = hub.get('customer', 'Unknown')
        if customer not in customer_hubs:
            customer_hubs[customer] = []
        customer_hubs[customer].append(hub)
    
    for customer, hubs in customer_hubs.items():
        # Calculate total orders and analyze package size distribution for this customer
        total_customer_orders = sum([hub['order_count'] for hub in hubs])
        
        # Analyze package size distribution across all hubs for this customer
        customer_package_profile = analyze_customer_package_profile(customer, hubs)
        
        # Smart vehicle selection based on customer profile, order volume, and package sizes
        if 'herbalife' in customer.lower() or 'nutrition' in customer.lower():
            customer_type = 'B2B_Large'
            preferred_vehicle = 'mini_truck'  # Always use mini truck for B2B large
            consolidation_factor = 0.9
        elif 'trent' in customer.lower() or 'westside' in customer.lower() or any(retail in customer.lower() for retail in ['retail', 'store', 'mart']):
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
            # Multiple hubs - smart consolidation with package size considerations
            warehouse_groups = {}
            
            for hub in hubs:
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
            
            # Optimize trips for each warehouse group
            trip_counter = 1
            for warehouse_id, group_hubs in warehouse_groups.items():
                remaining_hubs = group_hubs.copy()
                
                while remaining_hubs:
                    # Analyze combined package profile for trip optimization
                    combined_package_profile = combine_package_profiles([h['package_profile'] for h in remaining_hubs])
                    
                    # Determine optimal vehicle for this trip
                    total_remaining_orders = sum([h['hub']['order_count'] for h in remaining_hubs])
                    optimal_vehicle = determine_optimal_vehicle_for_packages(
                        total_remaining_orders, combined_package_profile, vehicle_specs, preferred_vehicle
                    )
                    
                    vehicle_type = optimal_vehicle['type']
                    cost_per_trip = vehicle_specs[vehicle_type]['cost']
                    
                    # Calculate capacity considering both orders and package volume
                    order_capacity = vehicle_specs[vehicle_type]['order_capacity'] * consolidation_factor
                    volume_capacity = vehicle_specs[vehicle_type]['volume_limit']
                    
                    # Fill trip considering both order count and package volume constraints
                    current_trip_orders = 0
                    current_trip_volume = 0
                    current_trip_hubs = []
                    current_trip_distance = 0
                    hubs_to_remove = []
                    
                    for hub_info in remaining_hubs:
                        hub = hub_info['hub']
                        hub_orders = hub['order_count']
                        hub_volume = calculate_hub_volume(hub_info['package_profile'], package_volumes)
                        
                        # Check if hub can fit in current trip
                        if (current_trip_orders + hub_orders <= order_capacity and 
                            current_trip_volume + hub_volume <= volume_capacity and
                            vehicle_can_handle_packages(vehicle_specs[vehicle_type], hub_info['package_profile'])):
                            
                            current_trip_orders += hub_orders
                            current_trip_volume += hub_volume
                            current_trip_hubs.append(hub['pickup'])
                            current_trip_distance = max(current_trip_distance, hub_info['distance'])
                            hubs_to_remove.append(hub_info)
                    
                    # Remove processed hubs
                    for hub_info in hubs_to_remove:
                        remaining_hubs.remove(hub_info)
                    
                    # If no hubs could be added, force add one to avoid infinite loop
                    if not current_trip_hubs and remaining_hubs:
                        hub_info = remaining_hubs.pop(0)
                        hub = hub_info['hub']
                        current_trip_orders = hub['order_count']
                        current_trip_volume = calculate_hub_volume(hub_info['package_profile'], package_volumes)
                        current_trip_hubs = [hub['pickup']]
                        current_trip_distance = hub_info['distance']
                    
                    # Calculate trip efficiency
                    order_efficiency = current_trip_orders / order_capacity if order_capacity > 0 else 0
                    volume_efficiency = current_trip_volume / volume_capacity if volume_capacity > 0 else 0
                    overall_efficiency = min(order_efficiency, volume_efficiency)
                    
                    trip_cost = cost_per_trip
                    customer_cost += trip_cost
                    
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
                        'warehouse': f"IF Hub {warehouse_id}",
                        'volume_used': f"{current_trip_volume:.2f}m³",
                        'package_mix': get_package_mix_summary(current_trip_hubs),
                        'vehicle_rationale': f"Optimized for {combined_package_profile['dominant_size']} packages"
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
    
    if 'herbalife' in customer.lower() or 'nutrition' in customer.lower():
        return {
            'dominant_size': 'Medium',
            'has_xl_xxl': False,
            'has_xl': False,
            'has_xxl': False,
            'size_distribution': {'Small': 0.2, 'Medium': 0.6, 'Large': 0.2}
        }
    elif 'trent' in customer.lower() or 'westside' in customer.lower():
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
    hub_name = hub.get('pickup', '')
    
    # Smart defaults based on hub characteristics
    if any(keyword in hub_name.lower() for keyword in ['warehouse', 'distribution', 'dc']):
        return {
            'dominant_size': 'Large',
            'has_xl_xxl': True,
            'has_xl': True,
            'has_xxl': True,
            'size_distribution': {'Small': 0.1, 'Medium': 0.2, 'Large': 0.3, 'XL': 0.3, 'XXL': 0.1}
        }
    elif any(keyword in hub_name.lower() for keyword in ['store', 'retail', 'shop']):
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

def get_package_indicator(package_profile):
    """Get visual indicator for package profile"""
    if package_profile['has_xxl']:
        return "📦📦📦 (Has XXL)"
    elif package_profile['has_xl']:
        return "📦📦 (Has XL)"
    else:
        return "📦 (S/M/L only)"

def calculate_middle_mile_costs(big_warehouses, feeder_warehouses):
    """Calculate middle mile costs for hub-to-feeder distribution"""
    
    # Middle mile vehicle specs (larger capacity for bulk transfers)
    middle_mile_vehicle = {
        'capacity': 200,  # orders per trip
        'cost': 2500,     # cost per trip
        'frequency': 6    # trips per day
    }
    
    total_middle_mile_cost = 0
    middle_mile_details = []
    
    # Hub to Feeder costs
    for feeder in feeder_warehouses:
        parent_hub = next((hub for hub in big_warehouses if hub['id'] == feeder['parent']), None)
        if parent_hub:
            # Calculate trips needed based on feeder capacity
            feeder_capacity = feeder['capacity']
            trips_per_day = math.ceil(feeder_capacity / middle_mile_vehicle['capacity'])
            
            # Cost per day for this feeder
            daily_cost = trips_per_day * middle_mile_vehicle['cost']
            monthly_cost = daily_cost * 30
            
            total_middle_mile_cost += monthly_cost
            
            middle_mile_details.append({
                'route': f"IF Hub {parent_hub['id']} → Feeder {feeder['id']}",
                'distance_km': feeder['distance_to_parent'],
                'feeder_capacity': feeder_capacity,
                'trips_per_day': trips_per_day,
                'daily_cost': daily_cost,
                'monthly_cost': monthly_cost
            })
    
    # Inter-hub relay costs (if multiple hubs)
    inter_hub_cost = 0
    inter_hub_details = []
    
    if len(big_warehouses) > 1:
        # Calculate inter-hub relay costs
        relay_vehicle = {
            'capacity': 150,  # orders per relay
            'cost': 3000,     # cost per relay trip
            'frequency': 2    # relays per day between each hub pair
        }
        
        for i, hub1 in enumerate(big_warehouses):
            for j, hub2 in enumerate(big_warehouses):
                if i < j:  # Avoid duplicate routes
                    distance = ((hub1['lat'] - hub2['lat'])**2 + (hub1['lon'] - hub2['lon'])**2)**0.5 * 111
                    
                    # Daily relay cost between these hubs
                    daily_relay_cost = relay_vehicle['frequency'] * relay_vehicle['cost']
                    monthly_relay_cost = daily_relay_cost * 30
                    
                    inter_hub_cost += monthly_relay_cost
                    
                    inter_hub_details.append({
                        'route': f"IF Hub {hub1['id']} ↔ IF Hub {hub2['id']}",
                        'distance_km': distance,
                        'relays_per_day': relay_vehicle['frequency'],
                        'daily_cost': daily_relay_cost,
                        'monthly_cost': monthly_relay_cost
                    })
    
    total_middle_mile_cost += inter_hub_cost
    
    return total_middle_mile_cost, middle_mile_details, inter_hub_details

def show_network_analysis(df_filtered, big_warehouses, feeder_warehouses, big_warehouse_count, total_feeders, total_orders_in_radius, coverage_percentage, delivery_radius=2):
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
    
    # Create cost overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 💰 Daily First Mile Costs")
        st.metric("Total Daily Cost", f"₹{first_mile_cost:,.0f}")
        st.metric("Monthly Cost", f"₹{first_mile_cost * 30:,.0f}")
        st.write(f"**Pickup Hubs:** {len(pickup_hubs)}")
        st.write(f"**Avg Cost per Hub:** ₹{first_mile_cost / len(pickup_hubs):,.0f}")
    
    with col2:
        st.markdown("### 🚛 Monthly Middle Mile Costs")
        st.metric("Hub-Feeder Distribution", f"₹{middle_mile_cost - (len(inter_hub_details) * inter_hub_details[0]['monthly_cost'] if inter_hub_details else 0):,.0f}")
        if inter_hub_details:
            inter_hub_monthly = sum([detail['monthly_cost'] for detail in inter_hub_details])
            st.metric("Inter-Hub Relays", f"₹{inter_hub_monthly:,.0f}")
        st.metric("Total Middle Mile", f"₹{middle_mile_cost:,.0f}")
    
    with col3:
        st.markdown("### 📈 Total Network Costs")
        monthly_first_mile = first_mile_cost * 30
        total_logistics_cost = monthly_first_mile + middle_mile_cost
        st.metric("Total Monthly Logistics", f"₹{total_logistics_cost:,.0f}")
        st.metric("Annual Logistics", f"₹{total_logistics_cost * 12:,.0f}")
        cost_per_order = total_logistics_cost / len(df_filtered) if len(df_filtered) > 0 else 0
        st.metric("Cost per Order", f"₹{cost_per_order:.2f}")
    
    # Detailed First Mile Analysis with Smart Scheduling
    st.markdown("### 🚴‍♂️ Smart First Mile Scheduling & Vehicle Optimization")
    
    # Customer-wise summary
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏢 Customer Profile Analysis")
        
        total_trips = sum([detail['total_trips'] for detail in first_mile_details])
        total_customers = len(first_mile_details)
        
        for detail in first_mile_details[:5]:  # Show top 5 customers
            efficiency_color = "🟢" if detail['cost_per_order'] < 5 else "🟡" if detail['cost_per_order'] < 10 else "🔴"
            st.write(f"{efficiency_color} **{detail['customer']}** ({detail['customer_type']})")
            st.write(f"   📦 {detail['total_orders']} orders, {detail['total_trips']} trips, ₹{detail['cost_per_order']:.1f}/order")
        
        if len(first_mile_details) > 5:
            st.write(f"... and {len(first_mile_details) - 5} more customers")
    
    with col2:
        st.markdown("#### 🚛 Vehicle Utilization Strategy")
        
        # Analyze vehicle distribution
        vehicle_usage = {'bike': 0, 'auto': 0, 'mini_truck': 0}
        for detail in first_mile_details:
            vehicle_usage[detail['preferred_vehicle']] += detail['total_trips']
        
        total_vehicle_trips = sum(vehicle_usage.values())
        for vehicle, trips in vehicle_usage.items():
            if trips > 0:
                percentage = (trips / total_vehicle_trips) * 100
                vehicle_emoji = "🏍️" if vehicle == 'bike' else "🛺" if vehicle == 'auto' else "🚚"
                st.write(f"{vehicle_emoji} **{vehicle.replace('_', ' ').title()}:** {trips} trips ({percentage:.1f}%)")
        
        st.markdown("#### 💡 Smart Scheduling Benefits")
        st.write("✅ **Single trip optimization** - No multiple pickups")
        st.write("✅ **Customer-specific vehicles** - Herbalife gets mini trucks")
        st.write("✅ **Route consolidation** - Multiple hubs per trip")
        st.write("✅ **Cost efficiency** - Optimal vehicle selection")
    
    # Detailed trip breakdown
    st.markdown("### 📋 Detailed Trip Schedule")
    
    # Create comprehensive trip details table
    all_trips = []
    for customer_detail in first_mile_details:
        customer = customer_detail['customer']
        for trip in customer_detail['scheduled_trips']:
            all_trips.append({
                'Customer': customer,
                'Trip ID': trip['trip_id'],
                'Vehicle': trip['vehicle'].replace('_', ' ').title(),
                'Orders': trip['orders'],
                'Hubs': len(trip['hubs']),
                'Hub Names': ', '.join(trip['hubs'][:2]) + ('...' if len(trip['hubs']) > 2 else ''),
                'Efficiency': trip['overall_efficiency'],
                'Distance (km)': f"{trip['distance']:.1f}",
                'Target Warehouse': trip['warehouse'],
                'Cost': f"₹{trip['cost']:,.0f}"
            })
    
    if all_trips:
        trips_df = pd.DataFrame(all_trips)
        st.dataframe(trips_df, use_container_width=True)
        
        # Trip analysis
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 📊 Trip Efficiency Analysis")
            high_efficiency = len([t for t in all_trips if float(t['Efficiency'].rstrip('%')) >= 80])
            medium_efficiency = len([t for t in all_trips if 60 <= float(t['Efficiency'].rstrip('%')) < 80])
            low_efficiency = len([t for t in all_trips if float(t['Efficiency'].rstrip('%')) < 60])
            
            st.write(f"🟢 **High Efficiency (≥80%):** {high_efficiency} trips")
            st.write(f"🟡 **Medium Efficiency (60-79%):** {medium_efficiency} trips")
            st.write(f"🔴 **Low Efficiency (<60%):** {low_efficiency} trips")
        
        with col2:
            st.markdown("#### 🚛 Vehicle Performance")
            vehicle_costs = {}
            vehicle_orders = {}
            
            for trip in all_trips:
                vehicle = trip['Vehicle']
                cost = int(trip['Cost'].replace('₹', '').replace(',', ''))
                orders = trip['Orders']
                
                if vehicle not in vehicle_costs:
                    vehicle_costs[vehicle] = 0
                    vehicle_orders[vehicle] = 0
                
                vehicle_costs[vehicle] += cost
                vehicle_orders[vehicle] += orders
            
            for vehicle in vehicle_costs:
                avg_cost_per_order = vehicle_costs[vehicle] / vehicle_orders[vehicle] if vehicle_orders[vehicle] > 0 else 0
                st.write(f"**{vehicle}:** ₹{avg_cost_per_order:.1f}/order")
        
        with col3:
            st.markdown("#### 🎯 Customer Optimization")
            customer_performance = {}
            for detail in first_mile_details:
                customer_performance[detail['customer']] = detail['cost_per_order']
            
            # Sort by cost efficiency
            sorted_customers = sorted(customer_performance.items(), key=lambda x: x[1])
            
            st.write("**Most Cost Efficient:**")
            for customer, cost in sorted_customers[:3]:
                st.write(f"• {customer[:15]}... ₹{cost:.1f}/order")
    
    # Strategic recommendations based on customer analysis
    st.markdown("### 💡 Smart Scheduling Optimization Recommendations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🚚 Vehicle Strategy Optimization")
        
        # Analyze high-volume customers
        high_volume_customers = [d for d in first_mile_details if d['total_orders'] >= 500]
        medium_volume_customers = [d for d in first_mile_details if 100 <= d['total_orders'] < 500]
        low_volume_customers = [d for d in first_mile_details if d['total_orders'] < 100]
        
        if high_volume_customers:
            st.success(f"✅ {len(high_volume_customers)} high-volume customers using mini trucks efficiently")
            for customer in high_volume_customers[:2]:
                st.write(f"• **{customer['customer']}:** {customer['total_orders']} orders, {customer['total_trips']} trips")
        
        if len(medium_volume_customers) > 3:
            st.info(f"ℹ️ Consider consolidating {len(medium_volume_customers)} medium-volume customers")
        
        if low_volume_customers:
            inefficient_customers = [c for c in low_volume_customers if c['cost_per_order'] > 15]
            if inefficient_customers:
                st.warning(f"⚠️ {len(inefficient_customers)} small customers have high per-order costs")
                st.write("**Recommendations:**")
                st.write("- Group small customers by area")
                st.write("- Use shared bike/auto trips")
                st.write("- Increase pickup frequency")
    
    with col2:
        st.markdown("#### 📈 Performance Improvements")
        
        # Calculate potential savings
        current_total = sum([d['total_cost'] for d in first_mile_details])
        
        # Estimate savings from better consolidation
        potential_savings = 0
        for detail in first_mile_details:
            if detail['cost_per_order'] > 10:  # High cost customers
                potential_savings += detail['total_cost'] * 0.2  # 20% savings potential
        
        if potential_savings > 0:
            st.metric("Potential Monthly Savings", f"₹{potential_savings * 30:,.0f}")
            st.write("**Optimization strategies:**")
            st.write("- Better route consolidation")
            st.write("- Optimal vehicle sizing")
            st.write("- Time window optimization")
            st.write("- Multi-customer shared trips")
        
        # Show efficiency gains
        avg_efficiency = sum([float(t['Efficiency'].rstrip('%')) for t in all_trips]) / len(all_trips) if all_trips else 0
        st.metric("Average Trip Efficiency", f"{avg_efficiency:.1f}%")
        
        if avg_efficiency < 75:
            st.write("🎯 **Target:** Achieve 80%+ efficiency")
        else:
            st.write("✅ **Excellent:** High efficiency achieved")
    
    # Middle Mile Analysis
    st.markdown("### 🔄 Middle Mile Distribution Network")
    
    if middle_mile_details:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Hub-Feeder Distribution")
            st.write(f"**Active routes:** {len(middle_mile_details)}")
            total_hub_feeder_cost = sum([detail['monthly_cost'] for detail in middle_mile_details])
            st.write(f"**Monthly cost:** ₹{total_hub_feeder_cost:,.0f}")
            avg_route_cost = total_hub_feeder_cost / len(middle_mile_details)
            st.write(f"**Avg cost per route:** ₹{avg_route_cost:,.0f}")
        
        with col2:
            st.markdown("#### Distribution Specs")
            st.write("**🚛 Distribution Vehicle:** 200 orders/trip, ₹2,500/trip")
            st.write("**Frequency:** 6 trips/day per route")
            st.write("**Purpose:** Bulk hub-to-feeder transfer")
    
    # Middle Mile Details Table
    if middle_mile_details:
        st.markdown("#### Hub-Feeder Distribution Routes")
        
        middle_mile_df = pd.DataFrame([
            {
                'Route': detail['route'],
                'Distance (km)': f"{detail['distance_km']:.1f}",
                'Feeder Capacity': detail['feeder_capacity'],
                'Trips/Day': detail['trips_per_day'],
                'Daily Cost': f"₹{detail['daily_cost']:,.0f}",
                'Monthly Cost': f"₹{detail['monthly_cost']:,.0f}"
            }
            for detail in middle_mile_details
        ])
        
        st.dataframe(middle_mile_df, use_container_width=True)
    
    # Inter-Hub Relay Analysis
    if inter_hub_details:
        st.markdown("#### Inter-Hub Relay Network")
        
        inter_hub_df = pd.DataFrame([
            {
                'Relay Route': detail['route'],
                'Distance (km)': f"{detail['distance_km']:.1f}",
                'Relays/Day': detail['relays_per_day'],
                'Daily Cost': f"₹{detail['daily_cost']:,.0f}",
                'Monthly Cost': f"₹{detail['monthly_cost']:,.0f}",
                'Purpose': 'Load balancing & overflow'
            }
            for detail in inter_hub_details
        ])
        
        st.dataframe(inter_hub_df, use_container_width=True)
    
    # Original feeder analysis continues...
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 IF Feeder Distribution")
        
        # Size distribution
        size_distribution = {}
        for feeder in feeder_warehouses:
            size = feeder['size_category']
            if size not in size_distribution:
                size_distribution[size] = 0
            size_distribution[size] += 1
        
        for size, count in size_distribution.items():
            if size == "Large":
                capacity_range = "200"
            elif size == "Medium":
                capacity_range = "100"
            else:
                capacity_range = "50"
            st.write(f"**{size} Feeders:** {count} units ({capacity_range} orders/day each)")
        
        # Coverage efficiency
        st.markdown("### 📍 Network Coverage")
        st.write(f"**Orders within {delivery_radius}km of feeders:** {total_orders_in_radius:,}")
        st.write(f"**Coverage percentage:** {coverage_percentage:.1f}%")
        remaining_orders = len(df_filtered) - total_orders_in_radius
        st.write(f"**Hub-direct orders:** {remaining_orders:,}")
        
        if remaining_orders > 0:
            st.write(f"**Avg distance for hub-direct:** {delivery_radius+1}-8km from IF hubs")
    
    with col2:
        st.markdown("### 💰 IF Network Economics")
        
        # Calculate costs more precisely
        hub_warehouse_rent = big_warehouse_count * 35000  # Updated hub rent
        feeder_rent_total = 0
        for feeder in feeder_warehouses:
            if feeder['size_category'] == 'Large':
                feeder_rent_total += 18000
            elif feeder['size_category'] == 'Medium':
                feeder_rent_total += 15000
            else:
                feeder_rent_total += 12000
        
        total_monthly_rent = hub_warehouse_rent + feeder_rent_total
        
        st.write(f"**IF Hub rent:** ₹{hub_warehouse_rent:,}/month")
        st.write(f"**IF Feeder rent:** ₹{feeder_rent_total:,}/month")
        st.write(f"**Total monthly rent:** ₹{total_monthly_rent:,}")
        st.write(f"**Total logistics cost:** ₹{total_logistics_cost:,}/month")
        st.write(f"**Combined monthly cost:** ₹{total_monthly_rent + total_logistics_cost:,}")
        
        # Efficiency metrics
        if total_orders_in_radius > 0:
            cost_per_covered_order = total_monthly_rent / total_orders_in_radius
            st.write(f"**Rent per feeder order:** ₹{cost_per_covered_order:.2f}")
        
        # Capacity utilization
        total_feeder_capacity = sum([feeder['capacity'] for feeder in feeder_warehouses])
        total_hub_capacity = big_warehouse_count * 500
        feeder_utilization = (total_orders_in_radius / total_feeder_capacity) * 100 if total_feeder_capacity > 0 else 0
        
        st.write(f"**Feeder utilization:** {feeder_utilization:.1f}%")
        st.write(f"**Total network capacity:** {total_hub_capacity + total_feeder_capacity} orders/day")
        st.write(f"**Delivery strategy:** {delivery_radius}km radius network")
    
    # Cost Optimization Recommendations
    st.markdown("### 💡 Cost Optimization Recommendations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### First Mile Optimization")
        
        # Analyze vehicle efficiency
        high_cost_hubs = [d for d in first_mile_details if d['total_cost'] > 2000]
        if high_cost_hubs:
            st.warning(f"⚠️ {len(high_cost_hubs)} hubs have high daily costs (>₹2,000)")
            st.write("**Recommendations:**")
            st.write("- Consider consolidating nearby high-cost hubs")
            st.write("- Optimize vehicle selection for order volumes")
            st.write("- Increase pickup frequency to reduce per-trip costs")
        
        low_utilization_vehicles = [d for d in first_mile_details if d['total_orders'] < 15]
        if low_utilization_vehicles:
            st.info(f"ℹ️ {len(low_utilization_vehicles)} hubs have low order volumes (<15)")
            st.write("**Suggestions:**")
            st.write("- Use bikes for very small volumes")
            st.write("- Combine multiple small hubs in single trip")
    
    with col2:
        st.markdown("#### Middle Mile Optimization")
        
        # Analyze middle mile efficiency
        high_frequency_routes = [d for d in middle_mile_details if d['trips_per_day'] > 3]
        if high_frequency_routes:
            st.warning(f"⚠️ {len(high_frequency_routes)} routes need >3 trips/day")
            st.write("**Recommendations:**")
            st.write("- Consider larger distribution vehicles")
            st.write("- Increase feeder warehouse capacity")
            st.write("- Optimize hub-feeder distance")
        
        if inter_hub_details:
            st.success("✅ Inter-hub relay system active for load balancing")
            st.write("**Benefits:**")
            st.write("- Dynamic overflow management")
            st.write("- Improved network resilience")
    
    # Continue with existing feeder analysis...
    # [Rest of the original function remains the same]
