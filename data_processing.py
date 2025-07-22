import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

# Caching function for data processing
@st.cache_data
def load_and_process_data(file_content, file_hash):
    """Cache data processing to avoid recomputation"""
    df = pd.read_csv(StringIO(file_content))
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Convert coordinates to numeric
    coordinate_cols = ['pickup_long', 'pickup_lat', 'order_long', 'order_lat']
    for col in coordinate_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Parse created_date
    df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')
    df['date_only'] = df['created_date'].dt.date
    
    # Remove rows with invalid coordinates or dates
    df_clean = df.dropna(subset=coordinate_cols + ['created_date'])
    
    # Sort by date for incremental loading
    df_clean = df_clean.sort_values('created_date')
    
    return df_clean

@st.cache_data
def get_date_summary(df):
    """Get daily order counts for incremental loading decisions"""
    # Check if 'number' column exists, if not use index or row count
    if 'number' in df.columns:
        count_col = 'number'
    else:
        # Create a temporary count column
        df_temp = df.copy()
        df_temp['temp_count'] = 1
        count_col = 'temp_count'
        
    daily_summary = df.groupby('date_only').agg({
        count_col: 'count',
        'customer': 'nunique',
        'pickup': 'nunique'
    }).reset_index()
    daily_summary.columns = ['Date', 'Orders', 'Customers', 'Pickups']
    return daily_summary

@st.cache_data
def filter_data_by_date_range(df, start_date, end_date):
    """Cache date filtering"""
    return df[(df['created_date'] >= start_date) & (df['created_date'] <= end_date)]

@st.cache_data
def create_representative_daily_sample(df_clean, target_orders_per_day=None):
    """Create a representative daily sample for same-day network analysis"""
    
    # Calculate actual daily statistics
    daily_summary = get_date_summary(df_clean)
    
    if target_orders_per_day is None:
        # Use average daily orders
        target_orders_per_day = int(daily_summary['Orders'].mean())
    
    # Get the distribution patterns from the full dataset
    total_orders = len(df_clean)
    total_days = daily_summary['Date'].nunique()
    
    # Calculate customer distribution in full dataset
    customer_dist = df_clean.groupby('customer').size() / total_orders
    pickup_dist = df_clean.groupby(['customer', 'pickup']).size() / total_orders
    
    # Create representative sample maintaining proportions
    sample_orders = []
    current_count = 0
    
    for customer in customer_dist.index:
        if current_count >= target_orders_per_day:
            break
            
        # Calculate how many orders this customer should have in daily sample
        customer_daily_orders = int(customer_dist[customer] * target_orders_per_day)
        customer_data = df_clean[df_clean['customer'] == customer]
        
        if len(customer_data) > 0 and customer_daily_orders > 0:
            # Sample orders from this customer
            n_sample = min(customer_daily_orders, len(customer_data))
            sampled_customer_orders = customer_data.sample(n=n_sample, random_state=42)
            sample_orders.append(sampled_customer_orders)
            current_count += n_sample
    
    # Combine all samples
    if sample_orders:
        representative_sample = pd.concat(sample_orders, ignore_index=True)
        # Add a synthetic date for display
        representative_sample['synthetic_date'] = pd.Timestamp('2025-07-22')  # Today for display
    else:
        # Fallback to simple random sample
        representative_sample = df_clean.sample(n=min(target_orders_per_day, len(df_clean)), random_state=42)
        representative_sample['synthetic_date'] = pd.Timestamp('2025-07-22')
    
    return representative_sample, target_orders_per_day

@st.cache_data
def create_map_data(df_filtered):
    """Cache map data preparation"""
    # Calculate map center
    all_lats = pd.concat([df_filtered['pickup_lat'], df_filtered['order_lat']])
    all_lons = pd.concat([df_filtered['pickup_long'], df_filtered['order_long']])
    center_lat = all_lats.mean()
    center_lon = all_lons.mean()
    
    # Prepare heatmap data
    heatmap_data = [[row['order_lat'], row['order_long']] for _, row in df_filtered.iterrows()]
    
    # Prepare pickup summary
    pickup_summary = df_filtered.groupby(['pickup', 'pickup_long', 'pickup_lat']).size().reset_index(name='order_count')
    
    return center_lat, center_lon, heatmap_data, pickup_summary
