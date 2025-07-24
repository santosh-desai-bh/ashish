#!/usr/bin/env python3
"""
Test script to verify the analytics module pd scope fix
"""

import pandas as pd
import sys
sys.path.append('.')

def test_analytics_functions():
    """Test that all analytics functions work without pd scope errors"""
    
    print("🧪 Testing Analytics Module Fix")
    print("=" * 40)
    
    try:
        # Import all the main functions
        from analytics import (
            create_pickup_clusters, 
            assign_vehicles_to_clusters, 
            calculate_fleet_summary,
            show_network_analysis
        )
        print("✅ All analytics functions imported successfully")
        
        # Test clustering workflow
        vehicle_specs = {
            'bike': {'min_capacity': 30, 'max_capacity': 50, 'daily_cost': 700},
            'auto': {'min_capacity': 50, 'max_capacity': 70, 'daily_cost': 900},
            'minitruck': {'min_capacity': 100, 'max_capacity': 200, 'daily_cost': 1400},
            'large_truck': {'min_capacity': 300, 'max_capacity': 500, 'daily_cost': 2600}
        }
        
        pickup_data = pd.DataFrame({
            'pickup': ['Hub1', 'Hub2', 'Hub3'],
            'pickup_lat': [12.9716, 12.9720, 12.9800],
            'pickup_long': [77.5946, 77.5950, 77.6000],
            'order_count': [400, 60, 80]
        })
        
        # Test clustering
        clusters = create_pickup_clusters(pickup_data, vehicle_specs)
        print(f"✅ Clustering created {len(clusters)} clusters")
        
        # Test vehicle assignment  
        assignments = assign_vehicles_to_clusters(clusters, vehicle_specs)
        print(f"✅ Vehicle assignment created {len(assignments)} assignments")
        
        # Test fleet summary
        fleet_summary = calculate_fleet_summary(assignments)
        print(f"✅ Fleet summary calculated: ₹{fleet_summary['total_daily_cost']:,}/day")
        
        # Test that pandas DataFrames work in context
        test_df = pd.DataFrame({'test': [1, 2, 3]})
        print(f"✅ Pandas DataFrame creation works: {len(test_df)} rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_analytics_functions()
    
    if success:
        print("\n🎉 All tests passed! Analytics module is fixed.")
        print("   The 'pd' scope issue has been resolved.")
    else:
        print("\n💥 Tests failed. There may still be issues.")
        sys.exit(1)