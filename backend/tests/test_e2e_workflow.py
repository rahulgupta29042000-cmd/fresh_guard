def test_full_order_workflow_create_to_feedback(client, seeded):
    payload = {
        "customer_name": "E2E Customer",
        "warehouse_id": seeded["warehouse"].id,
        "distance_km": 5.2,
        "items": [
            {"product_id": seeded["product1"].id, "quantity": 2},
            {"product_id": seeded["product2"].id, "quantity": 1},
        ],
    }

    created = client.post("/api/orders", json=payload)
    assert created.status_code == 200
    order = created.json()
    order_id = order["id"]
    assert order["status"] == "RISK_ASSESSED"
    assert order["risk"] is not None

    res = client.post(f"/api/orders/{order_id}/picking", json={"action": "start"})
    assert res.status_code == 200
    assert res.json()["status"] == "PICKING"

    for item in order["items"]:
        res = client.post(f"/api/orders/{order_id}/picking", json={"action": "mark_item_picked", "item_id": item["id"]})
        assert res.status_code == 200
        assert next(i for i in res.json()["items"] if i["id"] == item["id"])["picked"] is True

    res = client.post(f"/api/orders/{order_id}/picking", json={"action": "complete"})
    assert res.status_code == 200
    assert res.json()["status"] == "PICKED"

    plan = client.get(f"/api/orders/{order_id}/packing-plan")
    assert plan.status_code == 200
    assert len(plan.json()["bags"]) > 0

    res = client.post(f"/api/orders/{order_id}/packing", json={"action": "confirm"})
    assert res.status_code == 200
    assert res.json()["status"] == "confirmed"

    order_after_packing = client.get(f"/api/orders/{order_id}").json()
    assert order_after_packing["status"] == "PACKED"

    delivery = client.get(f"/api/orders/{order_id}/delivery")
    assert delivery.status_code == 200
    assert len(delivery.json()["instructions"]) > 0

    res = client.post(f"/api/orders/{order_id}/delivery", json={"action": "accept_instructions"})
    assert res.status_code == 200
    assert res.json()["accepted"] is True

    order_after_dispatch = client.get(f"/api/orders/{order_id}").json()
    assert order_after_dispatch["status"] == "DISPATCHED"

    res = client.post(f"/api/orders/{order_id}/delivery", json={"action": "mark_delivered"})
    assert res.status_code == 200

    order_after_delivery = client.get(f"/api/orders/{order_id}").json()
    assert order_after_delivery["status"] == "DELIVERED"

    res = client.post(f"/api/orders/{order_id}/feedback", json={"rating": 5, "issue_type": "none", "comments": "All good"})
    assert res.status_code == 200

    final_order = client.get(f"/api/orders/{order_id}").json()
    assert final_order["status"] == "FEEDBACK_RECEIVED"

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["kpis"]["damage_free_rate"] == 100.0
