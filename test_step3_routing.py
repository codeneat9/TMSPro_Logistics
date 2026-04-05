"""Test Step 3: Routing Decision with OSM Network Download"""
import requests
import time

print("Starting routing decision test...")
print("=" * 70)
print("\nNote: First request will download OSM street network (1-2 minutes)")
print("      Subsequent requests will be instant")
print("\n" + "=" * 70)

payload = {
    'origin_lat': 41.141412,
    'origin_lon': -8.618643,
    'destination_lat': 41.160000,
    'destination_lon': -8.640000,
    'delay_probability': 0.75,
    'time_of_day': 8,
    'weather': 'rain',
    'user_preference': 'balanced'
}

print("\nRequest payload:")
for key, value in payload.items():
    print(f"  {key}: {value}")

print("\n" + "=" * 70)
print("Sending request to /routing/reroute...")
print("(This may take 1-2 minutes on first run while downloading OSM network)")
print("=" * 70)

start_time = time.time()

try:
    r = requests.post(
        'http://127.0.0.1:8000/routing/reroute',
        json=payload,
        timeout=180  # 3 minute timeout for OSM download
    )
    elapsed = time.time() - start_time
    
    print(f"\n✓ Response received in {elapsed:.1f} seconds")
    print(f"Status Code: {r.status_code}\n")
    
    if r.status_code == 200:
        data = r.json()
        
        print("\n" + "=" * 70)
        print("RECOMMENDATION:")
        print("=" * 70)
        rec = data['recommendation']
        print(f"  Decision: {rec['decision'].upper()}")
        print(f"  Confidence: {rec['confidence']:.0%}")
        print(f"  Recommended Route Index: {rec['recommended_route_index']}")
        print(f"  Reasoning: {rec['reasoning']}")
        
        print("\n" + "=" * 70)
        print("ROUTES SUMMARY:")
        print("=" * 70)
        
        routes = data['routes']
        if routes['primary_route']:
            pr = routes['primary_route']
            print(f"\nPrimary Route:")
            print(f"  ├─ Distance: {pr['distance_km']} km")
            print(f"  ├─ Estimated Time: {pr['estimated_time_min']} minutes")
            print(f"  ├─ Risk Score: {pr['risk_score']:.3f}")
            print(f"  └─ Waypoints: {pr['num_waypoints']}")
        
        print(f"\nAlternate Routes ({len(routes['alternate_routes'])} found):")
        for i, alt in enumerate(routes['alternate_routes'], 1):
            print(f"\n  Alternative Route {i}:")
            print(f"  ├─ Distance: {alt['distance_km']} km")
            print(f"  ├─ Estimated Time: {alt['estimated_time_min']} minutes")
            print(f"  ├─ Risk Score: {alt['risk_score']:.3f}")
            print(f"  └─ Waypoints: {alt['num_waypoints']}")
        
        if routes['recommended_route']:
            rec_route = routes['recommended_route']
            print(f"\n" + "=" * 70)
            print("RECOMMENDED ROUTE (Best balance of risk vs time):")
            print("=" * 70)
            print(f"  Route Name: {rec_route['route_name']}")
            print(f"  Distance: {rec_route['distance_km']} km")
            print(f"  Estimated Time: {rec_route['estimated_time_min']} minutes")
            print(f"  Risk Score: {rec_route['risk_score']:.3f}")
            print(f"  Waypoints: {rec_route['num_waypoints']}")
        
        print("\n" + "=" * 70)
        print("✓ TEST SUCCESSFUL!")
        print("=" * 70)
    else:
        print(f"✗ Error: {r.status_code}")
        print(f"Response: {r.text}")

except requests.exceptions.Timeout:
    print("\n✗ Request timed out")
    print("   The OSM network download took too long or failed")
    print("   This sometimes happens if:")
    print("     - Your internet connection is slow")
    print("     - OSM servers are slow")
    print("   Try again in a moment!")

except requests.exceptions.ConnectionError:
    print("\n✗ Connection refused - API server is not running!")
    print("   Start the server with:")
    print("   python -m uvicorn cloud.app:app --reload")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
