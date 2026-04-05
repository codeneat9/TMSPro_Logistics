"""
Test the complete production dashboard workflow
"""
import requests
import json
from datetime import datetime

print("\n" + "=" * 70)
print("PRODUCTION DASHBOARD TEST")
print("=" * 70)

# Sample trip data
sample_trip = {
    "trip_id": "PROD-TRIP-001",
    "driver_id": "DRV-001", 
    "pickup_lat": 41.141412,
    "pickup_lon": -8.618643,
    "destination_lat": 41.160000,
    "destination_lon": -8.640000,
    "pickup_timestamp": int(datetime.now().timestamp()),
    "taxi_id": 20000589,
    "call_type": "B",
    "day_type": "A",
    "temperature_2m": 22.0,
    "precipitation": 2.5,  # Some rain
    "windspeed_10m": 5.0,
    "strategy": "balanced"
}

print("\nTest 1: Dashboard Health Check")
print("-" * 70)
try:
    r = requests.get("http://127.0.0.1:8000/dashboard/health", timeout=5)
    if r.status_code == 200:
        print("✓ Dashboard service is operational")
        print(f"  Response: {r.json()}")
    else:
        print(f"✗ Status {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n\nTest 2: Plan Trip (Consolidated Endpoint)")
print("-" * 70)
print(f"Sending trip request...")
print(f"  Trip ID: {sample_trip['trip_id']}")
print(f"  Pickup: ({sample_trip['pickup_lat']}, {sample_trip['pickup_lon']})")
print(f"  Destination: ({sample_trip['destination_lat']}, {sample_trip['destination_lon']})")
print(f"  Weather: {sample_trip['temperature_2m']}°C, {sample_trip['precipitation']}mm rain")

try:
    r = requests.post("http://127.0.0.1:8000/dashboard/plan-trip", 
                     json=sample_trip, 
                     timeout=180)
    
    if r.status_code == 200:
        data = r.json()
        print("\n✓ Trip planning successful!\n")
        
        print("PREDICTION RESULTS:")
        print(f"  Delay Probability: {data['predicted_delay']['probability']:.1%}")
        print(f"  Will be delayed: {data['predicted_delay']['is_delayed']}")
        print(f"  Confidence: {data['predicted_delay']['confidence']}")
        
        print("\nPRIMARY ROUTE:")
        pr = data['primary_route']
        print(f"  Distance: {pr['distance_km']:.1f} km")
        print(f"  Time: {pr['estimated_time_min']:.0f} minutes")
        print(f"  Risk Score: {pr['risk_score']:.3f}")
        
        print(f"\nALTERNATE ROUTES: {len(data['alternate_routes'])}")
        for i, alt in enumerate(data['alternate_routes'], 1):
            print(f"  Route {i}: {alt['distance_km']:.1f} km, {alt['estimated_time_min']:.0f} min, risk={alt['risk_score']:.3f}")
        
        print("\nAGENT DECISION:")
        rec = data['reroute_recommendation']
        print(f"  Should Reroute: {rec['should_reroute']}")
        print(f"  Recommendation: {rec['reasoning']}")
        print(f"  Urgency Level: {rec['urgency_level'].upper()}")
        print(f"  Confidence: {rec['confidence']:.0%}")
        
        if data['driver_alert']:
            print(f"\nDRIVER ALERT:")
            print(f"  {data['driver_alert']}")
        
    else:
        print(f"✗ Error {r.status_code}: {r.text}")
        
except requests.exceptions.Timeout:
    print("✗ Request timed out (OSM network still loading)")
except requests.exceptions.ConnectionError:
    print("✗ Connection refused - API server not running")
    print("  Start with: python -m uvicorn cloud.app:app --reload")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 70)
print("DASHBOARD ACCESS:")
print("=" * 70)
print("\n1. Open the production dashboard:")
print("   http://127.0.0.1:8000/dashboard")
print("\n2. Or access the original prototype:")
print("   http://127.0.0.1:8000/")
print("\n3. API Documentation:")
print("   http://127.0.0.1:8000/docs")
print("\n4. Endpoint tested:")
print("   POST /dashboard/plan-trip")
print("\n" + "=" * 70)
