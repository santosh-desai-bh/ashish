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
    'auto': {'capacity': 30, 'icon': '🛺', 'name': 'Auto'},
    'mini_truck': {'capacity': 60, 'icon': '🚚', 'name': 'Mini Truck'}, 
    'truck': {'capacity': 120, 'icon': '🚛', 'name': 'Truck'}
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
    
    # Transportation costs (corrected)
    # First mile: Customer pickups to main warehouse (consolidated trips)
    first_mile_trips_per_day = max(1, total_daily_orders / 40)  # 40 orders per pickup trip
    first_mile_monthly = first_mile_trips_per_day * VEHICLE_COSTS['mini_truck_per_trip'] * 30
    
    # Middle mile: Main to auxiliary (inventory restocking)
    middle_mile_trips_per_day = auxiliary_warehouse_count * 2  # 2 trips per auxiliary per day
    middle_mile_monthly = middle_mile_trips_per_day * VEHICLE_COSTS['mini_truck_per_trip'] * 30
    
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

def calculate_first_mile_vehicles(df_filtered, scaling_factor=1):
    """Calculate vehicle requirements for first mile operations"""
    
    # Get pickup data scaled to target capacity
    pickup_volumes = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size()
    
    vehicle_assignments = []
    total_vehicles = {'auto': 0, 'mini_truck': 0, 'truck': 0}
    
    for pickup_location, volume in pickup_volumes.items():
        scaled_volume = int(volume * scaling_factor)
        
        # Determine vehicle type based on daily volume
        if scaled_volume <= 25:
            vehicle_type = 'auto'
            trips_needed = max(1, scaled_volume // 25)
        elif scaled_volume <= 50:
            vehicle_type = 'mini_truck' 
            trips_needed = max(1, scaled_volume // 50)
        else:
            vehicle_type = 'truck'
            trips_needed = max(1, scaled_volume // 100)
        
        # For high volume locations, might need multiple vehicles
        vehicles_needed = max(1, trips_needed // 6)  # Max 6 trips per vehicle per day
        
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