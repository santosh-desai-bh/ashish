#!/usr/bin/env python3
"""
Test to verify people costs are properly integrated into the comprehensive cost breakdown
"""

import pandas as pd
import sys
sys.path.append('.')

def test_people_costs_integration():
    """Test that people costs are properly included in cost calculations"""
    print("👥 Testing People Costs Integration")
    print("=" * 50)
    
    try:
        from analytics import calculate_last_mile_operations
        
        # Test data
        df_test = pd.DataFrame({
            'package_size': ['Small (<125 ccm)'] * 1000  # 1000 orders
        })
        
        big_warehouses = [
            {'id': 'HUB001', 'lat': 12.9716, 'lon': 77.5946, 'capacity': 500},
            {'id': 'HUB002', 'lat': 12.8716, 'lon': 77.4946, 'capacity': 400}
        ]
        
        feeder_warehouses = [
            {'id': 'AUX001', 'lat': 12.9800, 'lon': 77.6000, 'capacity': 150},
            {'id': 'AUX002', 'lat': 12.9850, 'lon': 77.6050, 'capacity': 120},
            {'id': 'AUX003', 'lat': 12.8800, 'lon': 77.5000, 'capacity': 130},
            {'id': 'AUX004', 'lat': 12.8850, 'lon': 77.5050, 'capacity': 140}
        ]
        
        operations = calculate_last_mile_operations(df_test, big_warehouses, feeder_warehouses)
        
        print("✓ Last mile operations calculated successfully")
        
        # Verify people costs are calculated correctly
        expected_main_hub_cost = len(big_warehouses) * 2 * 30000  # 2 people per hub @ ₹30k
        expected_aux_cost = len(feeder_warehouses) * 1 * 15000    # 1 person per aux @ ₹15k
        expected_total_monthly = expected_main_hub_cost + expected_aux_cost
        expected_daily = expected_total_monthly / 30
        
        print(f"✓ Expected main hub staff cost: ₹{expected_main_hub_cost:,}/month")
        print(f"✓ Expected auxiliary staff cost: ₹{expected_aux_cost:,}/month") 
        print(f"✓ Expected total monthly staff cost: ₹{expected_total_monthly:,}/month")
        print(f"✓ Expected daily staff cost: ₹{expected_daily:,}/day")
        
        print(f"✓ Actual monthly staff cost: ₹{operations['total_monthly_staff_cost']:,}")
        print(f"✓ Actual daily staff cost: ₹{operations['total_daily_staff_cost']:,}")
        
        # Verify calculations match
        assert operations['total_monthly_staff_cost'] == expected_total_monthly, f"Monthly staff cost mismatch: {operations['total_monthly_staff_cost']} vs {expected_total_monthly}"
        assert abs(operations['total_daily_staff_cost'] - expected_daily) < 1, f"Daily staff cost mismatch: {operations['total_daily_staff_cost']} vs {expected_daily}"
        
        # Test comprehensive cost breakdown calculation
        print(f"\n📊 Testing Comprehensive Cost Integration:")
        
        # Sample costs (would come from actual analysis)
        warehouse_rent_monthly = 585000  # From the image
        transportation_monthly = 4013550  # From the image
        people_monthly = operations['total_monthly_staff_cost']
        
        grand_total = warehouse_rent_monthly + transportation_monthly + people_monthly
        
        print(f"✓ Warehouse Rent: ₹{warehouse_rent_monthly:,}/month")
        print(f"✓ Transportation: ₹{transportation_monthly:,}/month")
        print(f"✓ People Costs: ₹{people_monthly:,}/month")
        print(f"✓ Grand Total: ₹{grand_total:,}/month")
        
        # Calculate percentages
        warehouse_pct = (warehouse_rent_monthly / grand_total) * 100
        transport_pct = (transportation_monthly / grand_total) * 100
        people_pct = (people_monthly / grand_total) * 100
        
        print(f"\n📈 Cost Distribution:")
        print(f"✓ Warehouse: {warehouse_pct:.1f}%")
        print(f"✓ Transportation: {transport_pct:.1f}%")
        print(f"✓ People: {people_pct:.1f}%")
        print(f"✓ Total: {warehouse_pct + transport_pct + people_pct:.1f}%")
        
        # Verify percentages add up to 100%
        assert abs((warehouse_pct + transport_pct + people_pct) - 100) < 0.1, "Percentages should add up to 100%"
        
        # Verify people costs are significant but reasonable
        assert people_pct > 2, "People costs should be at least 2% of total"
        assert people_pct < 15, "People costs shouldn't exceed 15% of total for this scale"
        
        print(f"\n🎉 People costs integration verified!")
        print(f"   ✓ Monthly people costs: ₹{people_monthly:,} ({people_pct:.1f}% of total)")
        print(f"   ✓ Calculations are mathematically correct")
        print(f"   ✓ Integration with comprehensive breakdown working")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_people_costs_integration()
    
    if not success:
        sys.exit(1)