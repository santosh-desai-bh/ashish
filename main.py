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
    
    # Find the busiest day for optimal network design
    busiest_day = daily_summary.loc[daily_summary['Orders'].idxmax(), 'Date']
    busiest_day_orders = daily_summary['Orders'].max()
    
    # Simple day selector
    if st.sidebar.button("🔥 Use Busiest Day", type="primary"):
        start_date = busiest_day
        end_date = busiest_day
    else:
        start_date = busiest_day
        end_date = busiest_day
    
    st.sidebar.success(f"✅ Using {busiest_day} ({busiest_day_orders:,} orders)")
    
    # Simple capacity target
    st.sidebar.subheader("🎯 Design Target")
    target_daily_orders = st.sidebar.slider(
        "Target daily capacity", 
        500, 5000, busiest_day_orders, 250,
        help="Design network to handle this many orders per day"
    )
    analysis_method = "📈 Representative Daily Sample"  # Always use this for consistency
    
    # Simple network settings  
    st.sidebar.subheader("🏗️ Network Settings")
    delivery_radius = st.sidebar.selectbox(
        "Delivery coverage radius",
        options=[2, 3, 5],
        index=1,
        format_func=lambda x: f"{x}km - {'Fast' if x <= 3 else 'Balanced'} delivery"
    )
    
    # Hidden defaults for clean UI
    min_cluster_size = 30
    max_distance_from_big = 10
    
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
    
    # Simple map controls
    st.sidebar.subheader("🗺️ Map Display")
    show_heatmap = st.sidebar.checkbox("Show order density", value=True)
    show_coverage_circles = False  # Remove circles - use pincode clustering instead
    show_hub_auxiliary_routes = st.sidebar.checkbox("Show warehouse connections", value=True, help="Lines connecting hubs to auxiliaries")
    
    # Always show these for core functionality
    show_warehouse_recommendations = True
    show_collection_routes = False
    show_interhub_relays = True  # Enable inter-hub routes  
    show_density_clusters = False
    show_competitors = False
    show_existing_warehouses = True  # Show for comparison
    
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
        
        # Add all customers as individual layers (no "Other Customers" grouping)
        for customer in customers:
            if customer not in major_customers and len(df_filtered[df_filtered['customer'] == customer]) > 0:
                customer_data = df_filtered[df_filtered['customer'] == customer]
                pickup_hubs = customer_data.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
                
                if len(pickup_hubs) > 0:
                    customer_layer = folium.FeatureGroup(name=f"🏢 {customer[:15]}... ({len(pickup_hubs)})")
                    
                    for _, hub in pickup_hubs.iterrows():
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
                            weight=2,
                            fill=True,
                            fillColor='#A23B72',
                            fillOpacity=0.6
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
            
            # Add route networks if requested (separate options)
            if show_collection_routes or show_hub_auxiliary_routes or show_interhub_relays:
                create_relay_routes(m, df_filtered, big_warehouses, feeder_warehouses, 
                                  show_collection_routes, show_hub_auxiliary_routes, show_interhub_relays)
        
        # Add compact layer control (collapsed by default)
        folium.LayerControl(collapsed=True, position='topright').add_to(m)
        
        # Calculate total feeder warehouses and their distribution
        total_feeders = len(feeder_warehouses)
        total_orders_in_radius = sum([feeder.get('orders_within_radius', 0) for feeder in feeder_warehouses])
        
    
    # Clean map display
    st.subheader("🗺️ Your Ideal Network Design")
    
    # Display the map with more height for focus
    map_data = st_folium(m, width=None, height=600, returned_objects=["last_object_clicked"])
    
    # Key insights only
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🏭 Main Warehouses", big_warehouse_count, help="Large distribution hubs")
    
    with col2:
        st.metric("📦 Auxiliary Warehouses", total_feeders, help="Last-mile delivery points")
    
    with col3:
        coverage_percentage = (total_orders_in_radius / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.metric("🎯 Coverage", f"{coverage_percentage:.0f}%", help=f"Orders within {delivery_radius}km of warehouses")
    
    # Show analytics if warehouses exist
    if show_warehouse_recommendations and len(feeder_warehouses) > 0:
        try:
            from analytics import show_network_analysis
            # Get current vehicle mix from config or use default
            import analytics
            current_vehicle_mix = analytics.LAST_MILE_CONFIG.get('default_mix', 'auto_heavy')
            
            # Get target daily orders based on analysis method
            if analysis_method == "📈 Representative Daily Sample":
                target_capacity = target_daily_orders
            else:
                target_capacity = len(df_filtered)
            
            show_network_analysis(df_filtered, big_warehouses, feeder_warehouses, big_warehouse_count, total_feeders, total_orders_in_radius, coverage_percentage, delivery_radius, current_vehicle_mix, target_capacity)
        except Exception as e:
            st.error(f"Analytics module error: {str(e)}")
            
                
else:
    st.info("👆 Please upload your order data CSV file to start designing your network")
    st.markdown("### Required CSV columns:")
    st.markdown("- `created_date`, `pickup_long`, `pickup_lat`, `order_long`, `order_lat`")

# Clean sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("*Blowhorn Network Designer*")
