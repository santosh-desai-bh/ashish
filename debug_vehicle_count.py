#!/usr/bin/env python3
"""
Debug script to understand why last mile vehicle count is so high
"""

def debug_last_mile_calculation():
    """Debug the last mile vehicle calculation logic"""
    
    # Simulate the key parameters that are causing high vehicle count
    print("=== DEBUGGING LAST MILE VEHICLE COUNT ===\n")
    
    # From the code analysis, these are the key parameters:
    
    # 1. Big warehouses (main hubs)
    big_warehouse_count = 5  # Minimum 5 hubs as per line 372 in warehouse_logic.py
    big_warehouse_capacity = 500  # Default capacity per hub (line 1790 in analytics.py)
    
    # 2. Feeder warehouses (auxiliaries) 
    max_feeders = 20  # Default max feeders as per line 109 in pincode_warehouse_logic.py
    feeder_warehouse_capacity = 150  # Default capacity per feeder (line 1800 in analytics.py)
    
    print(f"Big Warehouses: {big_warehouse_count} × {big_warehouse_capacity} capacity = {big_warehouse_count * big_warehouse_capacity} total capacity")
    print(f"Feeder Warehouses: {max_feeders} × {feeder_warehouse_capacity} capacity = {max_feeders * feeder_warehouse_capacity} total capacity")
    
    # 3. Total delivery points
    total_delivery_points = big_warehouse_count + max_feeders
    print(f"Total Delivery Points: {total_delivery_points}")
    
    # 4. Calculate total orders (from line 1834 in analytics.py)
    # total_orders = sum([int(point['capacity'] * 0.8) for point in delivery_points])
    total_orders = (big_warehouse_count * big_warehouse_capacity * 0.8) + (max_feeders * feeder_warehouse_capacity * 0.8)
    print(f"Total Orders: {total_orders} (80% of capacity)")
    
    # 5. Package distribution (from line 1825-1831 in analytics.py)
    package_distribution = {
        'Small (<125 ccm)': 0.30,
        'Medium (125-1000 ccm)': 0.25,
        'Large (1000-3375 ccm)': 0.20,
        'XL(3375-10000 ccm)': 0.15,
        'XXL (>10000 ccm)': 0.10
    }
    
    # Calculate XL/XXL vs S/M/L orders
    xl_xxl_percentage = package_distribution['XL(3375-10000 ccm)'] + package_distribution['XXL (>10000 ccm)']
    sml_percentage = 1 - xl_xxl_percentage
    
    xl_xxl_orders = int(total_orders * xl_xxl_percentage)
    sml_orders = int(total_orders * sml_percentage)
    
    print(f"\nPackage Distribution:")
    print(f"XL/XXL Orders: {xl_xxl_orders} ({xl_xxl_percentage*100}%)")
    print(f"S/M/L Orders: {sml_orders} ({sml_percentage*100}%)")
    
    # 6. Vehicle specifications (from line 1761-1778 in analytics.py)
    avg_bike_deliveries = 22  # Average deliveries per bike per day
    avg_auto_deliveries = 27  # Average deliveries per auto per day
    
    print(f"\nVehicle Capacity:")
    print(f"Bike Deliveries per day: {avg_bike_deliveries}")
    print(f"Auto Deliveries per day: {avg_auto_deliveries}")
    
    # 7. Calculate minimum autos needed (from line 1853 in analytics.py)
    # min_autos_for_xl_xxl = max(1, (xl_xxl_orders + avg_auto_deliveries - 1) // avg_auto_deliveries) if xl_xxl_orders > 0 else 0
    min_autos_for_xl_xxl = max(1, (xl_xxl_orders + avg_auto_deliveries - 1) // avg_auto_deliveries) if xl_xxl_orders > 0 else 0
    
    print(f"\nMinimum Autos needed for XL/XXL: {min_autos_for_xl_xxl}")
    
    # 8. Calculate remaining auto capacity (from line 1856 in analytics.py)
    remaining_auto_capacity = (min_autos_for_xl_xxl * avg_auto_deliveries) - xl_xxl_orders
    print(f"Remaining Auto Capacity: {remaining_auto_capacity}")
    
    # 9. Distribute S/M/L packages (from line 1859-1860 in analytics.py)
    sml_on_autos = min(sml_orders, remaining_auto_capacity)
    sml_on_bikes = sml_orders - sml_on_autos
    
    print(f"S/M/L on Autos: {sml_on_autos}")
    print(f"S/M/L on Bikes: {sml_on_bikes}")
    
    # 10. Account for auxiliary staff (from line 1863 in analytics.py)
    aux_staff_bike_capacity = max_feeders * avg_bike_deliveries  # Each aux has 1 staff who can deliver
    print(f"Auxiliary Staff Bike Capacity: {aux_staff_bike_capacity}")
    
    # 11. Calculate bike requirements (from line 1866-1867 in analytics.py)
    remaining_bike_orders = max(0, sml_on_bikes - aux_staff_bike_capacity)
    total_bikes_needed = max(0, (remaining_bike_orders + avg_bike_deliveries - 1) // avg_bike_deliveries) if remaining_bike_orders > 0 else 0
    
    print(f"Remaining Bike Orders: {remaining_bike_orders}")
    print(f"Total Bikes Needed: {total_bikes_needed}")
    
    # 12. Final totals (from line 1868 in analytics.py)
    total_autos_needed = min_autos_for_xl_xxl
    
    print(f"\n=== FINAL VEHICLE COUNT ===")
    print(f"Total Bikes: {total_bikes_needed}")
    print(f"Total Autos: {total_autos_needed}")
    print(f"Total Vehicles: {total_bikes_needed + total_autos_needed}")
    print(f"Total Drivers: {total_bikes_needed + total_autos_needed}")
    
    print(f"\n=== PROBLEM ANALYSIS ===")
    print(f"Expected daily need: 60-70 vehicles")
    print(f"System calculating: {total_bikes_needed + total_autos_needed} vehicles")
    print(f"Difference: {(total_bikes_needed + total_autos_needed) - 65} vehicles too many")
    
    print(f"\n=== ROOT CAUSES ===")
    print(f"1. Too many delivery points: {total_delivery_points} (5 hubs + {max_feeders} feeders)")
    print(f"2. High total capacity assumption: {total_orders} orders/day")
    print(f"3. 80% capacity utilization factor built in")
    print(f"4. Each delivery point treated independently")
    
    print(f"\n=== RECOMMENDED FIXES ===")
    print(f"1. Reduce max_feeders from {max_feeders} to 8-10")
    print(f"2. Reduce feeder capacity from {feeder_warehouse_capacity} to 80-100")
    print(f"3. Use actual order volume instead of 80% of total capacity")
    print(f"4. Adjust utilization factor based on real demand patterns")

if __name__ == "__main__":
    debug_last_mile_calculation()