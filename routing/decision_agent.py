"""
Agent-Based Decision Module for Route Optimization

This module uses decision logic to determine whether to suggest rerouting
based on delay predictions, time saved, and risk-reward analysis.

Decision Rules:
1. If delay_prob >= 0.70 AND distance savings exist -> Reroute
2. If delay_prob >= 0.50 AND time savings >= 5 mins -> Consider reroute
3. If delay_prob < 0.30 -> Stick with primary route
4. If weather/traffic risk high AND alternate lower risk -> Suggest change
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class RerouteDecision(Enum):
    """Decision outcomes"""
    STICK_PRIMARY = "stick_primary"  # Keep current route
    STRONG_REROUTE = "strong_reroute"  # High confidence, definitely reroute
    WEAK_REROUTE = "weak_reroute"  # Marginal benefit, optional reroute
    CONDITIONAL_REROUTE = "conditional_reroute"  # Reroute if user prefers time/safety


@dataclass
class RerouteRecommendation:
    """Output of the decision module"""
    decision: RerouteDecision
    recommended_route_index: int  # 0 = primary, 1+ = alternatives
    confidence: float  # 0.0-1.0
    reasoning: str  # Explanation of the decision
    metrics: Dict = None  # Detailed decision breakdown

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "recommended_route_index": self.recommended_route_index,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "metrics": self.metrics or {}
        }


class RerouteDecisionAgent:
    """
    Decision agent for route optimization.
    Uses heuristic rules to determine when rerouting is beneficial.
    """

    # Decision thresholds
    STRONG_DELAY_THRESHOLD = 0.70  # High delay probability
    WEAK_DELAY_THRESHOLD = 0.50  # Moderate delay probability
    MIN_TIME_SAVINGS_MIN = 5.0  # Minimum time savings in minutes
    MIN_DISTANCE_SAVINGS_KM = 0.5  # Minimum distance savings

    def __init__(self):
        self.decision_history = []
        logger.info("RerouteDecisionAgent initialized")

    def decide(
        self,
        primary_route: Dict,
        alternate_routes: List[Dict],
        delay_probability: float,
        time_of_day: int = None,
        weather: str = "clear",
        user_preference: str = "balanced"  # "speed", "safety", or "balanced"
    ) -> RerouteRecommendation:
        """
        Make a rerouting decision based on delay prediction and route metrics.

        Args:
            primary_route: Dict with distance_km, estimated_time_min, risk_score
            alternate_routes: List of alternate route dicts
            delay_probability: Predicted delay prob (0.0-1.0)
            time_of_day: Hour (0-23)
            weather: "clear", "rain", or "storm"
            user_preference: "speed" (minimize time), "safety" (minimize risk), "balanced"

        Returns:
            RerouteRecommendation with decision and confidence
        """
        metrics = {
            "delay_probability": delay_probability,
            "time_of_day": time_of_day,
            "weather": weather,
            "user_preference": user_preference,
            "primary_route_metrics": primary_route,
            "alternate_routes_metrics": alternate_routes
        }

        # No alternates available -> stick with primary
        if not alternate_routes:
            recommendation = RerouteRecommendation(
                decision=RerouteDecision.STICK_PRIMARY,
                recommended_route_index=0,
                confidence=1.0,
                reasoning="No alternate routes available. Using primary route.",
                metrics=metrics
            )
            self.decision_history.append(recommendation)
            return recommendation

        # ========== DECISION LOGIC ==========

        # Rule 1: Very high delay probability -> STRONG REROUTE if alternative is safer
        if delay_probability >= self.STRONG_DELAY_THRESHOLD:
            best_alt = self._find_best_alternative(
                primary_route, alternate_routes,
                user_preference=user_preference
            )
            if best_alt["improvement"] > 0.05:  # 5% improvement
                recommendation = RerouteRecommendation(
                    decision=RerouteDecision.STRONG_REROUTE,
                    recommended_route_index=best_alt["index"] + 1,
                    confidence=0.95,
                    reasoning=f"High delay probability ({delay_probability:.1%}). Alternative route has {best_alt['improvement']:.1%} lower risk.",
                    metrics=metrics
                )
            else:
                recommendation = RerouteRecommendation(
                    decision=RerouteDecision.STICK_PRIMARY,
                    recommended_route_index=0,
                    confidence=0.85,
                    reasoning=f"High delay probability ({delay_probability:.1%}), but no significantly safer alternative available.",
                    metrics=metrics
                )
            self.decision_history.append(recommendation)
            return recommendation

        # Rule 2: Moderate delay prob + significant time/distance savings -> WEAK REROUTE
        if delay_probability >= self.WEAK_DELAY_THRESHOLD:
            time_savings = primary_route["estimated_time_min"] - min(
                [alt["estimated_time_min"] for alt in alternate_routes]
            )
            distance_savings = primary_route["distance_km"] - min(
                [alt["distance_km"] for alt in alternate_routes]
            )

            if time_savings >= self.MIN_TIME_SAVINGS_MIN or distance_savings >= self.MIN_DISTANCE_SAVINGS_KM:
                best_alt = self._find_best_alternative(
                    primary_route, alternate_routes,
                    user_preference=user_preference
                )
                recommendation = RerouteRecommendation(
                    decision=RerouteDecision.WEAK_REROUTE,
                    recommended_route_index=best_alt["index"] + 1,
                    confidence=0.70,
                    reasoning=f"Moderate delay risk ({delay_probability:.1%}). Alternative saves {time_savings:.1f} mins / {distance_savings:.1f} km.",
                    metrics=metrics
                )
            else:
                recommendation = RerouteRecommendation(
                    decision=RerouteDecision.STICK_PRIMARY,
                    recommended_route_index=0,
                    confidence=0.60,
                    reasoning=f"Moderate delay risk ({delay_probability:.1%}), but alternatives don't offer enough benefit.",
                    metrics=metrics
                )
            self.decision_history.append(recommendation)
            return recommendation

        # Rule 3: Low delay prob but bad weather/traffic -> CONDITIONAL REROUTE
        if delay_probability < self.WEAK_DELAY_THRESHOLD and (weather in ["rain", "storm"] or (time_of_day and (8 <= time_of_day <= 10 or 17 <= time_of_day <= 19))):
            best_alt = self._find_best_alternative(
                primary_route, alternate_routes,
                user_preference="safety"  # Prefer safety in bad conditions
            )
            if best_alt["improvement"] > 0.03:
                recommendation = RerouteRecommendation(
                    decision=RerouteDecision.CONDITIONAL_REROUTE,
                    recommended_route_index=best_alt["index"] + 1,
                    confidence=0.55,
                    reasoning=f"Weather/traffic conditions ({weather}, rush_hour={8 <= time_of_day <= 10 or 17 <= time_of_day <= 19}). Safer alternative available.",
                    metrics=metrics
                )
            else:
                recommendation = RerouteRecommendation(
                    decision=RerouteDecision.STICK_PRIMARY,
                    recommended_route_index=0,
                    confidence=0.75,
                    reasoning=f"Low delay probability ({delay_probability:.1%}). Primary route is best option.",
                    metrics=metrics
                )
            self.decision_history.append(recommendation)
            return recommendation

        # Rule 4: Default -> stick with primary
        recommendation = RerouteRecommendation(
            decision=RerouteDecision.STICK_PRIMARY,
            recommended_route_index=0,
            confidence=0.80,
            reasoning=f"Low delay probability ({delay_probability:.1%}). Primary route is optimal.",
            metrics=metrics
        )
        self.decision_history.append(recommendation)
        return recommendation

    def _find_best_alternative(
        self,
        primary_route: Dict,
        alternate_routes: List[Dict],
        user_preference: str = "balanced"
    ) -> Dict:
        """Find the best alternate route based on user preference."""
        best = None
        best_score = float("inf")

        for idx, alt in enumerate(alternate_routes):
            if user_preference == "speed":
                score = alt["estimated_time_min"]
            elif user_preference == "safety":
                score = alt["risk_score"]
            else:  # "balanced"
                # Weighted: 60% risk, 40% time
                primary_time = primary_route["estimated_time_min"] or 1.0  # Avoid division by zero
                score = alt["risk_score"] * 0.6 + (alt["estimated_time_min"] / primary_time) * 0.4

            if score < best_score:
                primary_risk = primary_route["risk_score"] or 0.001  # Avoid division by zero
                improvement = (primary_risk - alt["risk_score"]) / primary_risk if primary_risk > 0 else 0.0
                best = {
                    "index": idx,
                    "route": alt,
                    "score": score,
                    "improvement": improvement
                }
                best_score = score

        return best

    def get_decision_summary(self) -> Dict:
        """Get summary statistics of recent decisions."""
        if not self.decision_history:
            return {"decisions_made": 0}

        decisions_by_type = {}
        avg_confidence = 0.0
        for rec in self.decision_history[-100:]:  # Last 100 decisions
            decision_str = rec.decision.value
            decisions_by_type[decision_str] = decisions_by_type.get(decision_str, 0) + 1
            avg_confidence += rec.confidence

        return {
            "decisions_made": len(self.decision_history),
            "recent_100_breakdown": decisions_by_type,
            "avg_confidence": round(avg_confidence / len(self.decision_history[-100:]), 3)
        }
