"""
Advanced Agent-Based Rerouting Decision Engine

This module uses intelligent agent logic to:
1. Detect congestion/delays in real-time
2. Proactively recommend rerouting
3. Track agent decisions over time
4. Provide confidence scores and explanations
5. Support multiple rerouting strategies
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class RerouteStrategy(Enum):
    """Rerouting strategies available to the agent"""
    FASTEST = "fastest"           # Minimize travel time
    SAFEST = "safest"             # Minimize delay risk
    BALANCED = "balanced"         # Balance time and safety
    AVOID_TRAFFIC = "avoid_traffic"  # Avoid congested areas
    MINIMIZE_DISTANCE = "minimize_distance"  # Shortest distance


class InterventionLevel(Enum):
    """How aggressive should the agent intervene"""
    PASSIVE = "passive"           # Only suggest, don't interrupt
    ACTIVE = "active"             # Proactively alert driver
    AGGRESSIVE = "aggressive"     # Force reroute for critical situations


@dataclass
class RerouteAction:
    """Represents a rerouting action the agent recommends"""
    action_id: str  # Unique identifier
    timestamp: datetime
    current_route_index: int
    recommended_route_index: int
    reason: str
    confidence: float  # 0.0-1.0
    potential_time_savings_min: float
    potential_risk_reduction: float
    strategy: RerouteStrategy
    intervention_level: InterventionLevel
    metrics: Dict = field(default_factory=dict)


@dataclass
class ReroutingDecision:
    """Decision output from the rerouting agent"""
    should_reroute: bool
    reroute_action: Optional[RerouteAction] = None
    alternative_routes: List[int] = field(default_factory=list)  # Indices of available routes
    reasoning: str = ""
    confidence: float = 0.0
    driver_notification: str = ""  # Message to display to driver
    urgency_level: str = "low"  # low, medium, high, critical


class ReroutingAgent:
    """
    Intelligent agent that makes real-time rerouting decisions.
    
    Decision Logic:
    1. Monitors delay probability and risk scores continuously
    2. Detects significant changes (congestion spikes)
    3. Evaluates alternative routes
    4. Recommends rerouting when conditions worsen
    5. Adapts strategy based on driver preferences
    """

    # Decision thresholds
    IMMEDIATE_REROUTE_THRESHOLD = 0.80  # Delay prob >= 80%
    STRONG_REROUTE_THRESHOLD = 0.65     # Delay prob >= 65%
    CONSIDER_REROUTE_THRESHOLD = 0.50   # Delay prob >= 50%
    
    # Time/distance improvement thresholds
    MIN_TIME_SAVINGS_FOR_REROUTE_MIN = 3.0  # At least 3 minutes savings
    MIN_RISK_REDUCTION_PERCENTAGE = 0.15    # At least 15% risk reduction

    def __init__(self, driver_id: str = None):
        self.driver_id = driver_id or "unknown"
        self.decision_history: List[RerouteAction] = []
        self.current_trip = None
        self.last_recommendation_time = None
        logger.info(f"ReroutingAgent initialized for driver {self.driver_id}")

    def decide_reroute(
        self,
        current_route: Dict,
        alternate_routes: List[Dict],
        delay_probability: float,
        weather: str = "clear",
        time_of_day: int = None,
        strategy: RerouteStrategy = RerouteStrategy.BALANCED
    ) -> ReroutingDecision:
        """
        Make a rerouting decision based on current conditions.
        
        Args:
            current_route: Current route dict with distance, time, risk_score
            alternate_routes: List of alternate route dicts
            delay_probability: Predicted delay probability (0.0-1.0)
            weather: Current weather conditions
            time_of_day: Hour of day (0-23)
            strategy: Rerouting strategy preference
            
        Returns:
            ReroutingDecision with recommendation and actions
        """
        
        # Detect if we should even consider rerouting
        if delay_probability < self.CONSIDER_REROUTE_THRESHOLD and weather == "clear":
            return ReroutingDecision(
                should_reroute=False,
                reasoning="Delay probability is low and weather is clear. Current route is optimal.",
                confidence=0.95,
                urgency_level="low"
            )

        # No alternatives available
        if not alternate_routes:
            return ReroutingDecision(
                should_reroute=False,
                reasoning="No alternate routes available.",
                confidence=1.0,
                urgency_level="low"
            )

        # ========== AGENT DECISION LOGIC ==========

        # Tier 1: CRITICAL - Immediate reroute needed
        if delay_probability >= self.IMMEDIATE_REROUTE_THRESHOLD:
            best_alt = self._find_best_route(
                current_route, alternate_routes, strategy
            )
            
            time_savings = current_route["estimated_time_min"] - best_alt["route"]["estimated_time_min"]
            risk_reduction = (current_route["risk_score"] - best_alt["route"]["risk_score"]) / max(current_route["risk_score"], 0.001)
            
            action = RerouteAction(
                action_id=f"reroute_{datetime.now().timestamp()}",
                timestamp=datetime.now(),
                current_route_index=0,
                recommended_route_index=best_alt["index"] + 1,
                reason=f"CRITICAL: Delay probability is {delay_probability:.0%}. Immediate reroute recommended.",
                confidence=0.95,
                potential_time_savings_min=max(time_savings, 0),
                potential_risk_reduction=max(risk_reduction, 0),
                strategy=strategy,
                intervention_level=InterventionLevel.AGGRESSIVE,
                metrics={
                    "current_risk": current_route["risk_score"],
                    "alternate_risk": best_alt["route"]["risk_score"],
                    "weather": weather
                }
            )
            
            self.decision_history.append(action)
            
            return ReroutingDecision(
                should_reroute=True,
                reroute_action=action,
                alternative_routes=[i for i in range(len(alternate_routes))],
                reasoning=f"CRITICAL ALERT: Severe delay risk ({delay_probability:.0%}). Will save ~{time_savings:.0f} min.",
                confidence=0.95,
                driver_notification=f"⚠️ CRITICAL: Heavy congestion/delays detected!\n✓ Recommended: Route {best_alt['index'] + 1}\n⏱️ Time saved: ~{time_savings:.0f} min",
                urgency_level="critical"
            )

        # Tier 2: STRONG - High-confidence reroute recommendation
        elif delay_probability >= self.STRONG_REROUTE_THRESHOLD:
            best_alt = self._find_best_route(
                current_route, alternate_routes, strategy
            )
            
            time_savings = current_route["estimated_time_min"] - best_alt["route"]["estimated_time_min"]
            risk_reduction = (current_route["risk_score"] - best_alt["route"]["risk_score"]) / max(current_route["risk_score"], 0.001)
            
            if time_savings >= self.MIN_TIME_SAVINGS_FOR_REROUTE_MIN or risk_reduction >= self.MIN_RISK_REDUCTION_PERCENTAGE:
                action = RerouteAction(
                    action_id=f"reroute_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    current_route_index=0,
                    recommended_route_index=best_alt["index"] + 1,
                    reason=f"HIGH RISK: Delay probability is {delay_probability:.0%}. Strong reroute recommendation.",
                    confidence=0.80,
                    potential_time_savings_min=max(time_savings, 0),
                    potential_risk_reduction=max(risk_reduction, 0),
                    strategy=strategy,
                    intervention_level=InterventionLevel.ACTIVE,
                    metrics={
                        "current_risk": current_route["risk_score"],
                        "alternate_risk": best_alt["route"]["risk_score"],
                        "weather": weather
                    }
                )
                
                self.decision_history.append(action)
                
                return ReroutingDecision(
                    should_reroute=True,
                    reroute_action=action,
                    alternative_routes=[i for i in range(len(alternate_routes))],
                    reasoning=f"HIGH RISK: Delay probability is {delay_probability:.0%}. Recommended route saves ~{time_savings:.0f} min.",
                    confidence=0.80,
                    driver_notification=f"🚨 HIGH RISK: Moderate congestion expected\n✓ Recommended: Route {best_alt['index'] + 1}\n⏱️ Time saved: ~{time_savings:.0f} min",
                    urgency_level="high"
                )

        # Tier 3: MODERATE - Proactive suggestion
        elif delay_probability >= self.CONSIDER_REROUTE_THRESHOLD:
            best_alt = self._find_best_route(
                current_route, alternate_routes, strategy
            )
            
            time_savings = current_route["estimated_time_min"] - best_alt["route"]["estimated_time_min"]
            risk_reduction = (current_route["risk_score"] - best_alt["route"]["risk_score"]) / max(current_route["risk_score"], 0.001)
            
            if time_savings >= self.MIN_TIME_SAVINGS_FOR_REROUTE_MIN:
                return ReroutingDecision(
                    should_reroute=True,
                    alternative_routes=[best_alt["index"]],
                    reasoning=f"MODERATE RISK: Consider alternative route to save ~{time_savings:.0f} min.",
                    confidence=0.65,
                    driver_notification=f"💡 TIP: Consider Route {best_alt['index'] + 1} to save ~{time_savings:.0f} min",
                    urgency_level="medium"
                )

        # Tier 4: Weather/Traffic Alert
        elif weather in ["rain", "storm"] or (time_of_day and (8 <= time_of_day <= 10 or 17 <= time_of_day <= 19)):
            best_alt = self._find_best_route(
                current_route, alternate_routes, strategy
            )
            
            return ReroutingDecision(
                should_reroute=False,
                reasoning=f"Weather/rush hour detected ({weather}, hour {time_of_day}). Monitor situation.",
                confidence=0.50,
                driver_notification=f"ℹ️ {weather.upper()} conditions / Rush hour. Drive carefully.",
                urgency_level="low"
            )

        # Default: Stay on current route
        return ReroutingDecision(
            should_reroute=False,
            reasoning="Current route is optimal. Delay risk is acceptable.",
            confidence=0.70,
            urgency_level="low"
        )

    def _find_best_route(
        self,
        current_route: Dict,
        alternate_routes: List[Dict],
        strategy: RerouteStrategy
    ) -> Optional[Dict]:
        """Find the best alternate route based on strategy."""
        best = None
        best_score = float("inf")

        for idx, alt in enumerate(alternate_routes):
            if strategy == RerouteStrategy.FASTEST:
                score = alt["estimated_time_min"]
            elif strategy == RerouteStrategy.SAFEST:
                score = alt["risk_score"]
            elif strategy == RerouteStrategy.MINIMIZE_DISTANCE:
                score = alt["distance_km"]
            else:  # BALANCED
                # 60% risk, 40% time
                primary_time = current_route["estimated_time_min"] or 1.0
                score = alt["risk_score"] * 0.6 + (alt["estimated_time_min"] / primary_time) * 0.4

            if score < best_score:
                best = {
                    "index": idx,
                    "route": alt,
                    "score": score
                }
                best_score = score

        return best

    def get_agent_status(self) -> Dict:
        """Get the agent's current status and decision history."""
        return {
            "driver_id": self.driver_id,
            "total_decisions": len(self.decision_history),
            "reroutes_recommended": sum(1 for d in self.decision_history if hasattr(d, 'should_reroute')),
            "last_decision": self.decision_history[-1] if self.decision_history else None,
            "decision_history_count": len(self.decision_history)
        }
