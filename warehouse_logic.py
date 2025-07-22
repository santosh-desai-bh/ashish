import numpy as np
import pandas as pd

def find_order_density_clusters(df_filtered, min_cluster_size=30, grid_size=0.005):
    """Find high-density order clusters for feeder warehouse placement"""
    # Create density grid (finer grid for better cluster detection)
    lat_min, lat_max = df_filtered['order_lat'].min(), df_filtered['order_lat'].max()
    lon_min, lon_max = df_filtered['order_long'].min(), df_filtered['order_long'].max()
    
    # Use configurable grid size
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

def place_feeder_warehouses_near_clusters(density_clusters, big_warehouses, max_distance_from_big=8.0, delivery_radius=2.0, feeder_separation=1.5):
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
                if distance_to_existing < feeder_separation:
                    too_close = True
                    break
            
            if not too_close:
                # Determine feeder warehouse capacity based on delivery radius and order density
                order_count = cluster['order_count']
                
                if delivery_radius <= 2:
                    # Dense network for 2km radius
                    if order_count >= 80:
                        capacity = 150
                        size_category = "Large"
                    elif order_count >= 40:
                        capacity = 80
                        size_category = "Medium"
                    else:
                        capacity = 40
                        size_category = "Small"
                elif delivery_radius <= 3:
                    # Balanced network for 3km radius
                    if order_count >= 100:
                        capacity = 200
                        size_category = "Large"
                    elif order_count >= 60:
                        capacity = 120
                        size_category = "Medium"
                    else:
                        capacity = 60
                        size_category = "Small"
                elif delivery_radius <= 5:
                    # Wider coverage for 5km radius
                    if order_count >= 150:
                        capacity = 300
                        size_category = "Large"
                    elif order_count >= 80:
                        capacity = 180
                        size_category = "Medium"
                    else:
                        capacity = 100
                        size_category = "Small"
                else:
                    # Very wide coverage for 7km+ radius
                    if order_count >= 200:
                        capacity = 400
                        size_category = "Large"
                    elif order_count >= 100:
                        capacity = 250
                        size_category = "Medium"
                    else:
                        capacity = 150
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
                    'type': 'feeder',
                    'delivery_radius': delivery_radius
                })
                
                aux_id_counter += 1
    
    return feeder_warehouses

def create_comprehensive_feeder_network(df_filtered, big_warehouses, min_cluster_size=20, max_distance_from_big=8.0, delivery_radius=2.0):
    """Create a comprehensive feeder network ensuring delivery_radius coverage for all orders"""
    
    # Adjust grid size based on delivery radius (smaller radius = finer grid)
    if delivery_radius <= 2:
        grid_size = 0.005  # 0.5km grid for 2km radius
        min_gap_orders = 10
        feeder_separation = 1.5
    elif delivery_radius <= 3:
        grid_size = 0.007  # 0.7km grid for 3km radius
        min_gap_orders = 15
        feeder_separation = 2.0
    elif delivery_radius <= 5:
        grid_size = 0.01   # 1km grid for 5km radius
        min_gap_orders = 20
        feeder_separation = 3.0
    else:
        grid_size = 0.015  # 1.5km grid for 7km+ radius
        min_gap_orders = 25
        feeder_separation = 4.0
    
    # Step 1: Find high-density clusters with adjusted parameters
    density_clusters = find_order_density_clusters(df_filtered, min_cluster_size, grid_size)
    feeder_warehouses = place_feeder_warehouses_near_clusters(
        density_clusters, big_warehouses, max_distance_from_big, delivery_radius, feeder_separation
    )
    
    # Step 2: Find uncovered orders (more than delivery_radius from any feeder)
    uncovered_orders = []
    for _, order in df_filtered.iterrows():
        order_lat, order_lon = order['order_lat'], order['order_long']
        
        # Check distance to all feeders
        min_distance_to_feeder = float('inf')
        for feeder in feeder_warehouses:
            distance = ((order_lat - feeder['lat'])**2 + (order_lon - feeder['lon'])**2)**0.5 * 111
            min_distance_to_feeder = min(min_distance_to_feeder, distance)
        
        # If more than delivery_radius from nearest feeder, mark as uncovered
        if min_distance_to_feeder > delivery_radius:
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
        
        # Use grid for uncovered areas
        lat_min, lat_max = uncovered_df['lat'].min(), uncovered_df['lat'].max()
        lon_min, lon_max = uncovered_df['lon'].min(), uncovered_df['lon'].max()
        
        # Adjust grid size for gap-filling based on delivery radius
        gap_grid_size = grid_size * 1.5
        lat_steps = int((lat_max - lat_min) / gap_grid_size) + 1
        lon_steps = int((lon_max - lon_min) / gap_grid_size) + 1
        
        for i in range(lat_steps):
            for j in range(lon_steps):
                cell_lat_min = lat_min + i * gap_grid_size
                cell_lat_max = cell_lat_min + gap_grid_size
                cell_lon_min = lon_min + j * gap_grid_size
                cell_lon_max = cell_lon_min + gap_grid_size
                
                # Count uncovered orders in this cell
                cell_uncovered = [
                    order for order in uncovered_orders
                    if (cell_lat_min <= order['lat'] < cell_lat_max) and 
                       (cell_lon_min <= order['lon'] < cell_lon_max)
                ]
                
                if len(cell_uncovered) >= min_gap_orders:
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
                            if distance_to_existing < feeder_separation:
                                too_close = True
                                break
                        
                        if not too_close:
                            # Adjust capacity based on delivery radius and order count
                            if delivery_radius <= 2:
                                capacity = min(100, max(30, len(cell_uncovered) * 2))
                            elif delivery_radius <= 3:
                                capacity = min(150, max(50, len(cell_uncovered) * 2.5))
                            elif delivery_radius <= 5:
                                capacity = min(200, max(80, len(cell_uncovered) * 3))
                            else:
                                capacity = min(300, max(100, len(cell_uncovered) * 4))
                            
                            size_category = "Large" if capacity >= 150 else "Medium" if capacity >= 80 else "Small"
                            
                            additional_feeders.append({
                                'id': aux_id_counter,
                                'lat': cell_center_lat,
                                'lon': cell_center_lon,
                                'orders': len(cell_uncovered),
                                'capacity': capacity,
                                'size_category': size_category,
                                'parent': nearest_big_warehouse['id'],
                                'distance_to_parent': min_distance_to_big,
                                'density_score': len(cell_uncovered) / ((gap_grid_size * 111) ** 2),
                                'type': 'feeder',
                                'delivery_radius': delivery_radius
                            })
                            aux_id_counter += 1
    
    # Combine all feeders
    all_feeders = feeder_warehouses + additional_feeders
    
    # Add delivery radius info to all feeders
    for feeder in all_feeders:
        feeder['delivery_radius'] = delivery_radius
    
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
    """Calculate optimal locations for big warehouses (IF Hubs) with minimum 4-5 hubs"""
    try:
        total_orders = len(df_filtered)
        
        # Ensure minimum 4-5 big warehouses for proper first mile coverage
        big_warehouse_count = max(5, total_orders // 400)  # Minimum 5 hubs, 400 orders per hub
        big_warehouse_count = min(big_warehouse_count, 8)  # Cap at 8 for Bangalore
        
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
            # Fallback to geometric distribution for better coverage
            big_warehouse_centers = []
            if big_warehouse_count == 5:
                # Optimized 5-point distribution for Bangalore
                big_warehouse_centers = [
                    [lat_median, lon_median],  # Center
                    [lat_median + lat_range/4, lon_median + lon_range/4],  # NE
                    [lat_median + lat_range/4, lon_median - lon_range/4],  # NW
                    [lat_median - lat_range/4, lon_median + lon_range/4],  # SE
                    [lat_median - lat_range/4, lon_median - lon_range/4]   # SW
                ]
            elif big_warehouse_count == 6:
                big_warehouse_centers = [
                    [lat_median, lon_median],  # Center
                    [lat_median + lat_range/3, lon_median],  # North
                    [lat_median - lat_range/3, lon_median],  # South
                    [lat_median, lon_median + lon_range/3],  # East
                    [lat_median, lon_median - lon_range/3],  # West
                    [lat_median + lat_range/5, lon_median + lon_range/5]   # NE
                ]
            else:
                # Default distribution pattern
                angle_step = 2 * 3.14159 / (big_warehouse_count - 1) if big_warehouse_count > 1 else 0
                radius_lat = lat_range / 3
                radius_lon = lon_range / 3
                
                big_warehouse_centers = [[lat_median, lon_median]]  # Center hub
                
                for i in range(1, big_warehouse_count):
                    angle = (i - 1) * angle_step
                    hub_lat = lat_median + radius_lat * np.cos(angle)
                    hub_lon = lon_median + radius_lon * np.sin(angle)
                    big_warehouse_centers.append([hub_lat, hub_lon])
        
        return big_warehouse_centers, big_warehouse_count
    
    except Exception as e:
        # Fallback to simple center placement if anything goes wrong
        print(f"Error in calculate_big_warehouse_locations: {e}")
        lat_center = df_filtered['order_lat'].mean()
        lon_center = df_filtered['order_long'].mean()
        return [[lat_center, lon_center]], 1
