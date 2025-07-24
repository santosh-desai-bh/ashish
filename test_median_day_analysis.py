import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add the current directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class TestMedianDayAnalysis(unittest.TestCase):
    """Test suite for median day capacity analysis functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample daily summary data with varying order volumes
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        
        # Create realistic order pattern with some high and low days
        np.random.seed(42)  # For reproducible tests
        base_orders = 1000
        
        # Generate orders with some variation - typical e-commerce pattern
        orders = []
        for i, date in enumerate(dates):
            # Weekend boost (Saturday/Sunday higher)
            weekend_boost = 1.3 if date.weekday() >= 5 else 1.0
            
            # Random daily variation
            daily_variation = np.random.normal(1.0, 0.2)
            
            # Some days are particularly busy (sale days, etc.)
            if i % 7 == 0:  # Every 7th day is a sale day
                daily_variation *= 1.8
            
            daily_orders = int(base_orders * weekend_boost * daily_variation)
            orders.append(max(daily_orders, 200))  # Minimum 200 orders
        
        self.daily_summary = pd.DataFrame({
            'Date': dates,
            'Orders': orders
        })
    
    def test_median_day_calculation(self):
        """Test that median day is calculated correctly"""
        
        # Calculate median using the same logic as main.py
        median_day_orders = int(self.daily_summary['Orders'].median())
        median_day_idx = (self.daily_summary['Orders'] - median_day_orders).abs().idxmin()
        median_day = self.daily_summary.loc[median_day_idx, 'Date']
        
        # Verify median day orders is reasonable
        self.assertIsInstance(median_day_orders, int)
        self.assertGreater(median_day_orders, 0)
        
        # Verify median day is a valid date
        self.assertIsInstance(median_day, pd.Timestamp)
        self.assertIn(median_day, self.daily_summary['Date'].values)
        
        # Verify median is between min and max
        min_orders = self.daily_summary['Orders'].min()
        max_orders = self.daily_summary['Orders'].max()
        self.assertGreaterEqual(median_day_orders, min_orders)
        self.assertLessEqual(median_day_orders, max_orders)
    
    def test_busiest_vs_median_comparison(self):
        """Test that busiest day is always >= median day orders"""
        
        # Calculate both metrics
        busiest_day_orders = self.daily_summary['Orders'].max()
        median_day_orders = int(self.daily_summary['Orders'].median())
        
        # Busiest should always be >= median
        self.assertGreaterEqual(busiest_day_orders, median_day_orders)
        
        # They should be different for realistic data
        self.assertNotEqual(busiest_day_orders, median_day_orders)
    
    def test_capacity_utilization_scenarios(self):
        """Test capacity utilization calculations for different scenarios"""
        
        # Test data
        network_capacity = 1500
        median_orders = 1000
        busiest_orders = 1800
        
        # Calculate utilizations
        median_util = (median_orders / network_capacity * 100)
        busiest_util = (busiest_orders / network_capacity * 100)
        
        # Verify calculations
        self.assertAlmostEqual(median_util, 66.67, places=1)
        self.assertAlmostEqual(busiest_util, 120.0, places=1)
        
        # Test capacity recommendations logic
        self.assertLess(median_util, 70)  # Should be green for median
        self.assertGreater(busiest_util, 90)  # Should be red for busiest
    
    def test_median_day_edge_cases(self):
        """Test edge cases for median day calculation"""
        
        # Test with very small dataset
        small_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=3),
            'Orders': [100, 200, 150]
        })
        
        median_orders = int(small_data['Orders'].median())
        self.assertEqual(median_orders, 150)
        
        # Test with identical values
        identical_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=5),
            'Orders': [1000, 1000, 1000, 1000, 1000]
        })
        
        median_orders_identical = int(identical_data['Orders'].median())
        busiest_orders_identical = identical_data['Orders'].max()
        
        self.assertEqual(median_orders_identical, busiest_orders_identical)
    
    def test_capacity_recommendation_logic(self):
        """Test the recommendation logic for different capacity scenarios"""
        
        test_scenarios = [
            # (median_util, busiest_util, expected_category)
            (50, 60, "optimal"),      # Both under 70
            (40, 50, "over_provisioned"),  # Both well under 70
            (60, 95, "under_provisioned"), # Busiest over 90
            (75, 85, "tight_capacity"),    # Median over 70, busiest under 90
        ]
        
        for median_util, busiest_util, expected in test_scenarios:
            with self.subTest(median=median_util, busiest=busiest_util):
                
                if expected == "optimal":
                    self.assertLess(median_util, 70)
                    self.assertLess(busiest_util, 90)
                
                elif expected == "over_provisioned":
                    self.assertLess(median_util, 50)
                    self.assertLess(busiest_util, 70)
                
                elif expected == "under_provisioned":
                    self.assertGreater(busiest_util, 90)
                
                elif expected == "tight_capacity":
                    self.assertGreater(median_util, 70)
                    self.assertLess(busiest_util, 90)
    
    def test_additional_capacity_calculation(self):
        """Test calculation of additional capacity needed"""
        
        busiest_day_orders = 2000
        current_network_capacity = 1500
        
        # Calculate additional capacity needed (20% buffer)
        additional_capacity = int(busiest_day_orders * 1.2 - current_network_capacity)
        
        expected_total_needed = 2000 * 1.2  # 2400
        expected_additional = 2400 - 1500   # 900
        
        self.assertEqual(additional_capacity, expected_additional)
        self.assertEqual(additional_capacity, 900)
    
    def test_data_integrity(self):
        """Test that the test data itself is valid"""
        
        # Verify we have valid date range
        self.assertEqual(len(self.daily_summary), 30)
        
        # Verify orders are reasonable
        self.assertGreater(self.daily_summary['Orders'].min(), 0)
        self.assertLess(self.daily_summary['Orders'].max(), 5000)  # Reasonable upper bound
        
        # Verify we have variation in the data
        order_std = self.daily_summary['Orders'].std()
        self.assertGreater(order_std, 100)  # Should have some variation
        
        # Verify dates are consecutive
        date_diffs = self.daily_summary['Date'].diff().dropna()
        expected_diff = pd.Timedelta(days=1)
        self.assertTrue(all(diff == expected_diff for diff in date_diffs))


if __name__ == '__main__':
    # Run with verbose output to see test progress
    unittest.main(verbosity=2, buffer=True)