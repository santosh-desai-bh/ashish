import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import sys
import os

# Add the current directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pincode_warehouse_logic import create_pincode_based_network
from warehouse_logic import create_pincode_based_feeder_network


class TestWarehouseRadiusLogic(unittest.TestCase):
    """Test suite for warehouse count logic based on delivery radius"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample order data
        np.random.seed(42)  # For reproducible tests
        
        # Generate sample orders around Delhi/Bangalore coordinates
        lats = np.random.normal(12.9716, 0.1, 1000)  # Bangalore area
        lons = np.random.normal(77.5946, 0.1, 1000)
        
        self.sample_df = pd.DataFrame({
            'latitude': lats,
            'longitude': lons,
            'customer_pincode': [f"5600{i%100:02d}" for i in range(1000)],
            'order_id': range(1000),
            'order_date': pd.date_range('2024-01-01', periods=1000, freq='H')
        })
        
        # Sample big warehouses (hubs)
        self.big_warehouses = [
            {
                'lat': 12.9716,
                'lon': 77.5946,
                'id': 'HUB001',
                'capacity': 1000,
                'size_category': 'Large'
            },
            {
                'lat': 12.8716,
                'lon': 77.4946,
                'id': 'HUB002',
                'capacity': 800,
                'size_category': 'Large'
            }
        ]

    @patch('pincode_warehouse_logic.load_pincode_boundaries')
    @patch('pincode_warehouse_logic.analyze_order_density_by_pincode')
    @patch('pincode_warehouse_logic.select_optimal_pincode_feeders')
    @patch('pincode_warehouse_logic.assign_feeders_to_hubs')
    def test_warehouse_count_changes_with_radius(self, mock_assign, mock_select, mock_analyze, mock_load):
        """Test that warehouse count changes based on delivery radius"""
        
        # Mock the external dependencies
        mock_load.return_value = {"560001": {"boundary": "mock_boundary"}}
        mock_analyze.return_value = [{"pincode": "560001", "orders": 100, "density": 50}]
        
        # Test different radius values and their expected max_feeders
        test_cases = [
            (2, 35),  # 2km radius should allow 35 max feeders
            (3, 25),  # 3km radius should allow 25 max feeders  
            (5, 15),  # 5km radius should allow 15 max feeders
        ]
        
        for delivery_radius, expected_max_feeders in test_cases:
            with self.subTest(radius=delivery_radius):
                # Reset the mock to capture the call
                mock_select.reset_mock()
                
                # Mock the return values
                mock_select.return_value = [{"lat": 12.97, "lon": 77.59, "orders": 100}] * min(expected_max_feeders, 10)
                mock_assign.return_value = [{"lat": 12.97, "lon": 77.59, "coverage_orders": 100, "density": 50}] * min(expected_max_feeders, 10)
                
                # Call the function
                create_pincode_based_network(
                    self.sample_df, 
                    self.big_warehouses, 
                    delivery_radius=delivery_radius
                )
                
                # Verify that select_optimal_pincode_feeders was called with the correct max_feeders
                mock_select.assert_called_once()
                call_args = mock_select.call_args
                self.assertEqual(call_args[1]['max_feeders'], expected_max_feeders)

    def test_warehouse_count_boundary_conditions(self):
        """Test boundary conditions for delivery radius"""
        
        with patch('pincode_warehouse_logic.load_pincode_boundaries') as mock_load, \
             patch('pincode_warehouse_logic.analyze_order_density_by_pincode') as mock_analyze, \
             patch('pincode_warehouse_logic.select_optimal_pincode_feeders') as mock_select, \
             patch('pincode_warehouse_logic.assign_feeders_to_hubs') as mock_assign:
            
            mock_load.return_value = {"560001": {"boundary": "mock_boundary"}}
            mock_analyze.return_value = [{"pincode": "560001", "orders": 100, "density": 50}]
            mock_select.return_value = []
            mock_assign.return_value = []
            
            # Test edge cases
            test_cases = [
                (1.9, 35),   # Just under 2km
                (2.0, 35),   # Exactly 2km
                (2.1, 25),   # Just over 2km
                (3.0, 25),   # Exactly 3km
                (3.1, 15),   # Just over 3km
                (5.0, 15),   # Exactly 5km
                (6.0, 15),   # Over 5km
            ]
            
            for delivery_radius, expected_max_feeders in test_cases:
                with self.subTest(radius=delivery_radius):
                    mock_select.reset_mock()
                    
                    create_pincode_based_network(
                        self.sample_df, 
                        self.big_warehouses, 
                        delivery_radius=delivery_radius
                    )
                    
                    call_args = mock_select.call_args
                    self.assertEqual(call_args[1]['max_feeders'], expected_max_feeders,
                                   f"Failed for radius {delivery_radius}")

    @patch('pincode_warehouse_logic.create_pincode_based_network')
    def test_feeder_network_passes_radius(self, mock_create_network):
        """Test that create_pincode_based_feeder_network passes delivery_radius correctly"""
        
        mock_create_network.return_value = ([], [])  # Empty feeder assignments and clusters
        
        delivery_radius = 2.5
        min_cluster_size = 50
        max_distance_from_big = 10
        
        # Call the wrapper function
        create_pincode_based_feeder_network(
            self.sample_df, 
            self.big_warehouses, 
            min_cluster_size, 
            max_distance_from_big, 
            delivery_radius
        )
        
        # Verify the underlying function was called with the correct delivery_radius
        mock_create_network.assert_called_once_with(
            self.sample_df, 
            self.big_warehouses, 
            min_cluster_size, 
            max_distance_from_big,
            delivery_radius  # This should be passed through
        )

    def test_default_delivery_radius(self):
        """Test that default delivery radius is handled correctly"""
        
        with patch('pincode_warehouse_logic.load_pincode_boundaries') as mock_load, \
             patch('pincode_warehouse_logic.analyze_order_density_by_pincode') as mock_analyze, \
             patch('pincode_warehouse_logic.select_optimal_pincode_feeders') as mock_select, \
             patch('pincode_warehouse_logic.assign_feeders_to_hubs') as mock_assign:
            
            mock_load.return_value = {"560001": {"boundary": "mock_boundary"}}
            mock_analyze.return_value = [{"pincode": "560001", "orders": 100, "density": 50}]
            mock_select.return_value = []
            mock_assign.return_value = []
            
            # Call without specifying delivery_radius (should default to 3)
            create_pincode_based_network(self.sample_df, self.big_warehouses)
            
            # Should use default of 25 max_feeders (for 3km radius)
            call_args = mock_select.call_args
            self.assertEqual(call_args[1]['max_feeders'], 25)

    def test_warehouse_count_regression(self):
        """Regression test to ensure warehouse count always changes with radius"""
        
        with patch('pincode_warehouse_logic.load_pincode_boundaries') as mock_load, \
             patch('pincode_warehouse_logic.analyze_order_density_by_pincode') as mock_analyze, \
             patch('pincode_warehouse_logic.select_optimal_pincode_feeders') as mock_select, \
             patch('pincode_warehouse_logic.assign_feeders_to_hubs') as mock_assign:
            
            mock_load.return_value = {"560001": {"boundary": "mock_boundary"}}
            mock_analyze.return_value = [{"pincode": "560001", "orders": 100, "density": 50}]
            mock_assign.return_value = []
            
            # Track max_feeders values for different radii
            max_feeders_values = []
            radii = [2, 3, 5]
            
            for radius in radii:
                mock_select.reset_mock()
                mock_select.return_value = []
                
                create_pincode_based_network(
                    self.sample_df, 
                    self.big_warehouses, 
                    delivery_radius=radius
                )
                
                call_args = mock_select.call_args
                max_feeders_values.append(call_args[1]['max_feeders'])
            
            # Verify that max_feeders decreases as radius increases
            self.assertEqual(max_feeders_values, [35, 25, 15])
            
            # Ensure they are all different (no stuck at 25 bug)
            self.assertEqual(len(set(max_feeders_values)), 3, 
                           "All radius values should produce different max_feeders counts")


class TestWarehouseLogicIntegration(unittest.TestCase):
    """Integration tests for the complete warehouse logic flow"""
    
    def test_radius_parameter_flow(self):
        """Test that delivery_radius parameter flows correctly through the system"""
        
        # This is a simple test to verify the parameter passing works
        # We don't need complex integration since the unit tests cover the logic
        
        sample_df = pd.DataFrame({
            'latitude': [12.97, 12.98],
            'longitude': [77.59, 77.60],
            'customer_pincode': ["560001", "560002"],
            'order_id': [1, 2]
        })
        
        big_warehouses = [{'lat': 12.97, 'lon': 77.59, 'id': 'HUB001', 'capacity': 1000}]
        
        # Test that the function accepts delivery_radius parameter without error
        try:
            with patch('pincode_warehouse_logic.load_pincode_boundaries') as mock_load, \
                 patch('pincode_warehouse_logic.analyze_order_density_by_pincode') as mock_analyze, \
                 patch('pincode_warehouse_logic.select_optimal_pincode_feeders') as mock_select, \
                 patch('pincode_warehouse_logic.assign_feeders_to_hubs') as mock_assign:
                
                mock_load.return_value = {"560001": {"boundary": "mock"}}
                mock_analyze.return_value = []
                mock_select.return_value = []
                mock_assign.return_value = []
                
                # This should not raise an error
                create_pincode_based_network(
                    sample_df, 
                    big_warehouses, 
                    delivery_radius=2
                )
                
                # Verify select_optimal_pincode_feeders was called with max_feeders=35 for radius=2
                call_args = mock_select.call_args
                self.assertEqual(call_args[1]['max_feeders'], 35)
                
            self.assertTrue(True, "Function executed successfully with delivery_radius parameter")
            
        except Exception as e:
            self.fail(f"Function failed with delivery_radius parameter: {e}")


if __name__ == '__main__':
    # Run with verbose output to see test progress
    unittest.main(verbosity=2, buffer=True)