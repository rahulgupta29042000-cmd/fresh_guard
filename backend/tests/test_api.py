from app import models


def order_payload(seeded, **overrides):
    payload = {
        "customer_name": "Test Customer",
        "warehouse_id": seeded["warehouse"].id,
        "distance_km": 5.0,
        "items": [
            {"product_id": seeded["product1"].id, "quantity": 2},
            {"product_id": seeded["product2"].id, "quantity": 1},
        ],
    }
    payload.update(overrides)
    return payload


def test_create_order_valid(client, seeded):
    res = client.post("/api/orders", json=order_payload(seeded))
    assert res.status_code == 200
    data = res.json()
    assert data["order_code"].startswith("FG-")
    assert data["status"] == "RISK_ASSESSED"
    assert data["risk"] is not None
    assert data["risk"]["riskLevel"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert 0 <= data["risk"]["riskScore"] <= 100
    assert len(data["items"]) == 2


def test_create_order_missing_warehouse(client, seeded):
    res = client.post("/api/orders", json=order_payload(seeded, warehouse_id=999999))
    assert res.status_code == 400


def test_create_order_missing_product(client, seeded):
    payload = order_payload(seeded, items=[{"product_id": 999999, "quantity": 1}])
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400


def test_create_order_with_no_items_is_invalid(client, seeded):
    res = client.post("/api/orders", json=order_payload(seeded, items=[]))
    assert res.status_code == 400


def test_create_order_with_invalid_quantity_is_rejected(client, seeded):
    payload = order_payload(seeded, items=[{"product_id": seeded["product1"].id, "quantity": 0}])
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 422  # pydantic validation: quantity must be > 0


def test_get_order_not_found(client, seeded):
    res = client.get("/api/orders/999999")
    assert res.status_code == 404


def test_get_order_with_missing_risk_prediction_is_handled_gracefully(client, seeded, db_session):
    customer = models.Customer(name="No Risk Yet")
    db_session.add(customer)
    db_session.flush()
    order = models.Order(
        order_code="FG-99999",
        customer_id=customer.id,
        warehouse_id=seeded["warehouse"].id,
        distance_km=3.0,
        status="CREATED",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(models.OrderItem(order_id=order.id, product_id=seeded["product1"].id, quantity=1))
    db_session.commit()

    res = client.get(f"/api/orders/{order.id}")
    assert res.status_code == 200
    assert res.json()["risk"] is None


def test_list_orders_filters_by_risk_level(client, seeded):
    client.post("/api/orders", json=order_payload(seeded))
    res = client.get("/api/orders", params={"risk_level": "LOW"})
    assert res.status_code == 200
    for order in res.json():
        assert order["risk_level"] == "LOW"


def test_recalculate_risk(client, seeded):
    created = client.post("/api/orders", json=order_payload(seeded)).json()
    res = client.post(f"/api/orders/{created['id']}/recalculate-risk")
    assert res.status_code == 200
    assert res.json()["riskLevel"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_picking_requires_valid_item_id(client, seeded):
    created = client.post("/api/orders", json=order_payload(seeded)).json()
    res = client.post(f"/api/orders/{created['id']}/picking", json={"action": "mark_item_picked", "item_id": 999999})
    assert res.status_code == 404


def test_feedback_cannot_be_submitted_twice(client, seeded):
    created = client.post("/api/orders", json=order_payload(seeded)).json()
    order_id = created["id"]
    first = client.post(f"/api/orders/{order_id}/feedback", json={"rating": 5, "issue_type": "none"})
    assert first.status_code == 200
    second = client.post(f"/api/orders/{order_id}/feedback", json={"rating": 3, "issue_type": "other"})
    assert second.status_code == 409


def test_dashboard_returns_kpis(client, seeded):
    client.post("/api/orders", json=order_payload(seeded))
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert "kpis" in body
    assert "damage_free_rate" in body["kpis"]
