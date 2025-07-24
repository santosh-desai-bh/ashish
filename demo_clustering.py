#!/usr/bin/env python3
"""
Demo script showing the First Mile pickup clustering strategy in action
Works without geopy/sklearn dependencies using built-in fallbacks
"""

import pandas as pd
import sys
sys.path.append('.')

from analytics import create_pickup_clusters, assign_vehicles_to_clusters, calculate_fleet_summary

def main():
    print("🚚 First Mile Pickup Clustering Demo")
    print("=" * 50)
    
    # Vehicle specifications
    vehicle_specs = {
        'bike': {'min_capacity': 30, 'max_capacity': 50, 'daily_cost': 700},
        'auto': {'min_capacity': 50, 'max_capacity': 70, 'daily_cost': 900},
        'minitruck': {'min_capacity': 100, 'max_capacity': 200, 'daily_cost': 1400},
        'large_truck': {'min_capacity': 300, 'max_capacity': 500, 'daily_cost': 2600}
    }
    
    # Sample pickup hubs with realistic data
    pickup_hubs = pd.DataFrame({
        'pickup': ['Herbalife', 'Westside', 'Tata Cliq', 'Myntra', 'Flipkart', 'Zomato', 'Swiggy'],
        'pickup_lat': [12.9716, 12.9720, 12.9725, 12.9800, 12.9810, 12.9815, 13.0000],
        'pickup_long': [77.5946, 77.5950, 77.5955, 77.6000, 77.6005, 77.6010, 77.6500],
        'order_count': [500, 30, 25, 80, 150, 40, 35]
    })
    
    print("\n📍 Original Pickup Locations:")
    for _, hub in pickup_hubs.iterrows():
        print(f"  • {hub['pickup']}: {hub['order_count']} orders")
    
    total_original_orders = pickup_hubs['order_count'].sum()
    print(f"\nTotal: {len(pickup_hubs)} locations, {total_original_orders} orders")
    
    # Step 1: Create clusters
    print("\n🎯 Step 1: Creating proximity-based clusters...")
    clusters = create_pickup_clusters(pickup_hubs, vehicle_specs)
    
    print(f"\n📊 Clustering Results: {len(pickup_hubs)} locations → {len(clusters)} clusters")
    
    for i, cluster in enumerate(clusters, 1):
        main_hub = cluster['main_hub']['pickup']
        additional_hubs = [hub['pickup'] for hub in cluster['additional_hubs']]
        
        if additional_hubs:
            print(f"  Cluster {i}: {main_hub} + {', '.join(additional_hubs)} = {cluster['total_orders']} orders")
        else:
            print(f"  Cluster {i}: {main_hub} (standalone) = {cluster['total_orders']} orders")
    
    # Step 2: Assign vehicles
    print("\n🚛 Step 2: Assigning optimal vehicles...")
    assignments = assign_vehicles_to_clusters(clusters, vehicle_specs)
    
    for i, assignment in enumerate(assignments, 1):
        cluster = assignment['cluster']
        main_hub = cluster['main_hub']['pickup']
        vehicle_type = assignment['vehicle_type']
        cost = assignment['daily_cost']
        utilization = assignment['utilization']
        
        print(f"  Cluster {i} ({main_hub}): {vehicle_type.replace('_', ' ').title()} - ₹{cost}/day ({utilization:.1f}% utilization)")
    
    # Step 3: Calculate fleet summary
    print("\n💰 Step 3: Fleet summary and cost analysis...")
    fleet_summary = calculate_fleet_summary(assignments)
    
    print(f"\nFleet Composition:")
    for vehicle_type in ['bikes', 'autos', 'minitrucks', 'large_trucks']:
        count = fleet_summary[vehicle_type]['count']
        capacity = fleet_summary[vehicle_type]['capacity']
        cost = fleet_summary[vehicle_type]['cost']
        
        if count > 0:
            vehicle_name = vehicle_type.replace('_', ' ').title()
            print(f"  • {count} {vehicle_name}: {capacity} capacity, ₹{cost}/day")
    
    print(f"\nTotal Daily Cost: ₹{fleet_summary['total_daily_cost']:,}")
    print(f"Total Capacity: {fleet_summary['total_capacity']} orders")
    
    # Cost comparison
    naive_cost = len(pickup_hubs) * vehicle_specs['auto']['daily_cost']  # 1 auto per location
    optimized_cost = fleet_summary['total_daily_cost']
    savings = naive_cost - optimized_cost
    
    print(f"\n📈 Cost Efficiency Analysis:")
    print(f"  Naive approach (1 auto/location): ₹{naive_cost:,}/day")
    print(f"  Optimized clustering approach: ₹{optimized_cost:,}/day")
    print(f"  Daily savings: ₹{savings:,} ({savings/naive_cost*100:.1f}% saved)")
    
    print(f"\n✅ Optimization complete!")
    print(f"   {len(pickup_hubs)} locations → {len(clusters)} clusters")
    print(f"   {sum(fleet_summary[v]['count'] for v in ['bikes', 'autos', 'minitrucks', 'large_trucks'])} vehicles total")
    print(f"   ₹{savings:,} daily savings")

if __name__ == "__main__":
    main()