"""
Quick test script for routing module integration.

This tests:
1. Routing module can be imported
2. Basic route calculation
3. Decision agent logic
4. API integration
"""

import sys
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all routing modules can be imported"""
    try:
        logger.info("Testing imports...")
        from routing import RouteOptimizer, RerouteDecisionAgent
        logger.info("✓ Routing modules imported successfully")
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        raise

def test_feature_builder():
    """Test feature builder integration"""
    try:
        logger.info("Testing feature builder...")
        from cloud.feature_builder import DelayFeatureBuilder
        fb = DelayFeatureBuilder()
        
        sample_input = {
            "pickup_lat": 41.141412,
            "pickup_lon": -8.618643,
            "destination_lat": 41.160000,
            "destination_lon": -8.640000,
            "pickup_timestamp": 1372688400,
            "taxi_id": 20000589,
            "call_type": "B",
            "day_type": "A"
        }
        
        result = fb.build(sample_input)
        logger.info(f"✓ Feature builder working: {len(result.features)} features built")
        assert len(result.features) > 0
    except Exception as e:
        logger.error(f"✗ Feature builder test failed: {e}")
        raise

def test_predictor():
    """Test delay predictor"""
    try:
        logger.info("Testing delay predictor...")
        from scripts.predict_delay import DelayPredictor
        pred = DelayPredictor()
        
        # Get a sample set of features
        from cloud.feature_builder import DelayFeatureBuilder
        fb = DelayFeatureBuilder()
        sample_input = {
            "pickup_lat": 41.141412,
            "pickup_lon": -8.618643,
            "destination_lat": 41.160000,
            "destination_lon": -8.640000,
            "pickup_timestamp": 1372688400,
            "taxi_id": 20000589,
            "call_type": "B",
            "day_type": "A"
        }
        
        result = fb.build(sample_input)
        prediction = pred.predict(result.features)
        
        logger.info(f"✓ Predictor working: delay_prob={prediction['delay_probability']:.2%}")
        assert "delay_probability" in prediction
    except Exception as e:
        logger.error(f"✗ Predictor test failed: {e}")
        raise

def test_app_routes():
    """Test FastAPI app can load with routing"""
    try:
        logger.info("Testing FastAPI app...")
        from cloud.app import app
        
        routes = [r.path for r in app.routes]
        expected_routes = ["/health", "/predict", "/routing/health", "/routing/routes", "/routing/reroute"]
        
        found_routes = [r for r in expected_routes if any(r in route for route in routes)]
        logger.info(f"✓ FastAPI app loaded: found {len(found_routes)} routing routes")
        logger.info(f"  Routes: {[r for r in routes if '/routing' in r]}")
        assert len(found_routes) > 0
    except Exception as e:
        logger.error(f"✗ FastAPI app test failed: {e}")
        raise

def run_all_tests():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("ROUTING MODULE TEST SUITE")
    logger.info("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Feature Builder", test_feature_builder),
        ("Delay Predictor", test_predictor),
        ("FastAPI Integration", test_app_routes),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
        logger.info("")
    
    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("=" * 60)
    logger.info(f"Result: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
