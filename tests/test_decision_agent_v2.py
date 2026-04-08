from backend.services.decision_agent import DecisionAgentService


def test_decision_agent_picks_lowest_score_non_emergency():
    result = DecisionAgentService.decide(
        route_options=[
            {
                "route_id": "r1",
                "route_type": "optimal",
                "distance_km": 15.0,
                "duration_minutes": 35,
                "risk_score": 30,
                "predicted_cost": 20,
                "predicted_delay_minutes": 10,
            },
            {
                "route_id": "r2",
                "route_type": "alternative_1",
                "distance_km": 14.0,
                "duration_minutes": 30,
                "risk_score": 25,
                "predicted_cost": 18,
                "predicted_delay_minutes": 8,
            },
        ],
        delay_prediction={"predicted_delay_minutes": 12, "delay_probability": 0.4, "severity": "medium"},
        emergency=False,
    )

    assert result["selected_route_id"] == "r2"
    assert result["emergency_mode"] is False
    assert "notify_client" in result["recommended_actions"]
    assert len(result["ranked_routes"]) == 2


def test_decision_agent_emergency_actions_present():
    result = DecisionAgentService.decide(
        route_options=[
            {
                "route_id": "r1",
                "route_type": "optimal",
                "distance_km": 15.0,
                "duration_minutes": 35,
                "risk_score": 10,
                "predicted_cost": 20,
                "predicted_delay_minutes": 10,
            }
        ],
        delay_prediction={"predicted_delay_minutes": 20, "delay_probability": 0.8, "severity": "high"},
        emergency=True,
    )

    assert result["selected_route_id"] == "r1"
    assert result["emergency_mode"] is True
    assert "escalate_dispatch" in result["recommended_actions"]
    assert "priority_reroute" in result["recommended_actions"]
