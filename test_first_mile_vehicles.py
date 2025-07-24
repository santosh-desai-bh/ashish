import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add the current directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class TestFirstMileVehicleCalculations(unittest.TestCase):
    """Test suite for First Mile vehicle-wise capacity calculations"""
    
    def setUp(self):
        """Set up test data"""
        # Vehicle specifications from the code
        self.bike_capacity = 15
        self.auto_capacity = 35
        self.minitruck_capacity = 80
        
        self.bike_trips_per_day = 8
        self.auto_trips_per_day = 6
        self.truck_trips_per_day = 4
        
        # Sample pickup hub data
        self.pickup_hubs_small = pd.DataFrame({
            'pickup': ['Hub1', 'Hub2'],
            'pickup_lat': [12.97, 12.98],
            'pickup_long': [77.59, 77.60],
            'order_count': [30, 40]  # Total 70 orders, avg 35 per hub
        })
        
        self.pickup_hubs_medium = pd.DataFrame({
            'pickup': ['Hub1', 'Hub2', 'Hub3'],
            'pickup_lat': [12.97, 12.98, 12.99],
            'pickup_long': [77.59, 77.60, 77.61],
            'order_count': [80, 60, 70]  # Total 210 orders, avg 70 per hub
        })
        
        self.pickup_hubs_large = pd.DataFrame({
            'pickup': ['Hub1', 'Hub2'],
            'pickup_lat': [12.97, 12.98],
            'pickup_long': [77.59, 77.60],
            'order_count': [150, 120]  # Total 270 orders, avg 135 per hub
        })

    def test_vehicle_mix_small_locations(self):
        """Test vehicle mix for small pickup locations (≤50 orders avg)"""
        total_pickup_locations = len(self.pickup_hubs_small)
        current_orders = self.pickup_hubs_small['order_count'].sum()
        avg_orders_per_pickup = current_orders / total_pickup_locations
        
        # Should be 35 avg orders per pickup (small category)
        self.assertLessEqual(avg_orders_per_pickup, 50)
        
        # Expected vehicle mix for small locations: 2 bikes, 1 auto, 0 trucks
        expected_bikes_per_pickup = 2
        expected_autos_per_pickup = 1
        expected_trucks_per_pickup = 0
        
        total_bikes = expected_bikes_per_pickup * total_pickup_locations
        total_autos = expected_autos_per_pickup * total_pickup_locations
        total_trucks = expected_trucks_per_pickup * total_pickup_locations
        
        # Calculate capacities
        bike_daily_capacity = total_bikes * self.bike_trips_per_day * self.bike_capacity
        auto_daily_capacity = total_autos * self.auto_trips_per_day * self.auto_capacity
        truck_daily_capacity = total_trucks * self.truck_trips_per_day * self.minitruck_capacity
        
        self.assertEqual(total_bikes, 4)  # 2 hubs * 2 bikes each
        self.assertEqual(total_autos, 2)  # 2 hubs * 1 auto each
        self.assertEqual(total_trucks, 0) # 2 hubs * 0 trucks each
        
        # Verify capacities
        self.assertEqual(bike_daily_capacity, 4 * 8 * 15)  # 480
        self.assertEqual(auto_daily_capacity, 2 * 6 * 35)  # 420
        self.assertEqual(truck_daily_capacity, 0)          # 0
        
        total_capacity = bike_daily_capacity + auto_daily_capacity + truck_daily_capacity
        self.assertEqual(total_capacity, 900)
        
        # Should have more than enough capacity for 70 orders
        self.assertGreater(total_capacity, current_orders)

    def test_vehicle_mix_medium_locations(self):
        """Test vehicle mix for medium pickup locations (51-100 orders avg)"""
        total_pickup_locations = len(self.pickup_hubs_medium)
        current_orders = self.pickup_hubs_medium['order_count'].sum()
        avg_orders_per_pickup = current_orders / total_pickup_locations
        
        # Should be 70 avg orders per pickup (medium category)
        self.assertGreater(avg_orders_per_pickup, 50)
        self.assertLessEqual(avg_orders_per_pickup, 100)
        
        # Expected vehicle mix for medium locations: 2 bikes, 2 autos, 1 truck
        expected_bikes_per_pickup = 2
        expected_autos_per_pickup = 2
        expected_trucks_per_pickup = 1
        
        total_bikes = expected_bikes_per_pickup * total_pickup_locations
        total_autos = expected_autos_per_pickup * total_pickup_locations
        total_trucks = expected_trucks_per_pickup * total_pickup_locations
        
        self.assertEqual(total_bikes, 6)  # 3 hubs * 2 bikes each
        self.assertEqual(total_autos, 6)  # 3 hubs * 2 autos each
        self.assertEqual(total_trucks, 3) # 3 hubs * 1 truck each

    def test_vehicle_mix_large_locations(self):
        """Test vehicle mix for large pickup locations (>100 orders avg)"""
        total_pickup_locations = len(self.pickup_hubs_large)
        current_orders = self.pickup_hubs_large['order_count'].sum()
        avg_orders_per_pickup = current_orders / total_pickup_locations
        
        # Should be 135 avg orders per pickup (large category)
        self.assertGreater(avg_orders_per_pickup, 100)
        
        # Expected vehicle mix for large locations: 1 bike, 2 autos, 2 trucks
        expected_bikes_per_pickup = 1
        expected_autos_per_pickup = 2
        expected_trucks_per_pickup = 2
        
        total_bikes = expected_bikes_per_pickup * total_pickup_locations
        total_autos = expected_autos_per_pickup * total_pickup_locations
        total_trucks = expected_trucks_per_pickup * total_pickup_locations
        
        self.assertEqual(total_bikes, 2)  # 2 hubs * 1 bike each
        self.assertEqual(total_autos, 4)  # 2 hubs * 2 autos each
        self.assertEqual(total_trucks, 4) # 2 hubs * 2 trucks each

    def test_daily_capacity_calculations(self):
        """Test daily capacity calculations for each vehicle type"""
        # Test with known fleet sizes
        test_bikes = 10
        test_autos = 5
        test_trucks = 3
        
        bike_daily_capacity = test_bikes * self.bike_trips_per_day * self.bike_capacity
        auto_daily_capacity = test_autos * self.auto_trips_per_day * self.auto_capacity
        truck_daily_capacity = test_trucks * self.truck_trips_per_day * self.minitruck_capacity
        
        # Expected calculations
        self.assertEqual(bike_daily_capacity, 10 * 8 * 15)  # 1200
        self.assertEqual(auto_daily_capacity, 5 * 6 * 35)   # 1050
        self.assertEqual(truck_daily_capacity, 3 * 4 * 80)  # 960
        
        total_capacity = bike_daily_capacity + auto_daily_capacity + truck_daily_capacity
        self.assertEqual(total_capacity, 3210)

    def test_trips_per_day_calculation(self):
        """Test total trips per day calculation"""
        test_bikes = 4
        test_autos = 3
        test_trucks = 2
        
        bike_trips = test_bikes * self.bike_trips_per_day
        auto_trips = test_autos * self.auto_trips_per_day
        truck_trips = test_trucks * self.truck_trips_per_day
        
        total_trips = bike_trips + auto_trips + truck_trips
        
        self.assertEqual(bike_trips, 32)  # 4 * 8
        self.assertEqual(auto_trips, 18)  # 3 * 6
        self.assertEqual(truck_trips, 8)  # 2 * 4
        self.assertEqual(total_trips, 58)

    def test_vehicle_efficiency_comparison(self):
        """Test that vehicles are ranked correctly by efficiency"""
        # Calculate packages per trip
        packages_per_trip = {
            'bike': self.bike_capacity,
            'auto': self.auto_capacity,
            'truck': self.minitruck_capacity
        }
        
        # Calculate daily capacity per vehicle
        daily_capacity_per_vehicle = {
            'bike': self.bike_trips_per_day * self.bike_capacity,
            'auto': self.auto_trips_per_day * self.auto_capacity,
            'truck': self.truck_trips_per_day * self.minitruck_capacity
        }
        
        # Verify capacity ordering
        self.assertLess(packages_per_trip['bike'], packages_per_trip['auto'])
        self.assertLess(packages_per_trip['auto'], packages_per_trip['truck'])
        
        # Daily capacity comparison
        self.assertEqual(daily_capacity_per_vehicle['bike'], 8 * 15)  # 120
        self.assertEqual(daily_capacity_per_vehicle['auto'], 6 * 35)  # 210
        self.assertEqual(daily_capacity_per_vehicle['truck'], 4 * 80) # 320
        
        # Trucks should have highest daily capacity per vehicle
        self.assertGreater(daily_capacity_per_vehicle['truck'], daily_capacity_per_vehicle['auto'])
        self.assertGreater(daily_capacity_per_vehicle['auto'], daily_capacity_per_vehicle['bike'])

    def test_capacity_utilization_percentages(self):
        """Test capacity utilization percentage calculations"""
        # Sample fleet
        bike_daily_capacity = 1200
        auto_daily_capacity = 1050
        truck_daily_capacity = 960
        total_capacity = bike_daily_capacity + auto_daily_capacity + truck_daily_capacity
        
        # Calculate percentages
        bike_util = (bike_daily_capacity / total_capacity * 100)
        auto_util = (auto_daily_capacity / total_capacity * 100)
        truck_util = (truck_daily_capacity / total_capacity * 100)
        
        # Verify percentages add up to 100
        self.assertAlmostEqual(bike_util + auto_util + truck_util, 100.0, places=1)
        
        # Verify individual percentages
        self.assertAlmostEqual(bike_util, 37.4, places=1)
        self.assertAlmostEqual(auto_util, 32.7, places=1)
        self.assertAlmostEqual(truck_util, 29.9, places=1)

    def test_vehicle_mix_boundary_conditions(self):
        """Test vehicle mix at boundary conditions"""
        # Test exactly 50 orders (boundary between small and medium)
        test_cases = [
            (50, {'bikes': 2, 'autos': 1, 'minitrucks': 0}),  # Should be small
            (51, {'bikes': 2, 'autos': 2, 'minitrucks': 1}),  # Should be medium
            (100, {'bikes': 2, 'autos': 2, 'minitrucks': 1}), # Should be medium
            (101, {'bikes': 1, 'autos': 2, 'minitrucks': 2}), # Should be large
        ]
        
        for avg_orders, expected_mix in test_cases:
            with self.subTest(avg_orders=avg_orders):
                if avg_orders <= 50:
                    vehicles_per_pickup = {'bikes': 2, 'autos': 1, 'minitrucks': 0}
                elif avg_orders <= 100:
                    vehicles_per_pickup = {'bikes': 2, 'autos': 2, 'minitrucks': 1}
                else:
                    vehicles_per_pickup = {'bikes': 1, 'autos': 2, 'minitrucks': 2}
                
                self.assertEqual(vehicles_per_pickup, expected_mix)


if __name__ == '__main__':
    # Run with verbose output to see test progress
    unittest.main(verbosity=2, buffer=True)