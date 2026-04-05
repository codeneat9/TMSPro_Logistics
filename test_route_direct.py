"""
Direct route optimizer test to debug routing issues
"""
from routing.route_optimizer import RouteOptimizer
import time

def test_route_optimizer():
    """Test route optimizer directly"""
    print("="*70)
    print("ROUTE OPTIMIZER DEBUG TEST")
    print("="*70)
    
    # Initialize optimizer
    optimizer = RouteOptimizer(city="Lisbon", country="Portugal")
    
    print("\n1. Loading network...")
    start = time.time()
    success = optimizer.load_network(network_type="drive")
    elapsed = time.time() - start
    print(f"   Network loaded: {success} ({elapsed:.1f}s)")
    
    if not success:
        print("   ERROR: Failed to load network!")
        return
    
    if optimizer.G:
        print(f"   Network stats: {len(optimizer.G.nodes)} nodes, {len(optimizer.G.edges)} edges")
    
    # Test case 1: Short trip
    print("\n2. Testing short trip (2 km)...")
    pickup_lat, pickup_lon = 38.7075, -9.1371   # Praça do Comércio
    dest_lat, dest_lon = 38.7155, -9.1319  # Terreiro do Paço
    
    print(f"   Origin: ({pickup_lat}, {pickup_lon})")
    print(f"   Destination: ({dest_lat}, {dest_lon})")
    
    start = time.time()
    routes = optimizer.get_all_routes(
        origin_lat=pickup_lat,
        origin_lon=pickup_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        num_alternatives=2,
        delay_probability=0.15
    )
    elapsed = time.time() - start
    print(f"   Route calculation took {elapsed:.1f}s")
    
    if routes:
        print(f"   Primary route:")
        pr = routes.get('primary_route', {})
        print(f"     - Distance: {pr.get('distance_km', 0):.2f} km")
        print(f"     - Time: {pr.get('estimated_time_min', 0):.1f} min")
        print(f"     - Waypoints: {pr.get('num_waypoints', 0)}")
        print(f"     - Risk Score: {pr.get('risk_score', 0):.3f}")
        
        print(f"   Alternate routes: {len(routes.get('alternate_routes', []))}")
        for i, route in enumerate(routes.get('alternate_routes', []), 1):
            print(f"     Route {i}: {route.get('distance_km', 0):.2f} km, {route.get('estimated_time_min', 0):.1f} min")
    
    # Test case 2: Longer trip
    print("\n3. Testing medium trip (9 km)...")
    pickup_lat2, pickup_lon2 = 38.7167, -9.1344  # Terreiro do Paço
    dest_lat2, dest_lon2 = 38.6620, -9.2155  # Belém Tower
    
    print(f"   Origin: ({pickup_lat2}, {pickup_lon2})")
    print(f"   Destination: ({dest_lat2}, {dest_lon2})")
    
    start = time.time()
    routes2 = optimizer.get_all_routes(
        origin_lat=pickup_lat2,
        origin_lon=pickup_lon2,
        dest_lat=dest_lat2,
        dest_lon=dest_lon2,
        num_alternatives=2,
        delay_probability=0.20
    )
    elapsed = time.time() - start
    print(f"   Route calculation took {elapsed:.1f}s")
    
    if routes2:
        print(f"   Primary route:")
        pr2 = routes2.get('primary_route', {})
        print(f"     - Distance: {pr2.get('distance_km', 0):.2f} km")
        print(f"     - Time: {pr2.get('estimated_time_min', 0):.1f} min")
        print(f"     - Waypoints: {pr2.get('num_waypoints', 0)}")
        print(f"     - Risk Score: {pr2.get('risk_score', 0):.3f}")
        
        if pr2.get('coordinates'):
            print(f"   First 3 waypoints:")
            for i, coord in enumerate(pr2.get('coordinates', [])[:3]):
                print(f"     {i+1}. {coord}")

if __name__ == "__main__":
    test_route_optimizer()
