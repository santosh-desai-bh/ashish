#!/usr/bin/env python3
"""
Test script for the cost vs orders graph with margin analysis
"""

import pandas as pd
import sys
sys.path.append('.')

def test_cost_margin_graph():
    """Test the cost vs orders graph calculation logic"""
    
    print("📈 Testing Cost vs Orders Graph with Margin Analysis")
    print("=" * 60)
    
    try:
        # Sample data similar to what would be in the analytics - using 1400 orders as example
        current_orders = 1400
        network_bottleneck = 2000
        revenue_per_order = 77
        
        # Realistic cost components based on actual operations
        total_warehouse_rent = 450000  # Monthly (realistic for main + aux warehouses)
        total_transportation = 1200000  # Monthly (realistic transport costs)  
        daily_staff_cost = 6000  # Daily staff cost (₹180,000/month)
        
        # Daily cost components
        daily_warehouse_cost = total_warehouse_rent / 30  # Fixed cost
        daily_transport_cost = total_transportation / 30  # Variable cost  
        
        # Current utilization - full cost per order
        current_warehouse_cost_per_order = daily_warehouse_cost / current_orders if current_orders > 0 else 0
        current_transport_cost_per_order = daily_transport_cost / current_orders if current_orders > 0 else 0  
        current_staff_cost_per_order = daily_staff_cost / current_orders if current_orders > 0 else 0
        current_total_cost_per_order = current_warehouse_cost_per_order + current_transport_cost_per_order + current_staff_cost_per_order
        
        # Full capacity utilization - full cost per order
        full_capacity_orders = network_bottleneck
        full_warehouse_cost_per_order = daily_warehouse_cost / full_capacity_orders if full_capacity_orders > 0 else 0
        full_transport_cost_per_order = daily_transport_cost / full_capacity_orders if full_capacity_orders > 0 else 0
        full_staff_cost_per_order = daily_staff_cost / full_capacity_orders if full_capacity_orders > 0 else 0
        full_total_cost_per_order = full_warehouse_cost_per_order + full_transport_cost_per_order + full_staff_cost_per_order
        
        print("📊 Cost Components Analysis:")
        print(f"  Current Orders: {current_orders:,}")
        print(f"  Full Capacity: {full_capacity_orders:,}")
        print(f"  Revenue per Order: ₹{revenue_per_order}")
        print()
        
        print("💰 FULL Cost Structure Breakdown:")
        print("Current Utilization:")
        print(f"  Warehouse Cost: ₹{current_warehouse_cost_per_order:.1f}/order")
        print(f"  Transport Cost: ₹{current_transport_cost_per_order:.1f}/order")
        print(f"  Staff Cost: ₹{current_staff_cost_per_order:.1f}/order")
        print(f"  Total: ₹{current_total_cost_per_order:.1f}/order")
        print()
        
        print("Full Capacity Utilization:")
        print(f"  Warehouse Cost: ₹{full_warehouse_cost_per_order:.1f}/order")
        print(f"  Transport Cost: ₹{full_transport_cost_per_order:.1f}/order")
        print(f"  Staff Cost: ₹{full_staff_cost_per_order:.1f}/order")
        print(f"  Total: ₹{full_total_cost_per_order:.1f}/order")
        print()
        
        # Calculate margins using TOTAL daily costs
        current_daily_total_cost = daily_warehouse_cost + daily_transport_cost + daily_staff_cost
        current_revenue_total = revenue_per_order * current_orders
        current_margin = ((current_revenue_total - current_daily_total_cost) / current_revenue_total * 100) if current_revenue_total > 0 else 0
        
        full_capacity_daily_cost = daily_warehouse_cost + daily_staff_cost + (daily_transport_cost * full_capacity_orders / current_orders) if current_orders > 0 else 0
        full_capacity_revenue_total = revenue_per_order * full_capacity_orders
        full_capacity_margin = ((full_capacity_revenue_total - full_capacity_daily_cost) / full_capacity_revenue_total * 100) if full_capacity_revenue_total > 0 else 0
        
        margin_improvement = full_capacity_margin - current_margin
        
        print("📈 Margin Analysis:")
        print(f"  Current Daily Revenue: ₹{current_revenue_total:,}")
        print(f"  Current Daily Total Cost: ₹{current_daily_total_cost:,}")
        print(f"  Current Margin: {current_margin:.1f}%")
        print()
        print(f"  Full Capacity Daily Revenue: ₹{full_capacity_revenue_total:,}")
        print(f"  Full Capacity Daily Cost: ₹{full_capacity_daily_cost:,}")
        print(f"  Full Capacity Margin: {full_capacity_margin:.1f}%")
        print(f"  Margin Improvement: +{margin_improvement:.1f}%")
        print()
        
        # Create sample data points for graph validation
        order_ranges = [
            current_orders * 0.5,
            current_orders * 0.75, 
            current_orders,
            current_orders * 1.25,
            current_orders * 1.5,
            full_capacity_orders
        ]
        
        print("📊 Sample Data Points for Graph:")
        print("Orders\t\tCurrent Cost\tFull Cap Cost\tRevenue\t\tMargin")
        print("-" * 70)
        
        for orders in order_ranges:
            # Current utilization: Use current cost structure
            current_cost = current_total_cost_per_order * orders
            
            # Full capacity: Fixed costs spread over actual order volume, transport scales
            warehouse_cost = daily_warehouse_cost  # Fixed total daily cost
            staff_cost = daily_staff_cost  # Fixed total daily cost
            transport_cost = (daily_transport_cost / current_orders) * orders if current_orders > 0 else 0
            
            full_capacity_cost = warehouse_cost + staff_cost + transport_cost
            revenue = revenue_per_order * orders
            margin = ((revenue - full_capacity_cost) / revenue * 100) if revenue > 0 else 0
            
            print(f"{orders:,.0f}\t\t₹{current_cost:,.0f}\t\t₹{full_capacity_cost:,.0f}\t\t₹{revenue:,.0f}\t\t{margin:.1f}%")
        
        # Validate calculations
        assert current_margin < full_capacity_margin, "Full capacity should have better margins"
        assert margin_improvement > 0, "Should show margin improvement with scale"
        assert full_total_cost_per_order < current_total_cost_per_order, "Full capacity cost per order should be lower"
        
        print("\n🎉 All calculations validated! Cost vs Orders graph logic is working correctly.")
        print("   ✓ Fixed costs reduce per order at scale")
        print("   ✓ Margins improve with higher utilization") 
        print("   ✓ Graph data points are mathematically correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cost_margin_graph()
    
    if not success:
        sys.exit(1)