"""Full Phase 2 workflow: order -> risk -> product selection -> AI
inspection -> reject -> replacement -> reinspection -> pass -> packing ->
delivery -> customer feedback. Mirrors the FG-10241 demo scenario."""
from tests.test_vision import make_jpeg


def test_full_reject_replace_reinspect_pass_then_fulfillment(client, seeded):
    # Order -> Risk
    payload = {
        "customer_name": "E2E Phase 2 Customer",
        "warehouse_id": seeded["warehouse"].id,
        "distance_km": 6.0,
        "items": [
            {"product_id": seeded["product1"].id, "quantity": 2},  # Tomatoes
            {"product_id": seeded["product2"].id, "quantity": 1},  # Glass Sauce Bottle
        ],
    }
    order = client.post("/api/orders", json=payload).json()
    assert order["risk"] is not None
    tomato_item = next(i for i in order["items"] if i["product"]["id"] == seeded["product1"].id)

    # Picking
    client.post(f"/api/orders/{order['id']}/picking", json={"action": "start"})

    # Product selection -> AI Inspection -> REJECT
    bad_img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_severe_reject"}).json()
    insp = client.post(
        "/api/inspections", json={"order_id": order["id"], "order_item_id": tomato_item["id"], "image_id": bad_img["id"]}
    ).json()
    analyzed = client.post(f"/api/inspections/{insp['inspectionId']}/analyze").json()
    assert analyzed["inspectionStatus"] == "REJECT"
    client.post(f"/api/inspections/{insp['inspectionId']}/reject")

    # Replacement
    replaced = client.post(
        f"/api/inspections/{insp['inspectionId']}/replace",
        json={"replacement_product_id": seeded["product1"].id, "reason": "Bruising detected"},
    ).json()
    new_item_id = replaced["newOrderItem"]["id"]
    new_insp_id = replaced["newInspectionId"]

    # Reinspection -> PASS
    good_img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_good"}).json()
    client.post(f"/api/inspections/{new_insp_id}/image", json={"image_id": good_img["id"]})
    reinspected = client.post(f"/api/inspections/{new_insp_id}/analyze").json()
    assert reinspected["inspectionStatus"] == "PASS"
    client.post(f"/api/inspections/{new_insp_id}/accept")

    # Glass Sauce Bottle also inspects clean
    glass_item = next(i for i in order["items"] if i["product"]["id"] == seeded["product2"].id)
    glass_img = client.post("/api/images/upload-sample", json={"sample_key": "glass_good"}).json()
    glass_insp = client.post(
        "/api/inspections", json={"order_id": order["id"], "order_item_id": glass_item["id"], "image_id": glass_img["id"]}
    ).json()
    glass_analyzed = client.post(f"/api/inspections/{glass_insp['inspectionId']}/analyze").json()
    assert glass_analyzed["inspectionStatus"] == "PASS"
    client.post(f"/api/inspections/{glass_insp['inspectionId']}/accept")

    for item_id in [tomato_item["id"], glass_item["id"]]:
        client.post(f"/api/orders/{order['id']}/picking", json={"action": "mark_item_picked", "item_id": item_id})
    client.post(f"/api/orders/{order['id']}/picking", json={"action": "mark_item_picked", "item_id": new_item_id})
    client.post(f"/api/orders/{order['id']}/picking", json={"action": "complete"})

    # Packing — the replaced (original bruised) tomato line must be excluded
    plan = client.get(f"/api/orders/{order['id']}/packing-plan").json()
    packed_item_ids = {item["order_item_id"] for bag in plan["bags"] for item in bag["items"]}
    assert tomato_item["id"] not in packed_item_ids
    assert new_item_id in packed_item_ids
    client.post(f"/api/orders/{order['id']}/packing", json={"action": "confirm"})

    # Delivery
    client.post(f"/api/orders/{order['id']}/delivery", json={"action": "accept_instructions"})
    client.post(f"/api/orders/{order['id']}/delivery", json={"action": "mark_delivered"})

    # Customer feedback
    fb = client.post(f"/api/orders/{order['id']}/feedback", json={"rating": 5, "issue_type": "none"})
    assert fb.status_code == 200

    final_order = client.get(f"/api/orders/{order['id']}").json()
    assert final_order["status"] == "FEEDBACK_RECEIVED"

    # Inspection analytics reflect the reject + eventual passes
    analytics = client.get("/api/analytics/inspections").json()
    assert analytics["inspected"] >= 3
    assert analytics["rejected"] >= 1

    # Phase 1 dashboard still works and now carries the ai_inspection block
    dashboard = client.get("/api/dashboard").json()
    assert "ai_inspection" in dashboard
    assert dashboard["ai_inspection"]["inspected"] >= 3
