import streamlit as st
import pandas as pd
import math

def calculate_first_mile_costs(pickup_hubs, big_warehouses):
    """Calculate optimized first mile costs using mixed vehicle fleet"""
    
    vehicle_specs = {
        'bike': {'capacity': 20, 'cost': 700, 'min_orders': 15, 'max_orders': 25},
        'auto': {'capacity': 35, 'cost': 900, 'min_orders': 30, 'max_orders': 40},
        'mini_truck': {'capacity': 80, 'cost': 1350, 'min_orders': 60, 'max_orders': 100}  # Average of 1200-1500
    }
    
    total_first_mile_cost = 0
    first_mile_details = []
    
    for _, hub in pickup_hubs.iterrows():
        orders = hub['order_count']
        hub_name = hub['pickup']
        hub_lat, hub_lon = hub['pickup_lat'], hub['pickup_long']
        
        # Find nearest big warehouse
        min_distance = float('inf')
        nearest_warehouse = None
        for warehouse in big_warehouses:
            distance = ((hub_lat - warehouse['lat'])**2 + (hub_lon - warehouse['lon'])**2)**0.5 * 111
            if distance < min_distance:
                min_distance = distance
                nearest_warehouse = warehouse
        
        if nearest_warehouse:
            # Optimize vehicle selection based on order volume
            if orders <= 25:
                # Use bikes for small volumes
                trips_needed = math.ceil(orders / vehicle_specs['bike']['capacity'])
                vehicle_type = 'bike'
                cost_per_trip = vehicle_specs['bike']['cost']
            elif orders <= 40:
                # Use autos for medium volumes
                trips_needed = math.ceil(orders / vehicle_specs['auto']['capacity'])
                vehicle_type = 'auto'
                cost_per_trip = vehicle_specs['auto']['cost']
            elif orders <= 100:
                # Use mini trucks for large volumes
                trips_needed = math.ceil(orders / vehicle_specs['mini_truck']['capacity'])
                vehicle_type = 'mini_truck'
                cost_per_trip = vehicle_specs['mini_truck']['cost']
            else:
                # Use combination for very large volumes
                # Prioritize mini trucks, then autos, then bikes
                remaining_orders = orders
                total_cost = 0
                trip_details = []
                
                # Use mini trucks first
                mini_truck_trips = remaining_orders // vehicle_specs['mini_truck']['capacity']
                if mini_truck_trips > 0:
                    total_cost += mini_truck_trips * vehicle_specs['mini_truck']['cost']
                    remaining_orders -= mini_truck_trips * vehicle_specs['mini_truck']['capacity']
                    trip_details.append(f"{mini_truck_trips} mini truck trips")
                
                # Use autos for remaining orders if efficient
                if remaining_orders >= vehicle_specs['auto']['min_orders']:
                    auto_trips = remaining_orders // vehicle_specs['auto']['capacity']
                    if auto_trips > 0:
                        total_cost += auto_trips * vehicle_specs['auto']['cost']
                        remaining_orders -= auto_trips * vehicle_specs['auto']['capacity']
                        trip_details.append(f"{auto_trips} auto trips")
                
                # Use bikes for final remaining orders
                if remaining_orders > 0:
                    bike_trips = math.ceil(remaining_orders / vehicle_specs['bike']['capacity'])
                    total_cost += bike_trips * vehicle_specs['bike']['cost']
                    trip_details.append(f"{bike_trips} bike trips")
                
                hub_cost = total_cost
                vehicle_type = 'mixed'
                trips_needed = f"Mixed: {', '.join(trip_details)}"
                cost_per_trip = 'N/A'
            
            if orders <= 100:
                hub_cost = trips_needed * cost_per_trip
            
            total_first_mile_cost += hub_cost
            
            first_mile_details.append({
                'hub_name': hub_name,
                'orders': orders,
                'nearest_warehouse': f"IF Hub {nearest_warehouse['id']}",
                'distance_km': min_distance,
                'vehicle_type': vehicle_type,
                'trips_needed': trips_needed,
                'cost_per_trip': cost_per_trip,
                'total_cost': hub_cost
            })
    
    return total_first_mile_cost, first_mile_details

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

def show_network_analysis(df_filtered, big_warehouses, feeder_warehouses, big_warehouse_count, total_feeders, total_orders_in_2km, coverage_percentage):
    """Show comprehensive network analysis including detailed cost breakdown"""
    
    st.subheader("📊 Blowhorn IF Network Analysis")
    
    # Get pickup hubs data for cost calculation
    pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
    
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
    
    # Detailed First Mile Analysis
    st.markdown("### 🚴‍♂️ First Mile Vehicle Optimization")
    
    # Vehicle utilization summary
    vehicle_summary = {'bike': 0, 'auto': 0, 'mini_truck': 0, 'mixed': 0}
    total_trips = 0
    
    for detail in first_mile_details:
        vehicle_summary[detail['vehicle_type']] += 1
        if isinstance(detail['trips_needed'], int):
            total_trips += detail['trips_needed']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Vehicle Distribution")
        for vehicle, count in vehicle_summary.items():
            if count > 0:
                percentage = (count / len(first_mile_details)) * 100
                st.write(f"**{vehicle.replace('_', ' ').title()}:** {count} hubs ({percentage:.1f}%)")
        
        st.markdown("#### Cost Efficiency")
        st.write(f"**Total vehicle trips:** {total_trips}")
        st.write(f"**Avg cost per trip:** ₹{first_mile_cost / total_trips:.0f}")
        st.write(f"**Orders per trip:** {df_filtered['pickup'].count() / total_trips:.1f}")
    
    with col2:
        st.markdown("#### Vehicle Specifications")
        st.write("**🏍️ Bikes:** 15-25 orders, ₹700/trip")
        st.write("**🛺 Autos:** 30-40 orders, ₹900/trip")
        st.write("**🚚 Mini Trucks:** 60-100 orders, ₹1,350/trip")
        st.write("**Mixed Strategy:** Optimized combination")
    
    # First Mile Details Table
    st.markdown("### 📋 First Mile Hub Details")
    
    first_mile_df = pd.DataFrame([
        {
            'Pickup Hub': detail['hub_name'],
            'Orders': detail['orders'],
            'Target Hub': detail['nearest_warehouse'],
            'Distance (km)': f"{detail['distance_km']:.1f}",
            'Vehicle Type': detail['vehicle_type'].replace('_', ' ').title(),
            'Trips/Day': detail['trips_needed'],
            'Daily Cost': f"₹{detail['total_cost']:,.0f}"
        }
        for detail in first_mile_details
    ])
    
    st.dataframe(first_mile_df, use_container_width=True)
    
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
        st.write(f"**Orders within 2km of feeders:** {total_orders_in_2km:,}")
        st.write(f"**Coverage percentage:** {coverage_percentage:.1f}%")
        remaining_orders = len(df_filtered) - total_orders_in_2km
        st.write(f"**Hub-direct orders:** {remaining_orders:,}")
        
        if remaining_orders > 0:
            st.write(f"**Avg distance for hub-direct:** 3-8km from IF hubs")
    
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
        if total_orders_in_2km > 0:
            cost_per_covered_order = total_monthly_rent / total_orders_in_2km
            st.write(f"**Rent per feeder order:** ₹{cost_per_covered_order:.2f}")
        
        # Capacity utilization
        total_feeder_capacity = sum([feeder['capacity'] for feeder in feeder_warehouses])
        total_hub_capacity = big_warehouse_count * 500
        feeder_utilization = (total_orders_in_2km / total_feeder_capacity) * 100 if total_feeder_capacity > 0 else 0
        
        st.write(f"**Feeder utilization:** {feeder_utilization:.1f}%")
        st.write(f"**Total network capacity:** {total_hub_capacity + total_feeder_capacity} orders/day")
    
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
        
        low_utilization_vehicles = [d for d in first_mile_details if d['orders'] < 15]
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
