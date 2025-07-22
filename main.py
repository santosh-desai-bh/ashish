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
import math

# Import helper functions (create these as separate files)
from data_processing import load_and_process_data, get_date_summary, filter_data_by_date_range, create_map_data
from warehouse_logic import find_order_density_clusters, place_feeder_warehouses_near_clusters, determine_optimal_date_range
from visualization import create_warehouse_network, create_relay_routes, add_density_clusters

# Set page config
st.set_page_config(page_title="Blowhorn IF Future Network", layout="wide")

st.title("🚛 Blowhorn IF Future Network")
st.markdown("Upload your CSV file for intelligent feeder warehouse network design and relay optimization")

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
    
    # Determine optimal range based on data volume
    optimal_days = determine_optimal_date_range(daily_summary, max_orders=5000)
    recommended_start = max(min_date, max_date - timedelta(days=optimal_days-1))
    
    st.sidebar.write(f"**Recommended range:** {optimal_days} days")
    st.sidebar.write(f"**For optimal performance:** ≤5,000 orders")
    
    # Date range selector
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=recommended_start, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)
    
    # Quick date range buttons
    st.sidebar.write("**Quick Analysis Periods:**")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Today"):
            start_date = max_date
            end_date = max_date
    with col2:
        if st.button("Yesterday"):
            yesterday = max_date - timedelta(days=1)
            start_date = yesterday
            end_date = yesterday
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Last 3 Days"):
            start_date = max_date - timedelta(days=2)
            end_date = max_date
    with col2:
        if st.button("This Week"):
            start_date = max_date - timedelta(days=6)
            end_date = max_date
    
    # Show estimated performance impact
    try:
        estimated_orders = daily_summary[
            (daily_summary['Date'] >= start_date) & 
            (daily_summary['Date'] <= end_date)
        ]['Orders'].sum()
    except:
        estimated_orders = 0
    
    performance_color = "green" if estimated_orders <= 5000 else "orange" if estimated_orders <= 10000 else "red"
    st.sidebar.markdown(f"**Estimated orders:** <span style='color:{performance_color}'>{estimated_orders:,}</span>", unsafe_allow_html=True)
    
    # IF Feeder configuration
    st.sidebar.header("🏗️ IF Feeder Configuration")
    min_cluster_size = st.sidebar.slider("Min orders per cluster", 20, 100, 50, 10, 
                                        help="Minimum orders in an area to place feeder warehouse")
    max_distance_from_big = st.sidebar.slider("Max distance from hub (km)", 3, 12, 8, 1,
                                             help="Maximum distance feeder can be from hub warehouse")
    
    # Filter data by date range
    with st.spinner("Loading delivery data for selected period..."):
        df_filtered = filter_data_by_date_range(df_clean, pd.Timestamp(start_date), pd.Timestamp(end_date))
    
    if len(df_filtered) == 0:
        st.warning("No deliveries found for the selected date range. Please adjust the dates.")
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
    show_density_clusters = st.sidebar.checkbox("Show Order Density Clusters", value=True)
    
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
        
        for customer in customers:
            customer_data = df_filtered[df_filtered['customer'] == customer]
            pickup_hubs = customer_data.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
            
            if len(pickup_hubs) > 0:
                customer_layer = folium.FeatureGroup(name=f"🏢 {customer} Hubs ({len(pickup_hubs)} hubs)")
                
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
        
        # Add Q-Commerce competitor zones
        qcommerce_layer = folium.FeatureGroup(name="⚡ Q-Commerce Competitor Zones")
        
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
        
        # Create warehouse network
        if show_warehouse_recommendations:
            big_warehouses, feeder_warehouses, density_clusters = create_warehouse_network(
                df_filtered, m, min_cluster_size, max_distance_from_big
            )
            
            # Add density clusters if requested
            if show_density_clusters:
                add_density_clusters(m, density_clusters)
            
            # Add relay routes if requested
            if show_logistics_routes:
                create_relay_routes(m, df_filtered, big_warehouses, feeder_warehouses)
        else:
            # Initialize empty variables if warehouse recommendations are disabled
            big_warehouses = []
            feeder_warehouses = []
            density_clusters = []
        
        # Add layer control
        folium.LayerControl(collapsed=False).add_to(m)
        
        # Add legend
        total_feeders = len(feeder_warehouses) if 'feeder_warehouses' in locals() else 0
        total_orders_in_2km = sum([feeder['orders_within_2km'] for feeder in feeder_warehouses]) if 'feeder_warehouses' in locals() else 0
        big_warehouse_count = len(big_warehouses) if 'big_warehouses' in locals() else 0
        
        legend_html = f"""
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 360px; height: 300px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>🚛 Blowhorn IF Future Network</h4>
        <p><b>Period:</b> {start_date} to {end_date}</p>
        <p><b>Total Orders:</b> {len(df_filtered):,}</p>
        
        <i style="background:#A23B72; width:15px; height:15px; border-radius:50%; display:inline-block; border:2px solid #2E86AB;"></i> Customer Pickup Hubs<br>
        <i class="fa fa-industry" style="color:red; font-size:16px;"></i> IF Hub Warehouses ({big_warehouse_count})<br>
        <i class="fa fa-cube" style="color:orange"></i> IF Feeder Warehouses ({total_feeders})<br>
        <i style="background:green; width:10px; height:10px; border-radius:50%; display:inline-block;"></i> Order Density Clusters<br>
        <i style="background:green; width:20px; height:3px; display:inline-block;"></i> Hub-Feeder Links<br>
        <i style="background:purple; width:20px; height:3px; display:inline-block;"></i> Inter-Hub Relays<br>
        
        <hr style="margin: 8px 0;">
        <p><small>
        🎯 <b>Feeders at high-density clusters</b><br>
        🔗 <b>Smart hub-feeder linkage system</b><br>
        🔄 <b>Inter-hub relay for load balancing</b><br>
        📊 <b>{total_orders_in_2km:,} orders within 2km of feeders</b>
        </small></p>
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(legend_html))
    
    # Display map
    st.subheader("🗺️ Blowhorn IF Future Network Design")
    st.markdown("**IF Hub Warehouses** (red) → **Feeder Warehouses** (orange) with **intelligent relay system** for optimal load balancing")
    
    # Display the map
    map_data = st_folium(m, width=None, height=650, returned_objects=["last_object_clicked"])
    
    # Enhanced summary stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orders", f"{len(df_filtered):,}")
    
    with col2:
        st.metric("IF Hub Warehouses", big_warehouse_count)
    
    with col3:
        st.metric("IF Feeder Warehouses", total_feeders)
    
    with col4:
        coverage_percentage = (total_orders_in_2km / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.metric("2km Coverage", f"{coverage_percentage:.1f}%")
    
    # Show analytics if warehouses exist
    if show_warehouse_recommendations and len(feeder_warehouses) > 0:
        try:
            from analytics import show_network_analysis
            show_network_analysis(df_filtered, big_warehouses, feeder_warehouses, big_warehouse_count, total_feeders, total_orders_in_2km, coverage_percentage)
        except Exception as e:
            st.error(f"Error loading analytics: {str(e)}")
            st.write("**Fallback: Basic Cost Analysis**")
            
            # Simple fallback cost calculation
            pickup_hubs = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
            
            # Basic first mile cost calculation
            total_first_mile_cost = 0
            for _, hub in pickup_hubs.iterrows():
                orders = hub['order_count']
                if orders <= 25:
                    trips = math.ceil(orders / 20)
                    cost = trips * 700  # bike
                elif orders <= 40:
                    trips = math.ceil(orders / 35)
                    cost = trips * 900  # auto
                else:
                    trips = math.ceil(orders / 80)
                    cost = trips * 1350  # mini truck
                total_first_mile_cost += cost
            
            # Basic middle mile cost
            middle_mile_cost = len(feeder_warehouses) * 2500 * 6 * 30  # 6 trips/day, 30 days
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Daily First Mile Cost", f"₹{total_first_mile_cost:,.0f}")
            with col2:
                st.metric("Monthly Middle Mile Cost", f"₹{middle_mile_cost:,.0f}")
            with col3:
                st.metric("Total Monthly Logistics", f"₹{total_first_mile_cost * 30 + middle_mile_cost:,.0f}")
                
    elif show_warehouse_recommendations and len(feeder_warehouses) == 0:
        st.info("📊 Cost analytics will appear when feeder warehouses are created. Try adjusting the cluster size or distance settings in the sidebar.")
    
    # Debug info
    if show_warehouse_recommendations:
        st.write(f"**Debug Info:** {len(big_warehouses)} hubs, {len(feeder_warehouses)} feeders found")

else:
    st.info("👆 Please upload a CSV file to get started")
    st.markdown("### Expected CSV columns:")
    st.markdown("- `created_date`: Order creation timestamp")
    st.markdown("- `pickup_long`, `pickup_lat`: Pickup coordinates")
    st.markdown("- `order_long`, `order_lat`: Delivery coordinates") 
    st.markdown("- `customer`, `pickup`, `postcode`, `package_size`: Basic info")

# Enhanced instructions
st.sidebar.markdown("---")
st.sidebar.markdown("### 🚛 Blowhorn IF Future Network")
st.sidebar.markdown("""
**Smart Hub-Feeder Architecture:**
- IF Hub warehouses: 1000-1500 sqft, 500 orders/day, ₹35k/month
- IF Feeder warehouses: 400-600 sqft, 50-200 orders/day, ₹12-18k/month
- Intelligent placement at order density clusters
- 2km feeder delivery radius for rapid service

**Advanced Relay System:**
- Inter-hub relays for load balancing
- Hub-to-feeder automated distribution
- Dynamic overflow management
- Real-time capacity optimization

**Blowhorn IF Benefits:**
- Reduced last-mile costs by 30-40%
- 2km average delivery distance
- Scalable hub-feeder model
- Bangalore traffic-optimized design
- Smart relay network for peak handling
""")

st.sidebar.markdown("---")
st.sidebar.markdown("*Blowhorn IF Future Network with intelligent relay system*")
