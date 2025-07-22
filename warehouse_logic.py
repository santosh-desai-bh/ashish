import numpy as np
import pandas as pd

def find_order_density_clusters(df_filtered, min_cluster_size=30):
    """Find high-density order clusters for feeder warehouse placement"""
    # Create density grid (finer grid for better cluster detection)
    lat_min, lat_max = df_filtered['order_lat'].min(), df_filtered['order_lat'].max()
    lon_min, lon_max = df_filtered['order_long'].min(), df_filtered['order_long'].max()
    
    # Use smaller grid cells for better granularity (0.005 degrees ≈ 0.5km for better coverage)
    grid_size = 0.005  # degrees - reduced for better granularity
    lat_steps = int((lat_max - lat_min) / grid_size) + 1
    lon_steps = int((lon_max - lon_min) / grid_size) + 1
    
    density_clusters = []
    
    for i in range(lat_steps):
        for j in range(lon_steps):
            cell_lat_min = lat_min + i * grid_size
            cell_lat_max = cell_lat_min + grid_size
            cell_lon_min = lon_min + j * grid_size
            cell_lon_max = cell_lon_min + grid_size
            
            # Count orders in this grid cell
            cell_orders = df_filtered[
                (df_filtered['order_lat'] >= cell_lat_min) & 
                (df_filtered['order_lat'] < cell_lat_max) &
                (df_filtered['order_long'] >= cell_lon_min) & 
                (df_filtered['order_long'] < cell_lon_max)
            ]
            
            order_count = len(cell_orders)
            
            if order_count >= min_cluster_size:
                # Calculate cluster center (centroid of orders in this cell)
                cluster_center_lat = cell_orders['order_lat'].mean()
                cluster_center_lon = cell_orders['order_long'].mean()
                
                # Calculate density score (orders per km²)
                area_km2 = (grid_size * 111) ** 2  # Convert degrees to km²
                density_score = order_count / area_km2
                
                density_clusters.append({
                    'lat': cluster_center_lat,
                    'lon': cluster_center_lon,
                    'order_count': order_count,
                    'density_score': density_score,
                    'cell_bounds': {
                        'lat_min': cell_lat_min,
                        'lat_max': cell_lat_max,
                        'lon_min': cell_lon_min,
                        'lon_max': cell_lon_max
                    }
                })
    
    # Sort by density score (orders per km²) descending
    density_clusters.sort(key=lambda x: x['density_score'], reverse=True)
    
    return density_clusters

def place_feeder_warehouses_near_clusters(density_clusters, big_warehouses, max_distance_from_big=8.0):
    """Place feeder warehouses at density clusters within range of big warehouses"""
    feeder_warehouses = []
    aux_id_counter = 1
    
    for cluster in density_clusters:
        cluster_lat, cluster_lon = cluster['lat'], cluster['lon']
        
        # Find nearest big warehouse
        min_distance_to_big = float('inf')
        nearest_big_warehouse = None
        
        for big_wh in big_warehouses:
            distance = ((cluster_lat - big_wh['lat'])**2 + (cluster_lon - big_wh['lon'])**2)**0.5 * 111
            if distance < min_distance_to_big:
                min_distance_to_big = distance
                nearest_big_warehouse = big_wh
        
        # Only place feeder if within reasonable distance from a big warehouse
        if min_distance_to_big <= max_distance_from_big:
            # Check if there's already a feeder warehouse too close to this location
            too_close = False
            for existing_feeder in feeder_warehouses:
                distance_to_existing = ((cluster_lat - existing_feeder['lat'])**2 + 
                                      (cluster_lon - existing_feeder['lon'])**2)**0.5 * 111
                if distance_to_existing < 1.5:  # Reduced minimum separation to 1.5km for better coverage
                    too_close = True
                    break
            
            if not too_close:
                # Determine feeder warehouse capacity based on local order density
                order_count = cluster['order_count']
                if order_count >= 100:  # Reduced thresholds for better coverage
                    capacity = 200
                    size_category = "Large"
                elif order_count >= 50:
                    capacity = 100
                    size_category = "Medium"
                else:
                    capacity = 50
                    size_category = "Small"
                
                feeder_warehouses.append({
                    'id': aux_id_counter,
                    'lat': cluster_lat,
                    'lon': cluster_lon,
                    'orders': order_count,
                    'capacity': capacity,
                    'size_category': size_category,
                    'parent': nearest_big_warehouse['id'],
                    'distance_to_parent': min_distance_to_big,
                    'density_score': cluster['density_score'],
                    'type': 'feeder'
                })
                
                aux_id_counter += 1
    
    return feeder_warehouses

def create_comprehensive_feeder_network(df_filtered, big_warehouses, min_cluster_size=20, max_distance_from_big=8.0):
    """Create a comprehensive feeder network ensuring 2km coverage for all orders"""
    
    # Step 1: Find high-density clusters
    density_clusters = find_order_density_clusters(df_filtered, min_cluster_size)
    feeder_warehouses = place_feeder_warehouses_near_clusters(density_clusters, big_warehouses, max_distance_from_big)
    
    # Step 2: Find uncovered orders (more than 2km from any feeder)
    uncovered_orders = []
    for _, order in df_filtered.iterrows():
        order_lat, order_lon = order['order_lat'], order['order_long']
        
        # Check distance to all feeders
        min_distance_to_feeder = float('inf')
        for feeder in feeder_warehouses:
            distance = ((order_lat - feeder['lat'])**2 + (order_lon - feeder['lon'])**2)**0.5 * 111
            min_distance_to_feeder = min(min_distance_to_feeder, distance)
        
        # If more than 2km from nearest feeder, mark as uncovered
        if min_distance_to_feeder > 2.0:
            uncovered_orders.append({
                'lat': order_lat,
                'lon': order_lon,
                'distance_to_nearest_feeder': min_distance_to_feeder
            })
    
    # Step 3: Create additional feeders for uncovered areas
    additional_feeders = []
    aux_id_counter = len(feeder_warehouses) + 1
    
    if uncovered_orders:
        # Group uncovered orders by proximity
        uncovered_df = pd.DataFrame(uncovered_orders)
        
        # Use smaller grid for uncovered areas
        lat_min, lat_max = uncovered_df['lat'].min(), uncovered_df['lat'].max()
        lon_min, lon_max = uncovered_df['lon'].min(), uncovered_df['lon'].max()
        
        grid_size = 0.01  # 1km grid for uncovered areas
        lat_steps = int((lat_max - lat_min) / grid_size) + 1
        lon_steps = int((lon_max - lon_min) / grid_size) + 1
        
        for i in range(lat_steps):
            for j in range(lon_steps):
                cell_lat_min = lat_min + i * grid_size
                cell_lat_max = cell_lat_min + grid_size
                cell_lon_min = lon_min + j * grid_size
                cell_lon_max = cell_lon_min + grid_size
                
                # Count uncovered orders in this cell
                cell_uncovered = [
                    order for order in uncovered_orders
                    if (cell_lat_min <= order['lat'] < cell_lat_max) and 
                       (cell_lon_min <= order['lon'] < cell_lon_max)
                ]
                
                if len(cell_uncovered) >= 10:  # Minimum 10 uncovered orders to justify a feeder
                    # Calculate center of uncovered orders in this cell
                    cell_center_lat = sum([order['lat'] for order in cell_uncovered]) / len(cell_uncovered)
                    cell_center_lon = sum([order['lon'] for order in cell_uncovered]) / len(cell_uncovered)
                    
                    # Find nearest big warehouse
                    min_distance_to_big = float('inf')
                    nearest_big_warehouse = None
                    
                    for big_wh in big_warehouses:
                        distance = ((cell_center_lat - big_wh['lat'])**2 + (cell_center_lon - big_wh['lon'])**2)**0.5 * 111
                        if distance < min_distance_to_big:
                            min_distance_to_big = distance
                            nearest_big_warehouse = big_wh
                    
                    # Only place if within distance limit and not too close to existing feeders
                    if min_distance_to_big <= max_distance_from_big:
                        too_close = False
                        all_feeders = feeder_warehouses + additional_feeders
                        
                        for existing_feeder in all_feeders:
                            distance_to_existing = ((cell_center_lat - existing_feeder['lat'])**2 + 
                                                  (cell_center_lon - existing_feeder['lon'])**2)**0.5 * 111
                            if distance_to_existing < 1.5:  # 1.5km minimum separation
                                too_close = True
                                break
                        
                        if not too_close:
                            additional_feeders.append({
                                'id': aux_id_counter,
                                'lat': cell_center_lat,
                                'lon': cell_center_lon,
                                'orders': len(cell_uncovered),
                                'capacity': 50,  # Start with small capacity for gap-filling feeders
                                'size_category': "Small",
                                'parent': nearest_big_warehouse['id'],
                                'distance_to_parent': min_distance_to_big,
                                'density_score': len(cell_uncovered) / ((grid_size * 111) ** 2),
                                'type': 'feeder'
                            })
                            aux_id_counter += 1
    
    # Combine all feeders
    all_feeders = feeder_warehouses + additional_feeders
    
    return all_feeders, density_clusters

def determine_optimal_date_range(daily_summary, max_orders=5000):
    """Determine optimal date range for performance"""
    daily_summary = daily_summary.sort_values('Date', ascending=False)
    
    cumulative_orders = 0
    optimal_days = 0
    
    for _, row in daily_summary.iterrows():
        cumulative_orders += row['Orders']
        optimal_days += 1
        
        if cumulative_orders >= max_orders:
            break
    
    return optimal_days

def calculate_big_warehouse_locations(df_filtered):
    """Calculate optimal locations for big warehouses (IF Hubs)"""
    try:
        total_orders = len(df_filtered)
        
        # Determine big warehouses (500 daily capacity) based on order volume
        big_warehouse_count = max(1, total_orders // 500)
        big_warehouse_count = min(big_warehouse_count, 4)  # Cap at 4 for Bangalore
        
        # Use geographic distribution for warehouse placement - prioritize city center areas
        lat_median = df_filtered['order_lat'].median()
        lon_median = df_filtered['order_long'].median()
        lat_range = df_filtered['order_lat'].max() - df_filtered['order_lat'].min()
        lon_range = df_filtered['order_long'].max() - df_filtered['order_long'].min()
        
        # Handle edge case where lat_range or lon_range is 0
        if lat_range == 0:
            lat_range = 0.01
        if lon_range == 0:
            lon_range = 0.01
        
        # Find high-density urban areas for big warehouse placement
        grid_size = 5
        lat_step = lat_range / grid_size
        lon_step = lon_range / grid_size
        
        density_zones = []
        for i in range(grid_size):
            for j in range(grid_size):
                zone_lat_min = df_filtered['order_lat'].min() + i * lat_step
                zone_lat_max = zone_lat_min + lat_step
                zone_lon_min = df_filtered['order_long'].min() + j * lon_step
                zone_lon_max = zone_lon_min + lon_step
                
                # Count orders in this zone
                zone_orders = df_filtered[
                    (df_filtered['order_lat'] >= zone_lat_min) & 
                    (df_filtered['order_lat'] < zone_lat_max) &
                    (df_filtered['order_long'] >= zone_lon_min) & 
                    (df_filtered['order_long'] < zone_lon_max)
                ]
                
                if len(zone_orders) > 0:
                    zone_center_lat = zone_lat_min + lat_step/2
                    zone_center_lon = zone_lon_min + lon_step/2
                    density_zones.append({
                        'lat': zone_center_lat,
                        'lon': zone_center_lon,
                        'density': len(zone_orders),
                        'distance_from_center': ((zone_center_lat - lat_median)**2 + (zone_center_lon - lon_median)**2)**0.5
                    })
        
        # Sort zones by density and proximity to city center
        density_zones.sort(key=lambda x: (-x['density'], x['distance_from_center']))
        
        # Select top density zones for big warehouses
        urban_zones = []
        for zone in density_zones:
            if zone['distance_from_center'] <= 0.6 * max(lat_range, lon_range):
                urban_zones.append(zone)
                if len(urban_zones) >= big_warehouse_count * 2:
                    break
        
        # Place big warehouses (IF Hubs)
        if len(urban_zones) >= big_warehouse_count:
            big_warehouse_centers = []
            selected_zones = []
            
            for i in range(big_warehouse_count):
                best_zone = None
                max_min_distance = 0
                
                for zone in urban_zones:
                    if zone in selected_zones:
                        continue
                    
                    min_distance_to_selected = float('inf')
                    for selected in selected_zones:
                        distance = ((zone['lat'] - selected['lat'])**2 + (zone['lon'] - selected['lon'])**2)**0.5
                        min_distance_to_selected = min(min_distance_to_selected, distance)
                    
                    if len(selected_zones) == 0 or min_distance_to_selected > max_min_distance:
                        max_min_distance = min_distance_to_selected
                        best_zone = zone
                
                if best_zone:
                    selected_zones.append(best_zone)
                    big_warehouse_centers.append([best_zone['lat'], best_zone['lon']])
        else:
            # Fallback placement
            if big_warehouse_count == 1:
                big_warehouse_centers = [[lat_median, lon_median]]
            elif big_warehouse_count == 2:
                big_warehouse_centers = [
                    [lat_median + lat_range/6, lon_median],
                    [lat_median - lat_range/6, lon_median]
                ]
            elif big_warehouse_count == 3:
                big_warehouse_centers = [
                    [lat_median + lat_range/6, lon_median],
                    [lat_median - lat_range/8, lon_median - lon_range/6],
                    [lat_median - lat_range/8, lon_median + lon_range/6]
                ]
            else:  # 4 warehouses
                big_warehouse_centers = [
                    [lat_median + lat_range/6, lon_median + lon_range/6],
                    [lat_median + lat_range/6, lon_median - lon_range/6],
                    [lat_median - lat_range/6, lon_median + lon_range/6],
                    [lat_median - lat_range/6, lon_median - lon_range/6]
                ]
        
        return big_warehouse_centers, big_warehouse_count
    
    except Exception as e:
        # Fallback to simple center placement if anything goes wrong
        print(f"Error in calculate_big_warehouse_locations: {e}")
        lat_center = df_filtered['order_lat'].mean()
        lon_center = df_filtered['order_long'].mean()
        return [[lat_center, lon_center]], 1
