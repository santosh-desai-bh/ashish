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
