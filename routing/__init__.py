"""
Routing Module - Delay-aware route optimization and rerouting decision engine

Features:
- OSMnx-based route calculation on OpenStreetMap
- Multiple alternate route generation
- Risk scoring based on predicted delays, distance, and conditions
- Agent-based decision making for rerouting recommendations

Usage:
    from routing.route_optimizer import RouteOptimizer
    from routing.decision_agent import RerouteDecisionAgent
    
    router = RouteOptimizer("Lisbon", "Portugal")
    router.load_network()
    routes = router.get_all_routes(41.14, -8.61, 41.16, -8.64, delay_probability=0.75)
"""

from .route_optimizer import RouteOptimizer, RouteInfo
from .decision_agent import RerouteDecisionAgent, RerouteDecision, RerouteRecommendation

__all__ = [
    "RouteOptimizer",
    "RouteInfo",
    "RerouteDecisionAgent",
    "RerouteDecision",
    "RerouteRecommendation"
]
