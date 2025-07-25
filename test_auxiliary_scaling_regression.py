#!/usr/bin/env python3
"""
Regression test for auxiliary warehouse scaling with delivery radius
Ensures that auxiliary count decreases as delivery radius increases
"""
import pandas as pd
import numpy as np
from warehouse_logic import create_comprehensive_feeder_network, calculate_big_warehouse_locations

class TestAuxiliaryScalingRegression:
    def setUp(self):
        """Create realistic test data that should generate auxiliaries"""
        np.random.seed(42)
        
        # Create clustered data with clear density hotspots
        n_orders = 2000
        center_lat, center_lon = 12.9716, 77.5946
        
        # Create 3 distinct density clusters
        cluster1_orders = 800  # High density cluster
        cluster2_orders = 600  # Medium density cluster  
        cluster3_orders = 600  # Medium density cluster
        
        orders = []
        
        # Cluster 1: Northeast (high density)
        cluster1_lat, cluster1_lon = center_lat + 0.03, center_lon + 0.03
        for _ in range(cluster1_orders):
            orders.append({
                'order_lat': np.random.normal(cluster1_lat, 0.008),
                'order_long': np.random.normal(cluster1_lon, 0.008),
            })
        
        # Cluster 2: Southwest (medium density)
        cluster2_lat, cluster2_lon = center_lat - 0.03, center_lon - 0.03
        for _ in range(cluster2_orders):
            orders.append({
                'order_lat': np.random.normal(cluster2_lat, 0.012),
                'order_long': np.random.normal(cluster2_lon, 0.012),
            })
            
        # Cluster 3: Southeast (medium density)
        cluster3_lat, cluster3_lon = center_lat - 0.02, center_lon + 0.04
        for _ in range(cluster3_orders):
            orders.append({
                'order_lat': np.random.normal(cluster3_lat, 0.015),
                'order_long': np.random.normal(cluster3_lon, 0.015),
            })
        
        self.df_test = pd.DataFrame(orders)
        self.df_test['created_date'] = pd.date_range('2024-01-01', periods=len(orders), freq='30min')
        
        # Create big warehouses
        big_warehouse_centers, _ = calculate_big_warehouse_locations(self.df_test)
        self.big_warehouses = []
        for i, (lat, lon) in enumerate(big_warehouse_centers):
            self.big_warehouses.append({
                'id': i+1,
                'lat': lat,
                'lon': lon,
                'hub_code': f'HUB{i+1}',
                'capacity': 500,
                'type': 'hub'
            })
    
    def test_auxiliary_scaling_regression(self):
        """Main regression test: auxiliary count should decrease as delivery radius increases"""
        print("🧪 AUXILIARY SCALING REGRESSION TEST")
        print("=" * 50)
        
        self.setUp()
        
        # Test different delivery radii with lower min_cluster_size to ensure we find clusters
        test_radii = [2, 3, 5]
        results = {}
        
        for radius in test_radii:
            auxiliaries, clusters = create_comprehensive_feeder_network(
                self.df_test,
                self.big_warehouses,
                max_distance_from_big=15,
                delivery_radius=radius
            )
            
            results[radius] = {
                'auxiliaries': len(auxiliaries),
                'clusters': len(clusters)
            }
            
            print(f"  {radius}km radius: {len(auxiliaries)} auxiliaries, {len(clusters)} clusters")
        
        # Regression assertions
        aux_2km = results[2]['auxiliaries']
        aux_3km = results[3]['auxiliaries']
        aux_5km = results[5]['auxiliaries']
        
        print(f"\n🔍 SCALING VERIFICATION")
        print("-" * 30)
        print(f"2km: {aux_2km} auxiliaries")
        print(f"3km: {aux_3km} auxiliaries") 
        print(f"5km: {aux_5km} auxiliaries")
        
        # Primary assertion: scaling should work
        if aux_2km >= aux_3km >= aux_5km and (aux_2km > aux_5km):
            print("✅ PASS: Auxiliary count decreases as delivery radius increases")
            return True
        else:
            print("❌ FAIL: Auxiliary scaling is broken")
            print(f"   Expected: 2km({aux_2km}) >= 3km({aux_3km}) >= 5km({aux_5km}) with 2km > 5km")
            return False
    
    def test_auxiliary_limits_respected(self):
        """Test that auxiliary limits are respected for each radius"""
        print("\n🎯 AUXILIARY LIMITS TEST")
        print("=" * 30)
        
        self.setUp()
        
        # Expected limits from warehouse_logic.py
        expected_limits = {2: 6, 3: 4, 5: 2}
        
        for radius, expected_limit in expected_limits.items():
            auxiliaries, _ = create_comprehensive_feeder_network(
                self.df_test,
                self.big_warehouses,
                max_distance_from_big=15,
                delivery_radius=radius
            )
            
            actual_count = len(auxiliaries)
            
            if actual_count <= expected_limit:
                print(f"✅ {radius}km: {actual_count} auxiliaries (limit: {expected_limit})")
            else:
                print(f"❌ {radius}km: {actual_count} auxiliaries exceeds limit of {expected_limit}")
                return False
                
        return True
    
    def test_clusters_found_with_realistic_data(self):
        """Test that density clusters are actually found with realistic data"""
        print("\n🎯 CLUSTER DETECTION TEST")
        print("=" * 30)
        
        self.setUp()
        
        # Test cluster detection
        from warehouse_logic import find_order_density_clusters
        
        clusters = find_order_density_clusters(self.df_test, min_cluster_size=50, grid_size=0.015)
        
        if len(clusters) > 0:
            print(f"✅ Found {len(clusters)} density clusters")
            print(f"   Top cluster: {clusters[0]['order_count']} orders")
            return True
        else:
            print("❌ No density clusters found - data or parameters issue")
            return False

def run_all_regression_tests():
    """Run all auxiliary scaling regression tests"""
    test_suite = TestAuxiliaryScalingRegression()
    
    results = []
    results.append(test_suite.test_auxiliary_scaling_regression())
    results.append(test_suite.test_auxiliary_limits_respected()) 
    results.append(test_suite.test_clusters_found_with_realistic_data())
    
    print(f"\n📊 REGRESSION TEST RESULTS")
    print("=" * 40)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✅ Auxiliary scaling regression suite is healthy")
    else:
        print(f"❌ TESTS FAILED ({passed}/{total})")
        print("⚠️  Auxiliary scaling needs investigation")
    
    return passed == total

if __name__ == "__main__":
    run_all_regression_tests()