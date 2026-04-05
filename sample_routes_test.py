"""
Sample Routes Test - TMS Dashboard
Shows real coordinates and expected route results
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

# Sample routes in Lisbon with real destinations
SAMPLE_ROUTES = [
    {
        "name": "Route 1: Downtown to Belém Tower (8 km)",
        "pickup_lat": 38.7075,
        "pickup_lon": -9.1371,
        "dest_lat": 38.6620,
        "dest_lon": -9.2155,
        "weather": {"temp": 22.0, "precip": 0.0, "wind": 5.0}
    },
    {
        "name": "Route 2: Short Downtown Trip (1.3 km)",
        "pickup_lat": 38.7075,
        "pickup_lon": -9.1371,
        "dest_lat": 38.7155,
        "dest_lon": -9.1319,
        "weather": {"temp": 20.0, "precip": 0.0, "wind": 3.0}
    },
    {
        "name": "Route 3: Airport to City Center (7 km)",
        "pickup_lat": 38.6815,
        "pickup_lon": -9.1357,
        "dest_lat": 38.7136,
        "dest_lon": -9.1424,
        "weather": {"temp": 21.0, "precip": 0.0, "wind": 4.0}
    },
    {
        "name": "Route 4: Long Trip - Downtown to Cascais (30 km)",
        "pickup_lat": 38.7136,
        "pickup_lon": -9.1424,
        "dest_lat": 38.6977,
        "dest_lon": -9.4153,
        "weather": {"temp": 23.0, "precip": 2.0, "wind": 8.0}
    },
    {
        "name": "Route 5: Parque das Nações to Belém (4 km)",
        "pickup_lat": 38.7633,
        "pickup_lon": -9.0913,
        "dest_lat": 38.6620,
        "dest_lon": -9.2155,
        "weather": {"temp": 22.0, "precip": 0.0, "wind": 5.0}
    }
]

print("="*80)
print(" SAMPLE ROUTES - LISBON TAXI NAVIGATION SYSTEM")
print("="*80)

print("\n📍 SAMPLE COORDINATES TO ENTER IN DASHBOARD:\n")

for i, route in enumerate(SAMPLE_ROUTES, 1):
    print(f"\n{i}. {route['name']}")
    print(f"   ┌─ Pickup: {route['pickup_lat']}, {route['pickup_lon']}")
    print(f"   └─ Destination: {route['dest_lat']}, {route['dest_lon']}")

print("\n" + "="*80)
print(" TESTING ROUTES - LIVE RESULTS")
print("="*80)

for i, route in enumerate(SAMPLE_ROUTES, 1):
    print(f"\n\n📍 Testing Route {i}: {route['name']}")
    print("-" * 80)
    
    trip_data = {
        "trip_id": f"SAMPLE-{i}",
        "driver_id": "DRIVER-TEST",
        "pickup_lat": route["pickup_lat"],
        "pickup_lon": route["pickup_lon"],
        "destination_lat": route["dest_lat"],
        "destination_lon": route["dest_lon"],
        "pickup_timestamp": int(time.time()),
        "taxi_id": 20000589,
        "call_type": "A",
        "day_type": "B",
        "temperature_2m": route["weather"]["temp"],
        "precipitation": route["weather"]["precip"],
        "windspeed_10m": route["weather"]["wind"],
        "strategy": "balanced"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/dashboard/plan-trip", json=trip_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Primary route
            primary = data.get("primary_route", {})
            delay_prob = data.get("delay_probability", 0) * 100
            risk_score = data.get("risk_score", 0) * 100
            
            print(f"\n  ✓ STATUS: Success")
            print(f"\n  📊 PREDICTION:")
            print(f"     • Delay Risk: {delay_prob:.1f}%")
            print(f"     • Risk Score: {risk_score:.0f}%")
            
            print(f"\n  🛣️  PRIMARY ROUTE:")
            print(f"     • Distance: {primary.get('distance_km', 0):.2f} km")
            print(f"     • Est. Time: {primary.get('estimated_time_min', 0):.1f} minutes")
            print(f"     • Waypoints: {primary.get('num_waypoints', 0)} points")
            
            # Alternates
            alternates = data.get("alternate_routes", [])
            if alternates:
                print(f"\n  📍 ALTERNATIVE ROUTES:")
                for j, alt in enumerate(alternates, 1):
                    print(f"     Route {j}: {alt.get('distance_km', 0):.2f} km, {alt.get('estimated_time_min', 0):.1f} min")
            
            # Agent decision
            print(f"\n  🤖 AI AGENT DECISION:")
            print(f"     • Reroute: {'YES ⚠️' if data.get('should_reroute') else 'NO ✓'}")
            print(f"     • Urgency: {data.get('urgency_level', 'UNKNOWN').upper()}")
            print(f"     • Message: {data.get('driver_notification', 'N/A')}")
            
        else:
            print(f"  ✗ ERROR: Status {response.status_code}")
            print(f"  Response: {response.text[:100]}")
            
    except Exception as e:
        print(f"  ✗ ERROR: {str(e)}")

print("\n\n" + "="*80)
print(" MANUAL ENTRY INSTRUCTIONS")
print("="*80)

print("""
TO TEST THE DASHBOARD:

1. Open: http://127.0.0.1:8000/dashboard

2. Choose a sample route from above

3. Enter coordinates:
   • Pickup Latitude (e.g., 38.7075)
   • Pickup Longitude (e.g., -9.1371)
   • Destination Latitude (e.g., 38.6620)
   • Destination Longitude (e.g., -9.2155)

4. Press ENTER after each coordinate

5. Routes will AUTO-DISPLAY on the map:
   • Blue solid line = Primary route
   • Gray dashed lines = Alternatives
   • Blue & Purple circles = Start & End points

6. Check results:
   • Distance in km
   • Estimated time in minutes
   • Delay probability
   • AI agent recommendation
   • Color-coded urgency alert

QUICK TEST (Use Presets):
• Click "📌 Praça do Comércio" button
• Click "🏰 Belém Tower" button  
• Routes instantly display on map!
""")

print("="*80)
print(" LISBON LANDMARKS REFERENCE")
print("="*80)

landmarks = [
    ("Praça do Comércio (Downtown)", 38.7075, -9.1371),
    ("Terreiro do Paço (Harbor Front)", 38.7167, -9.1344),
    ("Belém Tower", 38.6620, -9.2155),
    ("Jerónimos Monastery", 38.6614, -9.2041),
    ("Cristo Rei (Christ the King)", 38.6788, -9.1969),
    ("Airport Terminal 1", 38.6815, -9.1357),
    ("Parque das Nações", 38.7633, -9.0913),
    ("Museu Artes Decorativas", 38.7190, -9.1383),
    ("Castelo de São Jorge", 38.7145, -9.1347),
    ("Rossio Square", 38.7136, -9.1424),
]

print("\nLisbon Coordinates Reference:")
for name, lat, lon in landmarks:
    print(f"  • {name:.<40} {lat}, {lon}")

print("\n" + "="*80)
