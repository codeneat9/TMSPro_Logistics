"""
Extended dashboard test with different trip scenarios
"""
import os
import pytest
import requests
import time

BASE_URL = "http://127.0.0.1:8000"
LIVE_DASHBOARD_TESTS = os.getenv("ENABLE_LIVE_DASHBOARD_TESTS", "false").lower() == "true"


def _require_live_dashboard() -> None:
    """Skip unless live dashboard tests are explicitly enabled and reachable."""
    if not LIVE_DASHBOARD_TESTS:
        pytest.skip("Live dashboard tests are disabled; set ENABLE_LIVE_DASHBOARD_TESTS=true to run")

    try:
        requests.get(f"{BASE_URL}/dashboard/health", timeout=2)
    except requests.RequestException as exc:
        pytest.skip(f"Dashboard backend not reachable at {BASE_URL}: {exc}")

def test_dashboard_health():
    """Test dashboard health endpoint"""
    _require_live_dashboard()
    print("\n" + "="*70)
    print("Test 1: Dashboard Health Check")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_dashboard_short_trip():
    """Test with short trip in Lisbon (2.5 km)"""
    _require_live_dashboard()
    print("\n" + "="*70)
    print("Test 2: Short Trip (2.5 km) - Lisbon City Center")
    print("="*70)
    
    # Real Lisbon coordinates
    # Praça do Comércio ~> Terreiro do Paço (~2 km away)
    trip_data = {
        "trip_id": "TEST-SHORT-001",
        "driver_id": "DRV-001",
        "pickup_lat": 38.7075,   # Praça do Comércio
        "pickup_lon": -9.1371,
        "destination_lat": 38.7155,  # Terreiro do Paço
        "destination_lon": -9.1319,
        "pickup_timestamp": int(time.time()),
        "taxi_id": 20000589,
        "call_type": "B",
        "day_type": "A",
        "temperature_2m": 22.0,
        "precipitation": 2.5,
        "windspeed_10m": 5.0,
        "strategy": "balanced"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/dashboard/plan-trip", json=trip_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nPrediction:")
            print(f"  Delay Probability: {data.get('delay_probability', 0)*100:.1f}%")
            print(f"\nPrimary Route:")
            if data.get('primary_route'):
                print(f"  Distance: {data['primary_route'].get('distance_km', 0):.2f} km")
                print(f"  Time: {data['primary_route'].get('estimated_time_min', 0):.1f} min")
                print(f"  Waypoints: {data['primary_route'].get('num_waypoints', 0)}")
            print(f"\nAgent Decision:")
            print(f"  Should Reroute: {data.get('should_reroute', False)}")
            print(f"  Urgency: {data.get('urgency_level', 'unknown')}")
            assert "delay_probability" in data
        else:
            print(f"Error: {response.text}")
            assert response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_dashboard_medium_trip():
    """Test with medium trip in Lisbon (8 km)"""
    _require_live_dashboard()
    print("\n" + "="*70)
    print("Test 3: Medium Trip (8 km) - Lisbon")
    print("="*70)
    
    # Real Lisbon coordinates
    # Terreiro do Paço → Belém Tower (~8 km east)
    trip_data = {
        "trip_id": "TEST-MEDIUM-001",
        "driver_id": "DRV-002",
        "pickup_lat": 38.7167,  # Terreiro do Paço
        "pickup_lon": -9.1344,
        "destination_lat": 38.6620,  # Belém Tower
        "destination_lon": -9.2155,
        "pickup_timestamp": int(time.time()),
        "taxi_id": 20000590,
        "call_type": "A",
        "day_type": "B",
        "temperature_2m": 20.0,
        "precipitation": 0.0,
        "windspeed_10m": 3.0,
        "strategy": "fastest"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/dashboard/plan-trip", json=trip_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nPrediction:")
            print(f"  Delay Probability: {data.get('delay_probability', 0)*100:.1f}%")
            print(f"\nPrimary Route:")
            if data.get('primary_route'):
                print(f"  Distance: {data['primary_route'].get('distance_km', 0):.2f} km")
                print(f"  Time: {data['primary_route'].get('estimated_time_min', 0):.1f} min")
                print(f"  Waypoints: {data['primary_route'].get('num_waypoints', 0)}")
            print(f"\nAlternate Routes: {len(data.get('alternate_routes', []))}")
            for i, route in enumerate(data.get('alternate_routes', []), 1):
                print(f"  Route {i}: {route.get('distance_km', 0):.2f} km, {route.get('estimated_time_min', 0):.1f} min")
            print(f"\nAgent Decision:")
            print(f"  Should Reroute: {data.get('should_reroute', False)}")
            print(f"  Urgency: {data.get('urgency_level', 'unknown')}")
            assert "delay_probability" in data
        else:
            print(f"Error: {response.text}")
            assert response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_dashboard_high_delay():
    """Test with high delay prediction scenario"""
    _require_live_dashboard()
    print("\n" + "="*70)
    print("Test 4: High Delay Scenario (Rush Hour Route)")
    print("="*70)
    
    # Real Lisbon coordinates  
    # Rossio → Cascais (~25 km)
    trip_data = {
        "trip_id": "TEST-DELAY-001",
        "driver_id": "DRV-003",
        "pickup_lat": 38.7136,
        "pickup_lon": -9.1424,
        "destination_lat": 38.6977,
        "destination_lon": -9.4153,
        "pickup_timestamp": int(time.time()),
        "taxi_id": 20000591,
        "call_type": "A",
        "day_type": "B",
        "temperature_2m": 25.0,
        "precipitation": 5.0,  # Heavy rain
        "windspeed_10m": 15.0,  # Strong wind
        "strategy": "safest"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/dashboard/plan-trip", json=trip_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nPrediction:")
            print(f"  Delay Probability: {data.get('delay_probability', 0)*100:.1f}%")
            print(f"\nAgent Decision:")
            print(f"  Should Reroute: {data.get('should_reroute', False)}")
            print(f"  Urgency: {data.get('urgency_level', 'unknown')}")
            print(f"  Recommendation: {data.get('driver_notification', '')}")
            assert "delay_probability" in data
        else:
            print(f"Error: {response.text}")
            assert response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PRODUCTION DASHBOARD EXTENDED TEST")
    print("="*70)
    
    results = []
    test_functions = [
        ("Health Check", test_dashboard_health),
        ("Short Trip", test_dashboard_short_trip),
        ("Medium Trip", test_dashboard_medium_trip),
        ("High Delay", test_dashboard_high_delay),
    ]

    for test_name, test_func in test_functions:
        try:
            test_func()
            results.append((test_name, True))
        except Exception:
            results.append((test_name, False))
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*70)
    print("DASHBOARD ACCESS:")
    print("="*70)
    print("1. Production Dashboard: http://127.0.0.1:8000/dashboard")
    print("2. Prototype UI: http://127.0.0.1:8000/")
    print("3. API Docs: http://127.0.0.1:8000/docs")
    print("="*70)
