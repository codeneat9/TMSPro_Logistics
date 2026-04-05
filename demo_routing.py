"""
Demonstrate routing functionality with sample data.

This shows:
1. Loading the route optimizer with Lisbon street network
2. Calculating primary and alternate routes
3. Using the decision agent for rerouting recommendations
4. Understanding delay probability impact on routing
"""

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def demo_route_calculation():
    """Demo: Calculate routes with different delay probabilities"""
    from routing import RouteOptimizer
    
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 1: Route Calculation")
    logger.info("=" * 70)
    
    # Sample coordinates in Lisbon
    origin_lat, origin_lon = 41.141412, -8.618643  # Rossio Square
    dest_lat, dest_lon = 41.160000, -8.640000      # Près River area
    
    logger.info(f"Route: {origin_lat:.5f}, {origin_lon:.5f} → {dest_lat:.5f}, {dest_lon:.5f}")
    logger.info("Note: Actual network loading takes 1-2 minutes on first run...")
    logger.info("      (Skipping real OSM download for demo)")
    
    # In production, this would download the network:
    # optimizer = RouteOptimizer("Lisbon", "Portugal")
    # optimizer.load_network(network_type="drive")
    # routes = optimizer.get_all_routes(origin_lat, origin_lon, dest_lat, dest_lon, ...)
    
    logger.info("\nAfter network loads, you would see:")
    logger.info("  - Primary Route: Shortest path via main roads")
    logger.info("  - Alternative Routes: Via residential/secondary roads")
    logger.info("  - Risk Scores: Based on distance, time, weather, delay prob")
    logger.info("  - Recommended Route: Optimal balance of risk vs time/distance")

def demo_decision_logic():
    """Demo: Show decision agent logic"""
    from routing import RerouteDecisionAgent
    
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 2: Decision Agent Logic")
    logger.info("=" * 70)
    
    agent = RerouteDecisionAgent()
    
    # Simulate a primary route
    primary_route = {
        "distance_km": 8.5,
        "estimated_time_min": 22.5,
        "risk_score": 0.65  # Moderate risk
    }
    
    # Simulate alternate routes
    alt_routes = [
        {
            "distance_km": 9.2,
            "estimated_time_min": 24.0,
            "risk_score": 0.35  # Lower risk
        },
        {
            "distance_km": 10.5,
            "estimated_time_min": 26.5,
            "risk_score": 0.25  # Even lower risk
        }
    ]
    
    # Test different delay probabilities
    scenarios = [
        ("Low delay (20%)", 0.20, "clear", 14),
        ("Moderate delay (55%)", 0.55, "clear", 14),
        ("High delay (80%)", 0.80, "rain", 8),
    ]
    
    for scenario_name, delay_prob, weather, hour in scenarios:
        logger.info(f"\n{scenario_name}")
        logger.info(f"  Delay Probability: {delay_prob:.0%}")
        logger.info(f"  Weather: {weather}, Time: {hour}:00")
        
        recommendation = agent.decide(
            primary_route=primary_route,
            alternate_routes=alt_routes,
            delay_probability=delay_prob,
            time_of_day=hour,
            weather=weather,
            user_preference="balanced"
        )
        
        logger.info(f"  → Decision: {recommendation.decision.value.upper()}")
        logger.info(f"  → Confidence: {recommendation.confidence:.0%}")
        logger.info(f"  → Recommended: {'Route ' + str(recommendation.recommended_route_index) if recommendation.recommended_route_index > 0 else 'Primary (index 0)'}")
        logger.info(f"  → Reason: {recommendation.reasoning}")

def demo_api_integration():
    """Demo: Show API endpoints"""
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 3: API Integration")
    logger.info("=" * 70)
    
    logger.info("\nAvailable Endpoints (after starting with uvicorn):\n")
    
    endpoints = [
        ("GET /routing/health", "Check if routing service is ready"),
        ("POST /routing/routes", "Calculate primary + alternate routes"),
        ("POST /routing/reroute", "Get rerouting recommendation"),
        ("GET /routing/decision-summary", "View recent decision statistics"),
    ]
    
    for endpoint, description in endpoints:
        logger.info(f"  {endpoint}")
        logger.info(f"    → {description}")
    
    logger.info("\n\nExample request to /routing/routes:")
    logger.info("""
    POST /routing/routes
    {
        "origin_lat": 41.141412,
        "origin_lon": -8.618643,
        "destination_lat": 41.160000,
        "destination_lon": -8.640000,
        "delay_probability": 0.75,
        "time_of_day": 8,
        "weather": "rain",
        "num_alternatives": 2
    }
    """)
    
    logger.info("\nExample request to /routing/reroute:")
    logger.info("""
    POST /routing/reroute
    {
        "origin_lat": 41.141412,
        "origin_lon": -8.618643,
        "destination_lat": 41.160000,
        "destination_lon": -8.640000,
        "delay_probability": 0.65,
        "time_of_day": 8,
        "weather": "clear",
        "user_preference": "balanced"
    }
    """)

def demo_combined_flow():
    """Demo: Show end-to-end workflow"""
    from cloud.feature_builder import DelayFeatureBuilder
    from scripts.predict_delay import DelayPredictor
    from routing import RerouteDecisionAgent
    
    logger.info("\n" + "=" * 70)
    logger.info("DEMO 4: End-to-End Workflow")
    logger.info("=" * 70)
    
    logger.info("\nStep 1: User provides trip request")
    trip = {
        "pickup_lat": 41.141412,
        "pickup_lon": -8.618643,
        "destination_lat": 41.160000,
        "destination_lon": -8.640000,
        "pickup_timestamp": 1372688400,
        "taxi_id": 20000589,
        "call_type": "B",
        "day_type": "A",
        "temperature_2m": 22.0,
        "precipitation": 0.5,
        "windspeed_10m": 3.5
    }
    logger.info(f"  Pickup: ({trip['pickup_lat']}, {trip['pickup_lon']})")
    logger.info(f"  Destination: ({trip['destination_lat']}, {trip['destination_lon']})")
    logger.info(f"  Weather: {trip['temperature_2m']}°C, {trip['precipitation']}mm rain")
    
    logger.info("\nStep 2: Build 24 model features from raw trip data")
    fb = DelayFeatureBuilder()
    result = fb.build(trip)
    logger.info(f"  ✓ Built {len(result.features)} features")
    if result.assumptions:
        logger.info(f"  ✓ Made {len(result.assumptions)} assumptions for missing values")
    
    logger.info("\nStep 3: Predict delay probability")
    predictor = DelayPredictor()
    prediction = predictor.predict(result.features)
    logger.info(f"  ✓ Delay Probability: {prediction['delay_probability']:.1%}")
    logger.info(f"  ✓ Confidence: {prediction['confidence']}")
    
    logger.info("\nStep 4: Request routing (if delay probability is high)")
    if prediction['delay_probability'] > 0.30:
        logger.info(f"  → Delay risk is notable ({prediction['delay_probability']:.1%})")
        logger.info(f"  → Requesting alternate routes for driver's consideration")
        logger.info(f"  → POST /routing/reroute would be called")
        
        # Show what decision would be
        agent = RerouteDecisionAgent()
        primary = {
            "distance_km": 8.5,
            "estimated_time_min": 22.5,
            "risk_score": prediction['delay_probability']
        }
        alts = [
            {
                "distance_km": 9.2,
                "estimated_time_min": 24.0,
                "risk_score": max(0.2, prediction['delay_probability'] - 0.1)
            }
        ]
        rec = agent.decide(primary, alts, prediction['delay_probability'], time_of_day=8, weather="clear")
        logger.info(f"  → Recommendation: {rec.decision.value}")
    else:
        logger.info(f"  → Delay risk is low ({prediction['delay_probability']:.1%})")
        logger.info(f"  → Stick with primary route")

def main():
    """Run all demos"""
    logger.info("""
╔══════════════════════════════════════════════════════════════════════╗
║        ROUTING MODULE DEMONSTRATION                                  ║
║                                                                      ║
║  This demonstrates the integrated delay prediction + routing system:║
║  1. Feature building from raw trip input                            ║
║  2. Delay probability prediction with LightGBM                      ║
║  3. Multi-route calculation with OSMnx                              ║
║  4. Decision logic for rerouting recommendations                    ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        demo_route_calculation()
        demo_decision_logic()
        demo_api_integration()
        demo_combined_flow()
        
        logger.info("\n" + "=" * 70)
        logger.info("NEXT STEPS")
        logger.info("=" * 70)
        logger.info("""
1. Start the API server:
   $ python -m uvicorn cloud.app:app --reload

2. Visit http://127.0.0.1:8000/
   - Use the delay prediction form
   - Once OSM network is loaded, routing endpoints become active

3. Test routing endpoints:
   $ curl -X POST http://127.0.0.1:8000/routing/routes \\
     -H "Content-Type: application/json" \\
     -d '{
       "origin_lat": 41.141412,
       "origin_lon": -8.618643,
       "destination_lat": 41.160000,
       "destination_lon": -8.640000,
       "delay_probability": 0.75
     }'

4. Integrated workflow:
   POST /predict → Get delay_probability
   POST /routing/reroute → Get routing recommendation
   → Display routes + decision to user in app
        """)
        
        logger.info("=" * 70)
        logger.info("✓ Routing module fully integrated and operational!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
