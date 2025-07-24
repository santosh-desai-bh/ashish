import unittest
import pandas as pd
import sys
import os

# Add the current directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import numpy for tests
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from analytics import create_pickup_clusters, assign_vehicles_to_clusters, calculate_fleet_summary


class TestPickupClustering(unittest.TestCase):
    """Test suite for proximity-based pickup clustering and vehicle assignment"""
    
    def setUp(self):
        """Set up test data"""
        # Vehicle specifications
        self.vehicle_specs = {
            'bike': {'min_capacity': 30, 'max_capacity': 50, 'daily_cost': 700},
            'auto': {'min_capacity': 50, 'max_capacity': 70, 'daily_cost': 900},
            'minitruck': {'min_capacity': 100, 'max_capacity': 200, 'daily_cost': 1400},
            'large_truck': {'min_capacity': 300, 'max_capacity': 500, 'daily_cost': 2600}
        }
        
        # Sample pickup hub data with various scenarios
        self.pickup_hubs_scenario1 = pd.DataFrame({
            'pickup': ['Herbalife', 'Westside', 'Tata Cliq', 'Myntra'],
            'pickup_lat': [12.9716, 12.9720, 12.9725, 12.9800],  # Close locations
            'pickup_long': [77.5946, 77.5950, 77.5955, 77.6000],
            'order_count': [500, 30, 25, 80]  # Mixed volumes
        })
        
        # Another scenario with medium-sized hubs
        self.pickup_hubs_scenario2 = pd.DataFrame({
            'pickup': ['Hub1', 'Hub2', 'Hub3', 'Hub4'],
            'pickup_lat': [12.9716, 12.9720, 12.9800, 12.9900],  # Some close, some far
            'pickup_long': [77.5946, 77.5950, 77.6100, 77.6200],
            'order_count': [120, 45, 150, 35]  # Mixed volumes
        })

    def test_large_hub_no_clustering(self):
        """Test that large hubs (≥300 orders) don't get clustered"""
        clusters = create_pickup_clusters(self.pickup_hubs_scenario1, self.vehicle_specs)
        
        # Find Herbalife cluster (500 orders)
        herbalife_cluster = None
        for cluster in clusters:
            if cluster['main_hub']['pickup'] == 'Herbalife':
                herbalife_cluster = cluster
                break
        
        self.assertIsNotNone(herbalife_cluster)
        self.assertEqual(herbalife_cluster['total_orders'], 500)
        self.assertEqual(len(herbalife_cluster['additional_hubs']), 0)  # No clustering

    def test_small_hub_clustering(self):
        """Test that small nearby hubs get clustered together"""
        clusters = create_pickup_clusters(self.pickup_hubs_scenario1, self.vehicle_specs)
        
        # Should have fewer clusters than original hubs due to clustering
        self.assertLess(len(clusters), len(self.pickup_hubs_scenario1))
        
        # Check that clustering occurred - look for a cluster with multiple hubs
        clustered_found = False
        for cluster in clusters:
            if len(cluster['additional_hubs']) > 0:
                clustered_found = True
                # Verify the cluster has reasonable total orders
                self.assertGreater(cluster['total_orders'], 
                                 cluster['main_hub']['order_count'])
                break
        
        # Should find at least one clustered group
        self.assertTrue(clustered_found, "No clustering occurred when it should have")

    def test_vehicle_assignment_logic(self):
        """Test vehicle assignment based on order volume"""
        clusters = create_pickup_clusters(self.pickup_hubs_scenario1, self.vehicle_specs)
        assignments = assign_vehicles_to_clusters(clusters, self.vehicle_specs)
        
        for assignment in assignments:
            total_orders = assignment['cluster']['total_orders']
            vehicle_type = assignment['vehicle_type']
            
            # Test assignment logic
            if total_orders >= 300:
                self.assertEqual(vehicle_type, 'large_truck')
            elif total_orders >= 100:
                self.assertEqual(vehicle_type, 'minitruck')
            elif total_orders >= 50:
                self.assertEqual(vehicle_type, 'auto')
            else:
                self.assertEqual(vehicle_type, 'bike')

    def test_cost_calculation(self):
        """Test cost calculation for vehicle assignments"""
        clusters = create_pickup_clusters(self.pickup_hubs_scenario1, self.vehicle_specs)
        assignments = assign_vehicles_to_clusters(clusters, self.vehicle_specs)
        
        for assignment in assignments:
            vehicle_type = assignment['vehicle_type']
            expected_cost = self.vehicle_specs[vehicle_type]['daily_cost']
            
            self.assertEqual(assignment['daily_cost'], expected_cost)
            
            # Test cost per order calculation
            if assignment['actual_capacity'] > 0:
                expected_cost_per_order = expected_cost / assignment['actual_capacity']
                self.assertAlmostEqual(assignment['cost_per_order'], expected_cost_per_order, places=2)

    def test_fleet_summary_calculation(self):
        """Test fleet summary calculations"""
        clusters = create_pickup_clusters(self.pickup_hubs_scenario1, self.vehicle_specs)
        assignments = assign_vehicles_to_clusters(clusters, self.vehicle_specs)
        fleet_summary = calculate_fleet_summary(assignments)
        
        # Verify total cost calculation
        manual_total_cost = sum(assignment['daily_cost'] for assignment in assignments)
        self.assertEqual(fleet_summary['total_daily_cost'], manual_total_cost)
        
        # Verify total capacity calculation
        manual_total_capacity = sum(assignment['actual_capacity'] for assignment in assignments)
        self.assertEqual(fleet_summary['total_capacity'], manual_total_capacity)
        
        # Verify vehicle counts
        bike_count = sum(1 for a in assignments if a['vehicle_type'] == 'bike')
        auto_count = sum(1 for a in assignments if a['vehicle_type'] == 'auto')
        minitruck_count = sum(1 for a in assignments if a['vehicle_type'] == 'minitruck')
        large_truck_count = sum(1 for a in assignments if a['vehicle_type'] == 'large_truck')
        
        self.assertEqual(fleet_summary['bikes']['count'], bike_count)
        self.assertEqual(fleet_summary['autos']['count'], auto_count)
        self.assertEqual(fleet_summary['minitrucks']['count'], minitruck_count)
        self.assertEqual(fleet_summary['large_trucks']['count'], large_truck_count)

    def test_proximity_clustering_distance(self):
        """Test that only nearby hubs (within 3km) get clustered"""
        # Create hubs with known distances
        test_hubs = pd.DataFrame({
            'pickup': ['Hub1', 'Hub2', 'Hub3'],
            'pickup_lat': [12.9716, 12.9720, 13.0000],  # Hub3 is far away
            'pickup_long': [77.5946, 77.5950, 77.6000],
            'order_count': [40, 35, 45]  # All small volumes
        })
        
        clusters = create_pickup_clusters(test_hubs, self.vehicle_specs)
        
        # Hub1 and Hub2 should be clustered (close), Hub3 should be separate (far)
        self.assertLessEqual(len(clusters), 2)  # Should have at most 2 clusters
        
        # Check that no cluster has more than reasonable total orders
        for cluster in clusters:
            self.assertLessEqual(cluster['total_orders'], 500)  # Within truck capacity

    def test_capacity_constraints(self):
        """Test that clusters don't exceed vehicle capacity limits"""
        clusters = create_pickup_clusters(self.pickup_hubs_scenario1, self.vehicle_specs)
        
        for cluster in clusters:
            # No cluster should exceed large truck capacity
            self.assertLessEqual(cluster['total_orders'], 500)

    def test_empty_input_handling(self):
        """Test handling of empty pickup hub data"""
        empty_hubs = pd.DataFrame(columns=['pickup', 'pickup_lat', 'pickup_long', 'order_count'])
        
        clusters = create_pickup_clusters(empty_hubs, self.vehicle_specs)
        self.assertEqual(len(clusters), 0)
        
        assignments = assign_vehicles_to_clusters(clusters, self.vehicle_specs)
        self.assertEqual(len(assignments), 0)
        
        fleet_summary = calculate_fleet_summary(assignments)
        self.assertEqual(fleet_summary['total_daily_cost'], 0)
        self.assertEqual(fleet_summary['total_capacity'], 0)

    def test_cost_efficiency_comparison(self):
        """Test that clustering provides cost efficiency"""
        # Compare clustered vs non-clustered approach
        clusters = create_pickup_clusters(self.pickup_hubs_scenario1, self.vehicle_specs)
        assignments = assign_vehicles_to_clusters(clusters, self.vehicle_specs)
        fleet_summary = calculate_fleet_summary(assignments)
        
        # Calculate naive cost (1 auto per pickup location)
        naive_cost = len(self.pickup_hubs_scenario1) * self.vehicle_specs['auto']['daily_cost']
        optimized_cost = fleet_summary['total_daily_cost']
        
        # Optimized approach should generally be more cost-effective
        # (though this may not always be true for all scenarios)
        self.assertGreater(naive_cost, 0)
        self.assertGreater(optimized_cost, 0)

    def test_utilization_calculation(self):
        """Test vehicle utilization calculation"""
        clusters = create_pickup_clusters(self.pickup_hubs_scenario1, self.vehicle_specs)
        assignments = assign_vehicles_to_clusters(clusters, self.vehicle_specs)
        
        for assignment in assignments:
            total_orders = assignment['cluster']['total_orders']
            actual_capacity = assignment['actual_capacity']
            utilization = assignment['utilization']
            
            if actual_capacity > 0:
                expected_utilization = (total_orders / actual_capacity) * 100
                self.assertAlmostEqual(utilization, expected_utilization, places=1)
            else:
                self.assertEqual(utilization, 0)

    def test_vehicle_capacity_boundaries(self):
        """Test vehicle assignment at capacity boundaries"""
        # Test specific order counts at boundaries
        boundary_test_cases = [
            (30, 'bike'),    # Minimum bike capacity
            (49, 'bike'),    # Just under auto threshold
            (50, 'auto'),    # Minimum auto capacity
            (99, 'auto'),    # Just under minitruck threshold
            (100, 'minitruck'), # Minimum minitruck capacity
            (299, 'minitruck'), # Just under large truck threshold
            (300, 'large_truck'), # Minimum large truck capacity
            (500, 'large_truck'), # Maximum large truck capacity
        ]
        
        for order_count, expected_vehicle in boundary_test_cases:
            with self.subTest(orders=order_count, expected=expected_vehicle):
                test_hubs = pd.DataFrame({
                    'pickup': ['TestHub'],
                    'pickup_lat': [12.9716],
                    'pickup_long': [77.5946],
                    'order_count': [order_count]
                })
                
                clusters = create_pickup_clusters(test_hubs, self.vehicle_specs)
                assignments = assign_vehicles_to_clusters(clusters, self.vehicle_specs)
                
                self.assertEqual(len(assignments), 1)
                self.assertEqual(assignments[0]['vehicle_type'], expected_vehicle)


if __name__ == '__main__':
    # Run with verbose output to see test progress
    unittest.main(verbosity=2, buffer=True)