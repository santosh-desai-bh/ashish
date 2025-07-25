import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
import json
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime, timedelta
import hashlib
from io import StringIO
import math

# Import helper functions (create these as separate files)
from data_processing import load_and_process_data, get_date_summary, filter_data_by_date_range, create_map_data, create_representative_daily_sample
from warehouse_logic import find_order_density_clusters, place_feeder_warehouses_near_clusters, determine_optimal_date_range
from visualization import create_warehouse_network, create_relay_routes, add_density_clusters

# Set page config
st.set_page_config(page_title="Blowhorn IF Future Network", layout="wide")

st.title("🗺️ Blowhorn Network Designer")
st.markdown("**Design your ideal logistics network** - See optimal warehouse locations and capacity planning")

# Sidebar for file uploads
st.sidebar.header("📁 Upload Files")
csv_file = st.sidebar.file_uploader("Upload CSV file", type=['csv'])
geojson_file = st.sidebar.file_uploader("Upload GeoJSON file (optional)", type=['geojson', 'json'])

if csv_file is not None:
    # Create file hash for caching
    file_content = csv_file.read().decode('utf-8')
    file_hash = hashlib.md5(file_content.encode()).hexdigest()
    
    # Load and process data (cached)
    with st.spinner("Processing delivery data..."):
        df_clean = load_and_process_data(file_content, file_hash)
    
    # Get daily summary for smart loading
    daily_summary = get_date_summary(df_clean)
    
    # Show dataset overview
    st.sidebar.write("**📊 Dataset Overview:**")
    st.sidebar.write(f"**Total orders:** {len(df_clean):,}")
    st.sidebar.write(f"**Date range:** {df_clean['date_only'].min()} to {df_clean['date_only'].max()}")
    unique_days = df_clean['date_only'].nunique()
    st.sidebar.write(f"**Days of data:** {unique_days}")
    avg_orders_per_day = len(df_clean) // unique_days if unique_days > 0 else 0
    st.sidebar.write(f"**Avg orders/day:** {avg_orders_per_day:,}")
    
    # Simple date selection
    st.sidebar.header("📅 Network Design Parameters")
    
    # Find the busiest day and median day for capacity analysis
    busiest_day = daily_summary.loc[daily_summary['Orders'].idxmax(), 'Date']
    busiest_day_orders = daily_summary['Orders'].max()
    
    # Calculate median day orders
    median_day_orders = int(daily_summary['Orders'].median())
    median_day_idx = (daily_summary['Orders'] - median_day_orders).abs().idxmin()
    median_day = daily_summary.loc[median_day_idx, 'Date']
    
    # Day selector with both options
    day_choice = st.sidebar.radio(
        "📊 Capacity Planning Basis:",
        ["🔥 Busiest Day", "📊 Median Day"],
        help="Choose whether to design for peak demand or typical demand"
    )
    
    if day_choice == "🔥 Busiest Day":
        start_date = busiest_day
        end_date = busiest_day
        selected_orders = busiest_day_orders
        st.sidebar.success(f"✅ Using Busiest Day: {busiest_day} ({busiest_day_orders:,} orders)")
    else:
        start_date = median_day
        end_date = median_day
        selected_orders = median_day_orders
        st.sidebar.success(f"✅ Using Median Day: {median_day} ({median_day_orders:,} orders)")
    
    # Show comparison and analysis insight
    st.sidebar.info(f"📈 Busiest: {busiest_day_orders:,} | 📊 Median: {median_day_orders:,}")
    
    # Simplified capacity insight
    capacity_type = "Peak" if day_choice == "🔥 Busiest Day" else "Typical"
    st.sidebar.info(f"🎯 {capacity_type} demand planning - {selected_orders:,} orders/day")
    
    # Simple capacity target
    st.sidebar.subheader("🎯 Design Target")
    target_daily_orders = st.sidebar.slider(
        "Target daily capacity", 
        500, 5000, selected_orders, 250,
        help="Design network to handle this many orders per day"
    )
    analysis_method = "📈 Representative Daily Sample"  # Always use this for consistency
    
    # Simplified network settings  
    st.sidebar.subheader("🏗️ Network Settings")
    delivery_radius = st.sidebar.selectbox(
        "Last mile delivery radius",
        options=[2, 3, 5],
        index=1,
        format_func=lambda x: f"{x}km radius"
    )
    
    # Fixed defaults for optimized network
    min_cluster_size = 100  # Higher threshold for fewer auxiliaries
    max_distance_from_big = 15  # Allow wider coverage from main warehouses
    
    # Filter/sample data based on selected method
    with st.spinner("Preparing delivery data for analysis..."):
        if analysis_method == "📈 Representative Daily Sample":
            # Use representative daily sample
            df_filtered, actual_daily_orders = create_representative_daily_sample(df_clean, target_daily_orders)
            analysis_title = f"Representative Daily Sample ({actual_daily_orders:,} orders)"
        else:
            # Use actual date range filtering
            df_filtered = filter_data_by_date_range(df_clean, pd.Timestamp(start_date), pd.Timestamp(end_date))
            analysis_title = f"Date Range: {start_date}" + (f" to {end_date}" if start_date != end_date else "")
    
    if len(df_filtered) == 0:
        if analysis_method == "📈 Representative Daily Sample":
            st.warning("Could not create representative sample. Please check your data.")
        else:
            st.warning("No deliveries found for the selected date range. Please adjust the dates or use Representative Sample.")
        st.stop()
    
    # Simple performance indicator
    st.sidebar.success(f"✅ Processing {len(df_filtered):,} orders")
    
    # Simple map controls
    st.sidebar.subheader("🗺️ Map Display")
    show_heatmap = st.sidebar.checkbox("Show order locations", value=True, help="Individual order markers clustered by location")
    
    # Core functionality only
    show_warehouse_recommendations = True
    show_coverage_circles = False
    show_hub_auxiliary_routes = False
    show_collection_routes = False
    show_interhub_relays = False
    show_density_clusters = False
    show_competitors = False
    show_existing_warehouses = False
    
    # Create map and add layers
    with st.spinner("Creating Blowhorn IF Network visualization..."):
        # Create map data
        center_lat, center_lon, heatmap_data, pickup_summary = create_map_data(df_filtered)
        
        # Create folium map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles='OpenStreetMap'
        )
        
        # Add GeoJSON layer if uploaded
        if geojson_file is not None:
            try:
                geojson_data = json.load(geojson_file)
                folium.GeoJson(
                    geojson_data,
                    name="Pincode Boundaries",
                    style_function=lambda feature: {
                        'fillColor': 'transparent',
                        'color': 'blue',
                        'weight': 1,
                        'fillOpacity': 0.1
                    }
                ).add_to(m)
            except:
                st.sidebar.warning("Could not load GeoJSON file")
        
        # Add marker clusters instead of heatmap for precise order visualization
        if show_heatmap and len(df_filtered) > 0:
            # Create marker cluster for orders
            order_cluster = MarkerCluster(
                name="Order Locations",
                overlay=True,
                control=True,
                show=True
            )
            
            # Sample orders for performance (max 2000 markers)
            display_orders = df_filtered.sample(min(2000, len(df_filtered)), random_state=42)
            
            for _, order in display_orders.iterrows():
                folium.CircleMarker(
                    location=[order['order_lat'], order['order_long']],
                    radius=3,
                    popup=f"<b>Order Location</b><br>Customer: {order.get('customer', 'N/A')}<br>Date: {order.get('created_date', 'N/A')}",
                    tooltip="📍 Order location",
                    color='green',
                    weight=1,
                    fill=True,
                    fillColor='green',
                    fillOpacity=0.6
                ).add_to(order_cluster)
            
            order_cluster.add_to(m)
        
        # Add customer pickup hubs (scaled to target capacity)
        customers = df_filtered['customer'].unique()
        all_hub_counts = df_filtered.groupby('pickup').size()
        
        # Scale pickup volumes proportionally to target capacity
        current_total_orders = len(df_filtered)
        if analysis_method == "📈 Representative Daily Sample":
            scaling_factor = target_daily_orders / current_total_orders if current_total_orders > 0 else 1
        else:
            scaling_factor = 1
        
        global_max_orders = int(all_hub_counts.max() * scaling_factor)
        global_min_orders = int(all_hub_counts.min() * scaling_factor)
        
        # Group customers by size for cleaner layer control
        major_customers = []
        
        for customer in customers:
            customer_data = df_filtered[df_filtered['customer'] == customer]
            scaled_volume = int(len(customer_data) * scaling_factor)
            if scaled_volume >= 50:  # Major customers threshold
                major_customers.append(customer)
        
        # Create a single pickup locations layer for clean toggling
        pickup_layer = folium.FeatureGroup(name="🏢 Customer Pickup Locations", show=True)
        
        # Create layers for major customers only (cleaner display)
        for customer in major_customers[:8]:  # Limit to top 8 customers for clean map
            customer_data = df_filtered[df_filtered['customer'] == customer]
            pickup_hubs = customer_data.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
            
            if len(pickup_hubs) > 0:
                # Apply scaling factor to order counts
                pickup_hubs['scaled_orders'] = (pickup_hubs['order_count'] * scaling_factor).astype(int)
                
                for _, hub in pickup_hubs.iterrows():
                    scaled_orders = hub['scaled_orders']
                    
                    # Use global scaling for consistency
                    if global_max_orders > global_min_orders:
                        proportion = (scaled_orders - global_min_orders) / (global_max_orders - global_min_orders)
                        bubble_size = 8 + (proportion * 25)
                    else:
                        bubble_size = 15
                    
                    folium.Marker(
                        location=[hub['pickup_lat'], hub['pickup_long']],
                        popup=f"<b>Customer: {customer}</b><br><b>Pickup Hub: {hub['pickup']}</b><br><b>Daily Orders: {scaled_orders}</b><br><b>Monthly Volume: {scaled_orders * 30:,}</b>",
                        tooltip=f"🏢 {hub['pickup']} - {scaled_orders} orders/day",
                        icon=folium.Icon(color='blue', icon='arrow-up', prefix='fa')
                    ).add_to(pickup_layer)
                    
                    # Add order count label near the blue pickup marker
                    folium.Marker(
                        location=[hub['pickup_lat'] + 0.002, hub['pickup_long'] + 0.002],  # Slight offset
                        icon=folium.DivIcon(
                            html=f'<div style="background: rgba(0,100,200,0.8); color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold; font-size: 10px; border: 1px solid white;">{scaled_orders}</div>',
                            icon_size=(40, 20),
                            icon_anchor=(20, 10)
                        )
                    ).add_to(pickup_layer)
        
        pickup_layer.add_to(m)
        
        # Skip competitor zones and existing warehouses to focus on optimal new network
        
        # Initialize variables
        big_warehouses = []
        feeder_warehouses = []
        density_clusters = []
        big_warehouse_count = 0
        
        # Create warehouse network
        if show_warehouse_recommendations:
            # Get target capacity for dynamic warehouse sizing
            if analysis_method == "📈 Representative Daily Sample":
                warehouse_target_capacity = target_daily_orders
            else:
                warehouse_target_capacity = len(df_filtered)
            
            big_warehouses, feeder_warehouses, density_clusters = create_warehouse_network(
                df_filtered, m, min_cluster_size, max_distance_from_big, delivery_radius, show_coverage_circles, warehouse_target_capacity
            )
            big_warehouse_count = len(big_warehouses)
            
            # Add density clusters if requested
            if show_density_clusters:
                add_density_clusters(m, density_clusters)
            
            # Skip route networks to focus on warehouse visualization
        
        # Calculate first mile vehicle requirements for display below
        from simple_analytics import calculate_first_mile_vehicles
        
        # Calculate scaling factor for vehicle requirements
        current_total_orders = len(df_filtered)
        if analysis_method == "📈 Representative Daily Sample":
            scaling_factor = target_daily_orders / current_total_orders if current_total_orders > 0 else 1
        else:
            scaling_factor = 1
            
        vehicle_counts, vehicle_assignments = calculate_first_mile_vehicles(df_filtered, scaling_factor)
        
        # Add compact layer control (collapsed by default)
        folium.LayerControl(collapsed=True, position='topright').add_to(m)
        
        # Calculate total feeder warehouses and their distribution
        total_feeders = len(feeder_warehouses)
        total_orders_in_radius = sum([feeder.get('orders_within_radius', 0) for feeder in feeder_warehouses])
        
    
    # Clean map display
    st.subheader("🗺️ Your Ideal Network Design")
    
    # Display the map with more height for focus
    map_data = st_folium(m, width=None, height=650, returned_objects=["last_object_clicked"])
    
    # Network overview (reduced spacing)
    st.markdown("<div style='margin-top: -20px;'></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏭 Main Hubs", big_warehouse_count)
    
    with col2:
        st.metric("📦 Auxiliaries", total_feeders)
    
    with col3:
        coverage_percentage = (total_orders_in_radius / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.metric("🎯 Coverage", f"{coverage_percentage:.0f}%")
        
    with col4:
        monthly_orders = len(df_filtered) * 30
        st.metric("📈 Monthly Volume", f"{monthly_orders:,}")
    
    # First Mile Vehicle Summary (clean display below metrics)
    st.subheader("🚛 First Mile Fleet Requirements")
    
    vehicle_cols = st.columns(len([v for v in vehicle_counts.values() if v > 0]))
    col_idx = 0
    
    for vehicle_type, count in vehicle_counts.items():
        if count > 0:
            from simple_analytics import VEHICLE_SPECS
            vehicle_info = VEHICLE_SPECS[vehicle_type]
            
            with vehicle_cols[col_idx]:
                st.metric(
                    f"{vehicle_info['icon']} {vehicle_info['name']}",
                    f"{count} vehicles",
                    help=f"Capacity: {vehicle_info['capacity']} orders/trip"
                )
            col_idx += 1
    
    # Show simple cost analytics (reduced spacing)
    st.markdown("<div style='margin-top: -15px;'></div>", unsafe_allow_html=True)
    if show_warehouse_recommendations and len(feeder_warehouses) > 0:
        try:
            from simple_analytics import show_simple_cost_analysis
            
            # Get target daily orders based on analysis method
            if analysis_method == "📈 Representative Daily Sample":
                target_capacity = target_daily_orders
            else:
                target_capacity = len(df_filtered)
            
            show_simple_cost_analysis(big_warehouses, feeder_warehouses, target_capacity)
        except Exception as e:
            st.error(f"Cost analytics error: {str(e)}")
            
                
else:
    st.info("👆 Please upload your order data CSV file to start designing your network")
    st.markdown("### Required CSV columns:")
    st.markdown("- `created_date`, `pickup_long`, `pickup_lat`, `order_long`, `order_lat`")

# Clean sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("🚛 **Blowhorn Network Designer**")
st.sidebar.markdown("📍 Optimized for Bengaluru logistics")
