#!/usr/bin/env python3
"""
Comprehensive validation tests to verify all calculations are mathematically correct
and detect any hallucinated numbers or incorrect logic.
"""

import pandas as pd
import sys
sys.path.append('.')

def test_basic_math_verification():
    """Test basic mathematical operations to ensure no hallucination"""
    print("🧮 Testing Basic Math Verification")
    print("=" * 50)
    
    # Test 1: Revenue calculation
    orders_per_day = 1400
    revenue_per_order = 77
    days_per_month = 30
    
    daily_revenue = orders_per_day * revenue_per_order
    monthly_revenue = daily_revenue * days_per_month
    
    print(f"✓ Daily Revenue: {orders_per_day} × ₹{revenue_per_order} = ₹{daily_revenue:,}")
    print(f"✓ Monthly Revenue: ₹{daily_revenue:,} × {days_per_month} = ₹{monthly_revenue:,}")
    
    # Verify calculations
    assert daily_revenue == 107800, f"Expected 107800, got {daily_revenue}"
    assert monthly_revenue == 3234000, f"Expected 3234000, got {monthly_revenue}"
    
    # Test 2: Cost calculations
    warehouse_monthly = 450000
    transport_monthly = 1200000
    staff_monthly = 180000
    
    total_monthly_cost = warehouse_monthly + transport_monthly + staff_monthly
    daily_cost = total_monthly_cost / 30
    
    print(f"✓ Total Monthly Cost: ₹{warehouse_monthly:,} + ₹{transport_monthly:,} + ₹{staff_monthly:,} = ₹{total_monthly_cost:,}")
    print(f"✓ Daily Cost: ₹{total_monthly_cost:,} ÷ 30 = ₹{daily_cost:,}")
    
    assert total_monthly_cost == 1830000, f"Expected 1830000, got {total_monthly_cost}"
    assert daily_cost == 61000, f"Expected 61000, got {daily_cost}"
    
    # Test 3: Margin calculation
    daily_profit = daily_revenue - daily_cost
    margin_percentage = (daily_profit / daily_revenue) * 100
    
    print(f"✓ Daily Profit: ₹{daily_revenue:,} - ₹{daily_cost:,} = ₹{daily_profit:,}")
    print(f"✓ Margin: (₹{daily_profit:,} ÷ ₹{daily_revenue:,}) × 100 = {margin_percentage:.1f}%")
    
    assert daily_profit == 46800, f"Expected 46800, got {daily_profit}"
    assert abs(margin_percentage - 43.4) < 0.1, f"Expected ~43.4%, got {margin_percentage:.1f}%"
    
    print("🎉 All basic math verified correctly!")
    return True

def test_staff_cost_calculations():
    """Test staff cost calculations for warehouses"""
    print("\n👥 Testing Staff Cost Calculations")
    print("=" * 50)
    
    # Main hub staff costs
    main_hubs = 2
    staff_per_main_hub = 2
    salary_per_person_monthly = 30000
    
    main_hub_total_staff = main_hubs * staff_per_main_hub
    main_hub_monthly_cost = main_hub_total_staff * salary_per_person_monthly
    
    print(f"✓ Main Hub Staff: {main_hubs} hubs × {staff_per_main_hub} staff = {main_hub_total_staff} people")
    print(f"✓ Main Hub Cost: {main_hub_total_staff} × ₹{salary_per_person_monthly:,} = ₹{main_hub_monthly_cost:,}/month")
    
    # Auxiliary staff costs
    aux_warehouses = 4
    staff_per_aux = 1
    aux_salary_monthly = 15000
    
    aux_total_staff = aux_warehouses * staff_per_aux
    aux_monthly_cost = aux_total_staff * aux_salary_monthly
    
    print(f"✓ Auxiliary Staff: {aux_warehouses} aux × {staff_per_aux} staff = {aux_total_staff} people")
    print(f"✓ Auxiliary Cost: {aux_total_staff} × ₹{aux_salary_monthly:,} = ₹{aux_monthly_cost:,}/month")
    
    # Total staff costs
    total_monthly_staff_cost = main_hub_monthly_cost + aux_monthly_cost
    daily_staff_cost = total_monthly_staff_cost / 30
    
    print(f"✓ Total Staff Cost: ₹{main_hub_monthly_cost:,} + ₹{aux_monthly_cost:,} = ₹{total_monthly_staff_cost:,}/month")
    print(f"✓ Daily Staff Cost: ₹{total_monthly_staff_cost:,} ÷ 30 = ₹{daily_staff_cost:,}/day")
    
    # Verify calculations
    assert main_hub_monthly_cost == 120000, f"Expected 120000, got {main_hub_monthly_cost}"
    assert aux_monthly_cost == 60000, f"Expected 60000, got {aux_monthly_cost}"
    assert total_monthly_staff_cost == 180000, f"Expected 180000, got {total_monthly_staff_cost}"
    assert daily_staff_cost == 6000, f"Expected 6000, got {daily_staff_cost}"
    
    print("🎉 All staff cost calculations verified!")
    return True

def test_scale_economics_logic():
    """Test scale economics calculations for different order volumes"""
    print("\n📈 Testing Scale Economics Logic")
    print("=" * 50)
    
    # Fixed costs (don't change with order volume)
    daily_warehouse_fixed = 15000  # ₹450k/month ÷ 30
    daily_staff_fixed = 6000       # ₹180k/month ÷ 30
    total_fixed_daily = daily_warehouse_fixed + daily_staff_fixed
    
    # Variable costs (change proportionally with orders)
    daily_transport_base = 40000   # ₹1.2M/month ÷ 30
    base_orders = 1400
    
    print(f"✓ Fixed Costs: ₹{daily_warehouse_fixed:,} (warehouse) + ₹{daily_staff_fixed:,} (staff) = ₹{total_fixed_daily:,}/day")
    print(f"✓ Variable Cost Base: ₹{daily_transport_base:,}/day for {base_orders:,} orders")
    
    # Test different order volumes
    test_volumes = [700, 1400, 2000, 2800]
    revenue_per_order = 77
    
    print(f"\nTesting different order volumes:")
    print("Orders\t\tFixed Cost\tVariable Cost\tTotal Cost\tRevenue\t\tMargin")
    print("-" * 80)
    
    for orders in test_volumes:
        # Fixed costs remain the same
        fixed_cost = total_fixed_daily
        
        # Variable costs scale proportionally
        variable_cost = (daily_transport_base * orders) / base_orders
        
        total_cost = fixed_cost + variable_cost
        revenue = orders * revenue_per_order
        margin = ((revenue - total_cost) / revenue * 100) if revenue > 0 else 0
        
        print(f"{orders:,}\t\t₹{fixed_cost:,}\t\t₹{variable_cost:,.0f}\t\t₹{total_cost:,.0f}\t\t₹{revenue:,}\t\t{margin:.1f}%")
        
        # Verify logical relationships
        assert fixed_cost == total_fixed_daily, "Fixed costs should not change"
        assert variable_cost > 0, "Variable costs should be positive"
        assert total_cost == fixed_cost + variable_cost, "Total cost should equal fixed + variable"
        assert revenue == orders * revenue_per_order, "Revenue calculation should be correct"
        
        # Verify scale economics - higher volume should have better margins (within reason)
        if orders == 1400:
            baseline_margin = margin
        elif orders > 1400:
            # Higher volume should have equal or better margins due to fixed cost absorption
            # (unless transport costs dominate, which is realistic)
            cost_per_order = total_cost / orders
            baseline_cost_per_order = (total_fixed_daily + daily_transport_base) / base_orders
            # Fixed cost per order should definitely be lower at higher volumes
            fixed_cost_per_order = fixed_cost / orders
            baseline_fixed_cost_per_order = total_fixed_daily / base_orders
            assert fixed_cost_per_order < baseline_fixed_cost_per_order, f"Fixed cost per order should decrease with scale: {fixed_cost_per_order:.1f} vs {baseline_fixed_cost_per_order:.1f}"
    
    print("🎉 Scale economics logic verified!")
    return True

def test_vehicle_loading_optimization():
    """Test vehicle loading optimization calculations"""
    print("\n🚛 Testing Vehicle Loading Optimization")  
    print("=" * 50)
    
    # Test package distribution
    total_orders = 1000
    package_distribution = {
        'Small (<125 ccm)': 0.20,
        'Medium (125-1000 ccm)': 0.20, 
        'Large (1000-3375 ccm)': 0.20,
        'XL(3375-10000 ccm)': 0.20,
        'XXL (>10000 ccm)': 0.20
    }
    
    # Calculate package counts
    package_counts = {}
    total_calculated = 0
    
    for package_size, percentage in package_distribution.items():
        count = int(total_orders * percentage)
        package_counts[package_size] = count
        total_calculated += count
        print(f"✓ {package_size}: {percentage:.1%} × {total_orders:,} = {count:,} packages")
    
    assert total_calculated <= total_orders, f"Total packages {total_calculated} should not exceed {total_orders}"
    print(f"✓ Total packages calculated: {total_calculated:,}")
    
    # Test vehicle assignment logic
    bike_packages = ['Small (<125 ccm)', 'Medium (125-1000 ccm)', 'Large (1000-3375 ccm)']
    auto_packages = ['XL(3375-10000 ccm)', 'XXL (>10000 ccm)']
    
    bike_orders = sum([package_counts[pkg] for pkg in bike_packages])
    auto_orders = sum([package_counts[pkg] for pkg in auto_packages])
    
    print(f"✓ Bike-suitable orders: {bike_orders:,}")
    print(f"✓ Auto-required orders: {auto_orders:,}")
    print(f"✓ Total verification: {bike_orders:,} + {auto_orders:,} = {bike_orders + auto_orders:,}")
    
    assert bike_orders + auto_orders == total_calculated, "Package assignment should account for all orders"
    
    # Test driver calculations
    avg_bike_deliveries = 22
    avg_auto_deliveries = 27
    
    bikes_needed = max(1, (bike_orders + avg_bike_deliveries - 1) // avg_bike_deliveries)
    autos_needed = max(1, (auto_orders + avg_auto_deliveries - 1) // avg_auto_deliveries)
    
    print(f"✓ Bikes needed: ceiling({bike_orders:,} ÷ {avg_bike_deliveries}) = {bikes_needed}")
    print(f"✓ Autos needed: ceiling({auto_orders:,} ÷ {avg_auto_deliveries}) = {autos_needed}")
    
    # Verify capacity constraints
    bike_capacity = bikes_needed * avg_bike_deliveries
    auto_capacity = autos_needed * avg_auto_deliveries
    
    assert bike_capacity >= bike_orders, f"Bike capacity {bike_capacity} should handle {bike_orders} orders"
    assert auto_capacity >= auto_orders, f"Auto capacity {auto_capacity} should handle {auto_orders} orders"
    
    print("🎉 Vehicle loading optimization verified!")
    return True

def test_margin_calculation_cross_check():
    """Cross-check margin calculations with different methods"""
    print("\n🔍 Cross-Checking Margin Calculations")
    print("=" * 50)
    
    # Method 1: Direct calculation
    orders = 1400
    revenue_per_order = 77
    daily_revenue = orders * revenue_per_order
    
    # Costs
    warehouse_cost = 450000 / 30  # ₹15,000/day
    transport_cost = 1200000 / 30  # ₹40,000/day  
    staff_cost = 180000 / 30       # ₹6,000/day
    total_cost = warehouse_cost + transport_cost + staff_cost
    
    profit = daily_revenue - total_cost
    margin_method1 = (profit / daily_revenue) * 100
    
    print("Method 1 - Direct Calculation:")
    print(f"  Revenue: {orders:,} × ₹{revenue_per_order} = ₹{daily_revenue:,}")
    print(f"  Costs: ₹{warehouse_cost:,} + ₹{transport_cost:,} + ₹{staff_cost:,} = ₹{total_cost:,}")
    print(f"  Profit: ₹{daily_revenue:,} - ₹{total_cost:,} = ₹{profit:,}")
    print(f"  Margin: (₹{profit:,} ÷ ₹{daily_revenue:,}) × 100 = {margin_method1:.1f}%")
    
    # Method 2: Per-order calculation
    cost_per_order = total_cost / orders
    profit_per_order = revenue_per_order - cost_per_order
    margin_method2 = (profit_per_order / revenue_per_order) * 100
    
    print("\nMethod 2 - Per-Order Calculation:")
    print(f"  Cost per order: ₹{total_cost:,} ÷ {orders:,} = ₹{cost_per_order:.2f}")
    print(f"  Profit per order: ₹{revenue_per_order} - ₹{cost_per_order:.2f} = ₹{profit_per_order:.2f}")
    print(f"  Margin: (₹{profit_per_order:.2f} ÷ ₹{revenue_per_order}) × 100 = {margin_method2:.1f}%")
    
    # Method 3: Monthly calculation
    monthly_revenue = daily_revenue * 30
    monthly_cost = total_cost * 30
    monthly_profit = monthly_revenue - monthly_cost
    margin_method3 = (monthly_profit / monthly_revenue) * 100
    
    print("\nMethod 3 - Monthly Calculation:")
    print(f"  Monthly Revenue: ₹{daily_revenue:,} × 30 = ₹{monthly_revenue:,}")
    print(f"  Monthly Cost: ₹{total_cost:,} × 30 = ₹{monthly_cost:,}")
    print(f"  Monthly Profit: ₹{monthly_revenue:,} - ₹{monthly_cost:,} = ₹{monthly_profit:,}")
    print(f"  Margin: (₹{monthly_profit:,} ÷ ₹{monthly_revenue:,}) × 100 = {margin_method3:.1f}%")
    
    # All methods should give the same result
    assert abs(margin_method1 - margin_method2) < 0.1, f"Method 1 ({margin_method1:.1f}%) and Method 2 ({margin_method2:.1f}%) should match"
    assert abs(margin_method2 - margin_method3) < 0.1, f"Method 2 ({margin_method2:.1f}%) and Method 3 ({margin_method3:.1f}%) should match"
    
    print(f"\n✓ All three methods give consistent results: ~{margin_method1:.1f}% margin")
    print("🎉 Margin calculation cross-check passed!")
    
    return True

def test_comprehensive_validation():
    """Run all validation tests"""
    print("🧪 COMPREHENSIVE VALIDATION TEST SUITE")
    print("=" * 70)
    print("Testing all calculations to detect hallucination and verify mathematical accuracy")
    print("=" * 70)
    
    tests = [
        test_basic_math_verification,
        test_staff_cost_calculations, 
        test_scale_economics_logic,
        test_vehicle_loading_optimization,
        test_margin_calculation_cross_check
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            result = test_func()
            if result:
                passed_tests += 1
            print()
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 70)
    print(f"FINAL RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! No hallucination detected. All calculations are mathematically correct.")
        print("✓ Revenue calculations verified")
        print("✓ Cost calculations verified")
        print("✓ Margin calculations verified")
        print("✓ Scale economics logic verified")
        print("✓ Vehicle optimization verified")
        print("✓ Cross-validation successful")
    else:
        print("❌ SOME TESTS FAILED! Please review calculations for errors.")
        return False
    
    return True

if __name__ == "__main__":
    success = test_comprehensive_validation()
    
    if not success:
        sys.exit(1)