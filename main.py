import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
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

st.title("🚛 Blowhorn Same-Day Delivery Network")
st.markdown("**Single-day peak capacity analysis** for intelligent feeder warehouse placement with pincode-based coverage (no overlaps!)")

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
    
    # Smart date range selection
    st.sidebar.header("📅 Smart Date Range")
    
    min_date = df_clean['date_only'].min()
    max_date = df_clean['date_only'].max()
    
    # For same-day delivery analysis, focus on single-day operations
    # Find the busiest day for optimal network design
    busiest_day = daily_summary.loc[daily_summary['Orders'].idxmax(), 'Date']
    busiest_day_orders = daily_summary['Orders'].max()
    
    # Default to single day (busiest day) for same-day delivery network analysis
    recommended_start = busiest_day
    recommended_end = busiest_day
    
    st.sidebar.write(f"**🎯 Same-Day Delivery Focus:** Single day analysis")
    st.sidebar.write(f"**Recommended:** {busiest_day} ({busiest_day_orders:,} orders)")
    st.sidebar.write(f"**Why single day?** Same-day networks need daily peak capacity planning")
    
    # Date range selector
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=recommended_start, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End Date", value=recommended_end, min_value=min_date, max_value=max_date)
    
    # Quick single-day analysis buttons
    st.sidebar.write("**🚀 Single-Day Analysis:**")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔥 Busiest Day"):
            start_date = busiest_day
            end_date = busiest_day
    with col2:
        if st.button("📅 Latest Day"):
            start_date = max_date
            end_date = max_date
    
    # Multi-day analysis (if needed for comparison)
    st.sidebar.write("**📊 Multi-Day Analysis:**")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Last 3 Days"):
            start_date = max_date - timedelta(days=2)
            end_date = max_date
    with col2:
        if st.button("Peak Week"):
            # Find week with busiest day
            start_date = busiest_day - timedelta(days=3)
            end_date = busiest_day + timedelta(days=3)
    
    # Show estimated performance impact with same-day delivery context
    try:
        estimated_orders = daily_summary[
            (daily_summary['Date'] >= start_date) & 
            (daily_summary['Date'] <= end_date)
        ]['Orders'].sum()
        
        selected_days = (end_date - start_date).days + 1
    except:
        estimated_orders = 0
        selected_days = 1
    
    # Color coding for same-day delivery operations
    if selected_days == 1:
        performance_color = "green" if estimated_orders <= 3000 else "orange" if estimated_orders <= 5000 else "red"
        context = "single-day peak capacity"
    else:
        performance_color = "orange"
        context = f"{selected_days}-day aggregate"
    
    st.sidebar.markdown(f"**Selected orders:** <span style='color:{performance_color}'>{estimated_orders:,}</span> ({context})", unsafe_allow_html=True)
    
    # Warning for multi-day analysis and data sampling option
    if selected_days > 1:
        st.sidebar.warning(f"⚠️ Multi-day selected ({selected_days} days). Same-day delivery networks should be designed for single-day peak capacity!")
    
    # Analysis method selection
    st.sidebar.subheader("📊 Analysis Method")
    analysis_method = st.sidebar.radio(
        "Choose analysis approach:",
        ["📈 Representative Daily Sample", "📅 Actual Date Range"],
        help="Representative sample maintains customer proportions for better network design"
    )
    
    if analysis_method == "📈 Representative Daily Sample":
        target_daily_orders = st.sidebar.slider(
            "Target daily orders", 
            500, 3000, int(daily_summary['Orders'].mean()), 100,
            help="Number of orders to use for network design"
        )
        st.sidebar.info(f"ℹ️ Using {target_daily_orders:,} orders maintaining customer proportions")
    
    # Vehicle Cost Configuration
    st.sidebar.header("💰 Vehicle Cost Configuration")
    with st.sidebar.expander("🚛 Edit Vehicle Costs (₹/day)", expanded=False):
        st.write("**Modify these values to see cost impact:**")
        
        col1, col2 = st.columns(2)
        with col1:
            bike_cost = st.number_input("🏍️ Bike", value=700, min_value=500, max_value=1000, step=50)
            auto_cost = st.number_input("🛺 Auto", value=900, min_value=700, max_value=1200, step=50)
        with col2:
            mini_truck_cost = st.number_input("🚚 Mini Truck", value=1350, min_value=1000, max_value=2000, step=50)
            truck_cost = st.number_input("🚛 Truck", value=1800, min_value=1500, max_value=2500, step=50)
        
        capacity_threshold = st.number_input("📦 Orders per vehicle threshold", value=500, min_value=300, max_value=800, step=50, help="Above this capacity, need additional vehicles")
        
        if st.button("💾 Update Costs"):
            # Update costs in analytics module
            import analytics
            analytics.VEHICLE_COSTS['bike'] = bike_cost
            analytics.VEHICLE_COSTS['auto'] = auto_cost  
            analytics.VEHICLE_COSTS['mini_truck'] = mini_truck_cost
            analytics.VEHICLE_COSTS['truck'] = truck_cost
            analytics.CAPACITY_SCALING['orders_per_vehicle_threshold'] = capacity_threshold
            st.success("✅ Costs updated! Analysis will reflect new costs.")
    
    # Last Mile Configuration
    st.sidebar.header("🏍️ Last Mile Configuration")
    with st.sidebar.expander("🚚 Last Mile Vehicle Mix", expanded=False):
        st.write("**Configure last mile delivery costs and vehicle mix:**")
        
        col1, col2 = st.columns(2)
        with col1:
            bike_cost_per_order = st.number_input("🏍️ Bike Cost/Order", value=25, min_value=20, max_value=35, step=1, help="INR per order for bike delivery")
            auto_cost_per_order = st.number_input("🛺 Auto Cost/Order", value=35, min_value=25, max_value=45, step=1, help="INR per order for auto delivery")
        
        with col2:
            vehicle_mix = st.selectbox("🔄 Vehicle Mix", 
                options=['auto_heavy', 'balanced', 'bike_heavy'], 
                index=0,
                format_func=lambda x: {
                    'auto_heavy': '70% Auto, 30% Bike',
                    'balanced': '50% Auto, 50% Bike', 
                    'bike_heavy': '30% Auto, 70% Bike'
                }[x],
                help="Choose the mix of bikes vs autos for last mile delivery")
        
        if st.button("🔄 Update Last Mile Config"):
            # Update last mile configuration
            import analytics
            analytics.LAST_MILE_CONFIG['cost_per_order_bike'] = bike_cost_per_order
            analytics.LAST_MILE_CONFIG['cost_per_order_auto'] = auto_cost_per_order
            analytics.LAST_MILE_CONFIG['default_mix'] = vehicle_mix
            st.success("✅ Last mile configuration updated!")
    
    # IF Feeder configuration
    st.sidebar.header("🏗️ IF Auxiliary Configuration")
    
    # Delivery radius selector
    delivery_radius = st.sidebar.selectbox(
        "🎯 Target Delivery Radius",
        options=[2, 3, 5, 7, 10],
        index=0,
        help="Maximum distance from feeder warehouse to delivery location"
    )
    
    st.sidebar.write(f"**Selected radius:** {delivery_radius}km")
    if delivery_radius <= 3:
        st.sidebar.success("✅ Fast delivery - Urban strategy")
    elif delivery_radius <= 5:
        st.sidebar.info("ℹ️ Balanced coverage - Mixed strategy") 
    else:
        st.sidebar.warning("⚠️ Wide coverage - Rural strategy")
    
    min_cluster_size = st.sidebar.slider("Min orders per cluster", 10, 100, 30, 10, 
                                        help="Minimum orders in an area to place feeder warehouse")
    max_distance_from_big = st.sidebar.slider("Max distance from hub (km)", 3, 15, 10, 1,
                                             help="Maximum distance feeder can be from hub warehouse")
    
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
    
    # Performance indicator
    if len(df_filtered) > 10000:
        st.warning(f"⚠️ Large dataset ({len(df_filtered):,} orders). Map may load slowly. Consider using a smaller date range.")
    elif len(df_filtered) > 5000:
        st.info(f"ℹ️ Moderate dataset ({len(df_filtered):,} orders). Performance may vary.")
    else:
        st.success(f"✅ Optimal dataset size ({len(df_filtered):,} orders). Fast loading expected.")
    
    # Visualization options
    st.sidebar.header("🎨 Visualization Options")
    show_heatmap = st.sidebar.checkbox("Show Delivery Heatmap", value=True)
    show_warehouse_recommendations = st.sidebar.checkbox("Show IF Network", value=True)
    show_logistics_routes = st.sidebar.checkbox("Show Relay Network", value=False)
    show_density_clusters = st.sidebar.checkbox("Show Order Density Clusters", value=False)
    show_competitors = st.sidebar.checkbox("Show Q-Commerce Competitors", value=False)
    show_existing_warehouses = st.sidebar.checkbox("Show Current Blowhorn Warehouses", value=False)
    
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
        
        # Add heatmap layer
        if show_heatmap and len(heatmap_data) > 0:
            HeatMap(
                heatmap_data,
                name="Delivery Density Heatmap",
                min_opacity=0.3,
                max_zoom=18,
                radius=25,
                blur=20,
                gradient={0.4: 'blue', 0.65: 'lime', 0.8: 'orange', 1.0: 'red'}
            ).add_to(m)
        
        # Add customer pickup hubs
        customers = df_filtered['customer'].unique()
        all_hub_counts = df_filtered.groupby('pickup').size()
        global_max_orders = all_hub_counts.max()
        global_min_orders = all_hub_counts.min()
        
        # Group customers by size for cleaner layer control
        major_customers = []
        minor_customers_data = []
        
        for customer in customers:
            customer_data = df_filtered[df_filtered['customer'] == customer]
            if len(customer_data) >= 100:  # Major customers with ≥100 orders
                major_customers.append(customer)
            else:
                minor_customers_data.append(customer_data)
        
        # Create layers for major customers only
        for customer in major_customers:
            customer_data = df_filtered[df_filtered['customer'] == customer]
            pickup_hubs = customer_data.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
            
            if len(pickup_hubs) > 0:
                customer_layer = folium.FeatureGroup(name=f"🏢 {customer[:15]}... ({len(pickup_hubs)})")
                
                for _, hub in pickup_hubs.iterrows():
                    # Use global scaling for consistency
                    if global_max_orders > global_min_orders:
                        proportion = (hub['order_count'] - global_min_orders) / (global_max_orders - global_min_orders)
                        bubble_size = 8 + (proportion * 32)
                    else:
                        bubble_size = 15
                    
                    folium.CircleMarker(
                        location=[hub['pickup_lat'], hub['pickup_long']],
                        radius=bubble_size,
                        popup=f"<b>Customer: {customer}</b><br><b>Pickup Hub: {hub['pickup']}</b><br><b>Orders: {hub['order_count']}</b>",
                        tooltip=f"🏢 {hub['pickup']} - {hub['order_count']} orders",
                        color='#2E86AB',
                        weight=3,
                        fill=True,
                        fillColor='#A23B72',
                        fillOpacity=0.8
                    ).add_to(customer_layer)
                    
                    folium.Marker(
                        location=[hub['pickup_lat'], hub['pickup_long']],
                        icon=folium.DivIcon(
                            html=f'<div style="color: white; font-weight: bold; font-size: 12px; text-align: center; text-shadow: 1px 1px 1px black;">{hub["order_count"]}</div>',
                            icon_size=(30, 20),
                            icon_anchor=(15, 10)
                        )
                    ).add_to(customer_layer)
                
                customer_layer.add_to(m)
        
        # Add minor customers as a single layer
        if minor_customers_data:
            minor_layer = folium.FeatureGroup(name=f"🏢 Other Customers ({len(minor_customers_data)})")
            
            for customer_data in minor_customers_data:
                pickup_hubs = customer_data.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
                
                for _, hub in pickup_hubs.iterrows():
                    if global_max_orders > global_min_orders:
                        proportion = (hub['order_count'] - global_min_orders) / (global_max_orders - global_min_orders)
                        bubble_size = 8 + (proportion * 32)
                    else:
                        bubble_size = 15
                    
                    folium.CircleMarker(
                        location=[hub['pickup_lat'], hub['pickup_long']],
                        radius=bubble_size,
                        popup=f"<b>Pickup Hub: {hub['pickup']}</b><br><b>Orders: {hub['order_count']}</b>",
                        tooltip=f"🏢 {hub['pickup']} - {hub['order_count']} orders",
                        color='#2E86AB',
                        weight=2,
                        fill=True,
                        fillColor='#A23B72',
                        fillOpacity=0.6
                    ).add_to(minor_layer)
            
            minor_layer.add_to(m)
        
        # Add Q-Commerce competitor zones (if enabled)
        if show_competitors:
            qcommerce_layer = folium.FeatureGroup(name="⚡ Competitors")
            
            qcommerce_hotspots = [
                {"name": "Koramangala (Zepto/Blinkit Hub)", "lat": 12.9279, "lon": 77.6271, "radius": 2000},
                {"name": "Indiranagar (Multi Q-Commerce)", "lat": 12.9784, "lon": 77.6408, "radius": 2000},
                {"name": "HSR Layout (Swiggy Instamart)", "lat": 12.9082, "lon": 77.6476, "radius": 2000},
                {"name": "Whitefield (Tech Hub Q-Commerce)", "lat": 12.9698, "lon": 77.7500, "radius": 2500},
                {"name": "Jayanagar (BigBasket BB Now)", "lat": 12.9249, "lon": 77.5833, "radius": 2000},
                {"name": "BTM Layout (Dense Q-Commerce)", "lat": 12.9116, "lon": 77.6103, "radius": 1800},
                {"name": "Electronic City (IT Hub Delivery)", "lat": 12.8456, "lon": 77.6603, "radius": 2500}
            ]
            
            for zone in qcommerce_hotspots:
                zone_orders = 0
                for _, row in df_filtered.iterrows():
                    lat_diff = abs(row['order_lat'] - zone['lat'])
                    lon_diff = abs(row['order_long'] - zone['lon'])
                    distance_km = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111
                    
                    if distance_km <= (zone['radius'] / 1000):
                        zone_orders += 1
                
                if zone_orders > 50:
                    color = 'red'
                    opacity = 0.3
                elif zone_orders > 20:
                    color = 'orange'
                    opacity = 0.25
                else:
                    color = 'yellow'
                    opacity = 0.2
                
                folium.Circle(
                    location=[zone['lat'], zone['lon']],
                    radius=zone['radius'],
                    popup=f"<b>{zone['name']}</b><br>Your Orders: {zone_orders}<br>Radius: {zone['radius']/1000:.1f} km<br>Competition: Zepto, Blinkit, Swiggy, BigBasket",
                    tooltip=f"⚡ {zone['name']} ({zone_orders} orders)",
                    color=color,
                    weight=2,
                    fill=True,
                    fillColor=color,
                    fillOpacity=opacity
                ).add_to(qcommerce_layer)
            
            qcommerce_layer.add_to(m)
        
        # Add existing Blowhorn warehouses overlay (if enabled)
        if show_existing_warehouses:
            existing_warehouses = [
                {"name": "Mahadevapura", "lat": 12.99119358634228, "lon": 77.70770502883568},
                {"name": "Hebbal", "lat": 13.067425838287791, "lon": 77.60532804961407},
                {"name": "Chandra Layout", "lat": 12.997711927246344, "lon": 77.51384747974708},
                {"name": "Banashankari", "lat": 12.89201406419532, "lon": 77.55634971164321},
                {"name": "Kudlu", "lat": 12.880621849247323, "lon": 77.65504449205629},
                {"name": "Domlur Post Office", "lat": 12.961033527003837, "lon": 77.6360033595211}
            ]
            
            existing_layer = folium.FeatureGroup(name="📍 Existing Warehouses")
            
            for wh in existing_warehouses:
                # Count orders near existing warehouse
                nearby_orders = 0
                for _, row in df_filtered.iterrows():
                    distance = ((row['order_lat'] - wh['lat'])**2 + (row['order_long'] - wh['lon'])**2)**0.5 * 111
                    if distance <= 8:  # 8km radius
                        nearby_orders += 1
                
                # Add existing warehouse marker
                folium.Marker(
                    location=[wh['lat'], wh['lon']],
                    popup=f"<b>Current: {wh['name']}</b><br>Type: Blowhorn Microwarehouse<br>Orders within 8km: {nearby_orders}<br>Status: Existing facility",
                    tooltip=f"📍 {wh['name']} ({nearby_orders} orders nearby)",
                    icon=folium.Icon(color='green', icon='home', prefix='fa')
                ).add_to(existing_layer)
                
                # Add coverage circle for existing warehouse
                folium.Circle(
                    location=[wh['lat'], wh['lon']],
                    radius=8000,
                    popup=f"{wh['name']} Current Coverage (8km)",
                    color='green',
                    weight=2,
                    fill=True,
                    fillColor='green',
                    fillOpacity=0.05
                ).add_to(existing_layer)
            
            existing_layer.add_to(m)
        
        # Initialize variables
        big_warehouses = []
        feeder_warehouses = []
        density_clusters = []
        big_warehouse_count = 0
        
        # Create warehouse network
        if show_warehouse_recommendations:
            big_warehouses, feeder_warehouses, density_clusters = create_warehouse_network(
                df_filtered, m, min_cluster_size, max_distance_from_big, delivery_radius
            )
            big_warehouse_count = len(big_warehouses)
            
            # Add density clusters if requested
            if show_density_clusters:
                add_density_clusters(m, density_clusters)
            
            # Add relay routes if requested
            if show_logistics_routes:
                create_relay_routes(m, df_filtered, big_warehouses, feeder_warehouses)
        
        # Add compact layer control (collapsed by default)
        folium.LayerControl(collapsed=True, position='topright').add_to(m)
        
        # Calculate total feeder warehouses and their distribution
        total_feeders = len(feeder_warehouses)
        total_orders_in_radius = sum([feeder.get('orders_within_radius', 0) for feeder in feeder_warehouses])
        
    
    # Display map
    st.subheader(f"🗺️ Same-Day Network Design - {analysis_title}")
    st.markdown("**IF Hub Warehouses** (red) → **Feeder Warehouses** (orange) with **intelligent relay system** for optimal load balancing")
    
    # Display the map
    map_data = st_folium(m, width=None, height=500, returned_objects=["last_object_clicked"])
    
    # Enhanced summary stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orders", f"{len(df_filtered):,}")
    
    with col2:
        st.metric("IF Hub Warehouses", big_warehouse_count)
    
    with col3:
        st.metric("IF Feeder Warehouses", total_feeders)
    
    with col4:
        coverage_percentage = (total_orders_in_radius / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.metric(f"{delivery_radius}km Coverage", f"{coverage_percentage:.1f}%")
    
    # Show analytics if warehouses exist
    if show_warehouse_recommendations and len(feeder_warehouses) > 0:
        try:
            from analytics import show_network_analysis
            # Get current vehicle mix from config or use default
            import analytics
            current_vehicle_mix = analytics.LAST_MILE_CONFIG.get('default_mix', 'auto_heavy')
            show_network_analysis(df_filtered, big_warehouses, feeder_warehouses, big_warehouse_count, total_feeders, total_orders_in_radius, coverage_percentage, delivery_radius, current_vehicle_mix)
        except Exception as e:
            st.error(f"Analytics module error: {str(e)}")
            
            # Show more comprehensive fallback analysis
            st.subheader("📊 Basic Network Analysis (Fallback)")
            
            # Get pickup hub data
            if 'customer' in df_filtered.columns:
                pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat', 'customer']).size().reset_index(name='order_count')
            else:
                pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
            
            # Basic first mile cost calculation with vehicle distribution
            bike_trips = auto_trips = truck_trips = 0
            total_first_mile_cost = 0
            
            for _, hub in pickup_hubs.iterrows():
                orders = hub['order_count']
                if orders <= 25:
                    bike_trips += 1
                    cost = 700  # simplified: 1 trip per hub
                elif orders <= 40:
                    auto_trips += 1
                    cost = 900
                else:
                    truck_trips += 1
                    cost = 1350
                total_first_mile_cost += cost
            
            # Basic middle mile cost
            middle_mile_cost = len(feeder_warehouses) * 2500 * 6 * 30  # 6 trips/day, 30 days
            
            # Display costs
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("### 💰 Daily First Mile")
                st.metric("Total Cost", f"₹{total_first_mile_cost:,.0f}")
                st.write(f"**Pickup Hubs:** {len(pickup_hubs)}")
                
            with col2:
                st.markdown("### 🚛 Vehicle Distribution")
                st.write(f"🏍️ **Bikes:** {bike_trips} trips")
                st.write(f"🛺 **Autos:** {auto_trips} trips")  
                st.write(f"🚚 **Mini Trucks:** {truck_trips} trips")
                
            with col3:
                st.markdown("### 📈 Total Costs")
                monthly_total = total_first_mile_cost * 30 + middle_mile_cost
                st.metric("Monthly Logistics", f"₹{monthly_total:,.0f}")
                cost_per_order = monthly_total / len(df_filtered) if len(df_filtered) > 0 else 0
                st.write(f"**Cost per order:** ₹{cost_per_order:.1f}")
                
    elif show_warehouse_recommendations and len(feeder_warehouses) == 0:
        st.info("📊 Advanced analytics will appear when feeder warehouses are created. Try adjusting the cluster size or distance settings in the sidebar.")
    
    # Optional debug info (collapsed by default)
    if show_warehouse_recommendations:
        with st.expander("🔧 Debug Information"):
            st.write(f"**Hubs found:** {len(big_warehouses)}")
            st.write(f"**Feeders found:** {len(feeder_warehouses)}")
            st.write(f"**Analytics module:** {'✅ Working' if len(feeder_warehouses) > 0 else '⚠️ Check settings'}")

else:
    st.info("👆 Please upload a CSV file to get started")
    st.markdown("### Expected CSV columns:")
    st.markdown("- `created_date`: Order creation timestamp")
    st.markdown("- `pickup_long`, `pickup_lat`: Pickup coordinates")
    st.markdown("- `order_long`, `order_lat`: Delivery coordinates") 
    st.markdown("- `customer`, `pickup`, `postcode`, `package_size`: Basic info")

# System info (compact)
st.sidebar.markdown("---")
with st.sidebar.expander("ℹ️ About Same-Day Network"):
    st.markdown("""
    **Same-Day Delivery Architecture:**
    - Analysis based on single-day peak capacity
    - Pincode-based feeders (no overlaps!)
    - IF Hub: 1000-1500 sqft, ₹35k/month
    - IF Feeder: 400-600 sqft, ₹12-18k/month
    
    **Same-Day Optimizations:**
    - Circuit-based middle mile (2-3 circuits/day)
    - Volume-based vehicle selection (not customer-type)
    - Geographic boundaries instead of circular overlaps
    - Peak capacity planning for demand spikes
    """)

st.sidebar.markdown("---")
st.sidebar.markdown("*Blowhorn Same-Day Network with pincode-based optimization*")
