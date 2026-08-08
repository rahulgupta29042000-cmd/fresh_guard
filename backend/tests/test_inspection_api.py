import io

from app import config


def make_image_bytes(**kwargs):
    from tests.test_vision import make_jpeg

    return make_jpeg(**kwargs)


def create_order(client, seeded, product_id=None, quantity=2):
    payload = {
        "customer_name": "Test Customer",
        "warehouse_id": seeded["warehouse"].id,
        "distance_km": 5.0,
        "items": [{"product_id": product_id or seeded["product1"].id, "quantity": quantity}],
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 200
    return res.json()


# ---------------------------------------------------------------------------
# Image upload validation
# ---------------------------------------------------------------------------


def test_upload_valid_image(client, seeded):
    files = {"file": ("tomato.jpg", make_image_bytes(), "image/jpeg")}
    res = client.post("/api/images/upload", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["imageQuality"]["status"] == "good"


def test_upload_invalid_image_rejected(client, seeded):
    files = {"file": ("not-an-image.jpg", b"garbage bytes not an image", "image/jpeg")}
    res = client.post("/api/images/upload", files=files)
    assert res.status_code == 400


def test_upload_unsupported_format_rejected(client, seeded):
    files = {"file": ("doc.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")}
    res = client.post("/api/images/upload", files=files)
    assert res.status_code == 400


def test_upload_too_large_rejected(client, seeded):
    oversized = b"0" * (config.IMAGE_MAX_SIZE_BYTES + 1)
    files = {"file": ("huge.jpg", oversized, "image/jpeg")}
    res = client.post("/api/images/upload", files=files)
    assert res.status_code == 400


def test_upload_sample_image(client, seeded):
    res = client.post("/api/images/upload-sample", json={"sample_key": "tomato_good"})
    assert res.status_code == 200
    assert res.json()["imageQuality"]["status"] == "good"


# ---------------------------------------------------------------------------
# Inspection creation + analysis
# ---------------------------------------------------------------------------


def test_create_and_analyze_inspection_pass(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id)
    item_id = order["items"][0]["id"]

    img = client.post("/api/images/upload", files={"file": ("t.jpg", make_image_bytes(), "image/jpeg")}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    assert insp["inspectionStatus"] == "PENDING"

    analyzed = client.post(f"/api/inspections/{insp['inspectionId']}/analyze").json()
    assert analyzed["inspectionStatus"] == "PASS"
    assert analyzed["modelVersion"]


def test_analyze_with_poor_quality_image_returns_422(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id)
    item_id = order["items"][0]["id"]

    dark_img = client.post(
        "/api/images/upload", files={"file": ("dark.jpg", make_image_bytes(brightness_scale=0.1), "image/jpeg")}
    ).json()
    assert dark_img["imageQuality"]["status"] == "poor"

    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": dark_img["id"]}).json()
    res = client.post(f"/api/inspections/{insp['inspectionId']}/analyze")
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Human review
# ---------------------------------------------------------------------------


def test_human_accepts_ai_pass(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id)
    item_id = order["items"][0]["id"]
    img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_good"}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    client.post(f"/api/inspections/{insp['inspectionId']}/analyze")

    res = client.post(f"/api/inspections/{insp['inspectionId']}/accept")
    assert res.status_code == 200
    assert res.json()["humanDecision"] == "ACCEPT"

    item = client.get(f"/api/orders/{order['id']}").json()["items"][0]
    assert item["quality_check_status"] == "PASSED"


def test_human_overrides_ai_reject_to_accept(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id)
    item_id = order["items"][0]["id"]
    img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_severe_reject"}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    analyzed = client.post(f"/api/inspections/{insp['inspectionId']}/analyze").json()
    assert analyzed["aiDecision"] == "REJECT"

    res = client.post(f"/api/inspections/{insp['inspectionId']}/accept")
    assert res.status_code == 200
    assert res.json()["humanDecision"] == "ACCEPT"
    assert res.json()["aiDecision"] == "REJECT"  # raw AI output is never overwritten


def test_human_confirms_ai_reject(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id)
    item_id = order["items"][0]["id"]
    img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_severe_reject"}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    client.post(f"/api/inspections/{insp['inspectionId']}/analyze")

    res = client.post(f"/api/inspections/{insp['inspectionId']}/reject")
    assert res.status_code == 200
    assert res.json()["humanDecision"] == "REJECT"
    item = client.get(f"/api/orders/{order['id']}").json()["items"][0]
    assert item["quality_check_status"] == "FAILED"


def test_review_case_appears_in_queue_and_resolves(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product2"].id)  # Glass Sauce Bottle
    item_id = order["items"][0]["id"]
    img = client.post("/api/images/upload-sample", json={"sample_key": "glass_crack_review"}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    analyzed = client.post(f"/api/inspections/{insp['inspectionId']}/analyze").json()
    assert analyzed["inspectionStatus"] == "REVIEW"

    queue = client.get("/api/qc/review-queue").json()
    assert any(i["inspectionId"] == insp["inspectionId"] for i in queue["items"])

    client.post(f"/api/inspections/{insp['inspectionId']}/accept")
    queue_after = client.get("/api/qc/review-queue").json()
    assert not any(i["inspectionId"] == insp["inspectionId"] for i in queue_after["items"])


# ---------------------------------------------------------------------------
# Replacement loop
# ---------------------------------------------------------------------------


def test_replace_after_reject_creates_new_item_and_inspection(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id, quantity=2)
    item_id = order["items"][0]["id"]
    img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_severe_reject"}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    client.post(f"/api/inspections/{insp['inspectionId']}/analyze")
    client.post(f"/api/inspections/{insp['inspectionId']}/reject")

    res = client.post(
        f"/api/inspections/{insp['inspectionId']}/replace",
        json={"replacement_product_id": seeded["product3"].id, "reason": "bruised"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["newOrderItem"]["product"]["id"] == seeded["product3"].id
    assert body["newOrderItem"]["quantity"] == 2

    order_after = client.get(f"/api/orders/{order['id']}").json()
    original = next(i for i in order_after["items"] if i["id"] == item_id)
    assert original["replaced"] is True
    assert original["replaced_by_item_id"] == body["newOrderItem"]["id"]


def test_cannot_replace_without_rejection(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id)
    item_id = order["items"][0]["id"]
    img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_good"}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    client.post(f"/api/inspections/{insp['inspectionId']}/analyze")
    client.post(f"/api/inspections/{insp['inspectionId']}/accept")

    res = client.post(f"/api/inspections/{insp['inspectionId']}/replace", json={"replacement_product_id": seeded["product3"].id})
    assert res.status_code == 400


def test_reinspect_same_item_creates_fresh_attempt(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id)
    item_id = order["items"][0]["id"]
    img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_good"}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    client.post(f"/api/inspections/{insp['inspectionId']}/analyze")

    res = client.post(f"/api/inspections/{insp['inspectionId']}/reinspect")
    assert res.status_code == 200
    fresh = res.json()
    assert fresh["orderItemId"] == item_id
    assert fresh["attemptNumber"] == 2
    assert fresh["inspectionStatus"] == "PENDING"


def test_replacement_can_then_pass(client, seeded):
    order = create_order(client, seeded, product_id=seeded["product1"].id)
    item_id = order["items"][0]["id"]
    img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_severe_reject"}).json()
    insp = client.post("/api/inspections", json={"order_id": order["id"], "order_item_id": item_id, "image_id": img["id"]}).json()
    client.post(f"/api/inspections/{insp['inspectionId']}/analyze")
    client.post(f"/api/inspections/{insp['inspectionId']}/reject")
    replaced = client.post(
        f"/api/inspections/{insp['inspectionId']}/replace", json={"replacement_product_id": seeded["product1"].id}
    ).json()

    new_item_id = replaced["newOrderItem"]["id"]
    new_insp_id = replaced["newInspectionId"]

    good_img = client.post("/api/images/upload-sample", json={"sample_key": "tomato_good"}).json()
    client.post(f"/api/inspections/{new_insp_id}/image", json={"image_id": good_img["id"]})
    analyzed = client.post(f"/api/inspections/{new_insp_id}/analyze").json()
    assert analyzed["inspectionStatus"] == "PASS"

    client.post(f"/api/inspections/{new_insp_id}/accept")
    item = next(i for i in client.get(f"/api/orders/{order['id']}").json()["items"] if i["id"] == new_item_id)
    assert item["quality_check_status"] == "PASSED"
