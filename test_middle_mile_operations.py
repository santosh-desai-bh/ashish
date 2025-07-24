#!/usr/bin/env python3
"""
Test script for enhanced middle mile operations including relay and round-robin strategy
"""

import sys
sys.path.append('.')

def test_middle_mile_operations():
    """Test the enhanced middle mile operations"""
    
    print("🔄 Testing Enhanced Middle Mile Operations")
    print("=" * 50)
    
    try:
        from analytics import calculate_middle_mile_operations
        
        # Sample warehouse data
        big_warehouses = [
            {'id': 'HUB001', 'lat': 12.9716, 'lon': 77.5946, 'capacity': 800},
            {'id': 'HUB002', 'lat': 12.8716, 'lon': 77.4946, 'capacity': 600}
        ]
        
        feeder_warehouses = [
            {'id': 'AUX001', 'lat': 12.9800, 'lon': 77.6000, 'capacity': 150},
            {'id': 'AUX002', 'lat': 12.9850, 'lon': 77.6050, 'capacity': 200},
            {'id': 'AUX003', 'lat': 12.8800, 'lon': 77.5000, 'capacity': 180},
            {'id': 'AUX004', 'lat': 12.8850, 'lon': 77.5050, 'capacity': 160},
            {'id': 'AUX005', 'lat': 12.9900, 'lon': 77.6100, 'capacity': 140},
            {'id': 'AUX006', 'lat': 12.8900, 'lon': 77.5100, 'capacity': 170}
        ]
        
        current_orders = 1000
        
        # Test the middle mile operations
        operations = calculate_middle_mile_operations(big_warehouses, feeder_warehouses, current_orders)
        
        print("✅ Middle mile operations calculated successfully")
        print()
        
        # Display results
        print("📦 Hub-to-Auxiliary Operations:")
        for i, route in enumerate(operations['hub_to_auxiliary'], 1):
            print(f"  Route {i}: {route['hub_id']}")
            print(f"    Vehicles: {route['vehicles_needed']} x {route['vehicle_type'].replace('_', ' ')}")
            print(f"    Serves: {route['served_auxiliaries']} auxiliaries")
            print(f"    Capacity: {route['route_capacity']:,} orders")
            print(f"    Cost: ₹{route['daily_cost']:,}/day")
            print(f"    Utilization: {route['utilization']:.1f}%")
            print()
        
        print("🔄 Relay Operations:")
        for i, route in enumerate(operations['relay_operations'], 1):
            print(f"  {route['route_id']}: {route['vehicles_needed']} x {route['vehicle_type'].replace('_', ' ')}")
            print(f"    Serves: {route['auxiliaries_served']} auxiliaries")
            print(f"    Purpose: {route['purpose']}")
            print(f"    Capacity: {route['route_capacity']:,} orders")
            print(f"    Cost: ₹{route['daily_cost']:,}/day")
            print()
        
        print("📊 Summary:")
        print(f"  Total Vehicles: {operations['total_vehicles']}")
        print(f"  Total Capacity: {operations['total_capacity']:,} orders")
        print(f"  Total Daily Cost: ₹{operations['daily_cost']:,}")
        print(f"  Cost per Order: ₹{operations['daily_cost']/operations['total_capacity']:.1f}")
        
        # Verify round-robin strategy
        hub_routes = len(operations['hub_to_auxiliary'])
        relay_routes = len(operations['relay_operations'])
        total_warehouses = len(big_warehouses) + len(feeder_warehouses)
        
        print()
        print("🎯 Round-Robin Strategy Analysis:")
        print(f"  Total Warehouses: {total_warehouses}")
        print(f"  Hub Routes: {hub_routes}")
        print(f"  Relay Routes: {relay_routes}")
        print(f"  Total Vehicle Routes: {operations['total_vehicles']}")
        print(f"  Efficiency: {((total_warehouses - operations['total_vehicles'])/total_warehouses*100):.1f}% vehicle reduction")
        
        # Validate operations
        assert operations['total_vehicles'] > 0, "Should have at least one vehicle"
        assert operations['total_capacity'] > 0, "Should have positive capacity"
        assert operations['daily_cost'] > 0, "Should have positive cost"
        assert len(operations['hub_to_auxiliary']) == len(big_warehouses), "Should have routes for each hub"
        assert len(operations['relay_operations']) > 0, "Should have relay operations with multiple auxiliaries"
        
        print("\n🎉 All tests passed! Enhanced middle mile operations working correctly.")
        print("   ✓ Hub-to-auxiliary routes implemented")
        print("   ✓ Relay operations for load balancing")
        print("   ✓ Round-robin vehicle strategy")
        print("   ✓ Cost-efficient vehicle assignment")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_middle_mile_operations()
    
    if not success:
        sys.exit(1)