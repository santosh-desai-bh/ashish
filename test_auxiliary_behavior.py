#!/usr/bin/env python3
"""
Quick test to verify current auxiliary warehouse behavior with different delivery radii
"""
import pandas as pd
import numpy as np
from warehouse_logic import create_comprehensive_feeder_network, calculate_big_warehouse_locations

def test_auxiliary_scaling():
    print("🧪 AUXILIARY WAREHOUSE SCALING TEST")
    print("=" * 50)
    
    # Create sample data (Bengaluru-like distribution)
    np.random.seed(42)
    n_orders = 1000
    
    # Center around Bengaluru coordinates
    center_lat, center_lon = 12.9716, 77.5946
    
    df_test = pd.DataFrame({
        'order_lat': np.random.normal(center_lat, 0.05, n_orders),
        'order_long': np.random.normal(center_lon, 0.05, n_orders),
        'created_date': pd.date_range('2024-01-01', periods=n_orders, freq='H')
    })
    
    # Create big warehouses (should be 5 always)
    big_warehouse_centers, big_warehouse_count = calculate_big_warehouse_locations(df_test)
    print(f"✓ Created {big_warehouse_count} main warehouses")
    
    big_warehouses = []
    for i, (lat, lon) in enumerate(big_warehouse_centers):
        big_warehouses.append({
            'id': i+1,
            'lat': lat,
            'lon': lon,
            'hub_code': f'HUB{i+1}',
            'capacity': 500,
            'type': 'hub'
        })
    
    # Test different delivery radii
    test_radii = [2, 3, 5]
    results = {}
    
    for radius in test_radii:
        print(f"\n📍 Testing delivery radius: {radius}km")
        print("-" * 30)
        
        auxiliaries, clusters = create_comprehensive_feeder_network(
            df_test, 
            big_warehouses, 
            max_distance_from_big=15, 
            delivery_radius=radius
        )
        
        print(f"  Auxiliary warehouses created: {len(auxiliaries)}")
        print(f"  Density clusters found: {len(clusters)}")
        
        results[radius] = {
            'auxiliaries': len(auxiliaries),
            'clusters': len(clusters)
        }
    
    print(f"\n📊 RESULTS SUMMARY")
    print("=" * 30)
    for radius, data in results.items():
        print(f"{radius}km radius: {data['auxiliaries']} auxiliaries, {data['clusters']} clusters")
    
    # Check if scaling is working
    print(f"\n🔍 SCALING ANALYSIS")
    print("=" * 30)
    if results[2]['auxiliaries'] > results[3]['auxiliaries'] > results[5]['auxiliaries']:
        print("✅ Perfect! Auxiliary count decreases as delivery radius increases")
    elif results[2]['auxiliaries'] == results[3]['auxiliaries'] == results[5]['auxiliaries']:
        print("❌ Problem: Auxiliary count is not changing with delivery radius")
    else:
        print("⚠️ Inconsistent: Auxiliary scaling doesn't follow expected pattern")
    
    return results

if __name__ == "__main__":
    test_auxiliary_scaling()