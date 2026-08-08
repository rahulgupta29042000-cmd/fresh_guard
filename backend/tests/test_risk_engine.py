import datetime
from types import SimpleNamespace

from app import config, risk_engine


def make_order(distance_km=5.0, hour=12):
    return SimpleNamespace(distance_km=distance_km, order_time=datetime.datetime(2026, 1, 1, hour, 0, 0))


def make_warehouse(current_load=10, capacity=40):
    return SimpleNamespace(current_load=current_load, capacity=capacity)


def make_item(name="Item", category="general", fragility=20, temp=False, weight=0.3, hist=0.05, qty=1):
    return {
        "name": name,
        "category": category,
        "fragility_score": fragility,
        "temperature_sensitive": temp,
        "weight_kg": weight,
        "historical_damage_rate": hist,
        "quantity": qty,
    }


def test_risk_level_thresholds_are_configurable():
    assert config.risk_level_for_score(10) == "LOW"
    assert config.risk_level_for_score(45) == "MEDIUM"
    assert config.risk_level_for_score(70) == "HIGH"
    assert config.risk_level_for_score(90) == "CRITICAL"
    assert config.risk_level_for_score(0) == "LOW"
    assert config.risk_level_for_score(100) == "CRITICAL"


def test_low_risk_order():
    order = make_order(distance_km=2, hour=11)
    warehouse = make_warehouse(current_load=4, capacity=40)
    items = [make_item(name="Apples", category="produce", fragility=15, hist=0.02, qty=3)]

    result = risk_engine.assess_risk(order, items, warehouse, None, None)

    assert result["risk_level"] in ("LOW", "MEDIUM")
    assert 0 <= result["risk_score"] <= 100
    assert result["prediction_source"] in ("ml_model", "rule_based_fallback")


def test_high_risk_order_with_fragile_and_temp_items():
    order = make_order(distance_km=6, hour=19)  # peak hour
    warehouse = make_warehouse(current_load=38, capacity=40)  # near-saturated warehouse
    items = [
        make_item(name="Glass Sauce Bottle", category="condiments", fragility=90, hist=0.15, qty=1),
        make_item(name="Milk", category="dairy", fragility=25, temp=True, hist=0.06, qty=1),
        make_item(name="Tomatoes", category="produce", fragility=45, hist=0.12, qty=2),
    ]

    result = risk_engine.assess_risk(order, items, warehouse, None, None)

    assert result["risk_level"] in ("HIGH", "CRITICAL")
    fragile_factor = any("Fragile" in f["factor"] or "fragile" in f["factor"] for f in result["risk_factors"])
    assert fragile_factor


def test_critical_risk_order_with_many_fragile_temperature_sensitive_items():
    order = make_order(distance_km=15, hour=19)
    warehouse = make_warehouse(current_load=39, capacity=40)
    items = [
        make_item(name="Eggs", category="dairy", fragility=85, temp=True, hist=0.20, qty=4),
        make_item(name="Glass Bottle A", category="condiments", fragility=92, hist=0.18, qty=2),
        make_item(name="Glass Bottle B", category="condiments", fragility=88, hist=0.16, qty=2),
    ]

    result = risk_engine.assess_risk(order, items, warehouse, None, None)

    assert result["risk_score"] >= 55
    assert result["risk_level"] in ("HIGH", "CRITICAL")


def test_component_scores_are_bounded_0_to_100():
    features = risk_engine.build_features(make_order(), [make_item()], make_warehouse(), None, None)
    components = risk_engine.compute_component_scores(features)
    for value in components.values():
        assert 0 <= value <= 100


def test_recommendations_are_generated_separately_from_score(monkeypatch):
    from app import recommendations

    recs = recommendations.generate_recommendations(
        "HIGH",
        [{"name": "Glass Bottle", "category": "condiments", "fragility_score": 90, "temperature_sensitive": False, "weight_kg": 0.4}],
        distance_km=10,
    )
    assert any("separately" in r["instruction"] for r in recs)
    assert any(r["priority"] == "high" for r in recs)


def test_falls_back_to_rule_based_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(risk_engine, "_try_load_model", lambda: None)

    order = make_order()
    warehouse = make_warehouse()
    result = risk_engine.assess_risk(order, [make_item()], warehouse, None, None)

    assert result["prediction_source"] == "rule_based_fallback"
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
