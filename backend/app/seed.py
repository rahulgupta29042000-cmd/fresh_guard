"""Seed the Fresh_Guard database with a synthetic but internally-consistent
demo dataset: warehouses, products, pickers/riders, ~230 historical orders
spanning the last 14 days (run through the *real* risk engine so seeded
numbers match what the live app would compute), and the polished demo
order FG-10241 used for the end-to-end walkthrough.

Run from backend/: python -m app.seed
"""
import datetime
import json
import random

from . import models, services
from .database import Base, SessionLocal, engine

random.seed(7)

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditi", "Ananya", "Diya", "Ishaan", "Kabir", "Meera",
    "Neha", "Rohan", "Saanvi", "Tara", "Vihaan", "Zara", "Arjun", "Kiara",
    "Dev", "Priya", "Rahul", "Sanya",
]
LAST_NAMES = ["Sharma", "Verma", "Iyer", "Reddy", "Gupta", "Nair", "Khan", "Patel", "Menon", "Rao"]

WAREHOUSE_SEED = [
    {"name": "Koramangala Dark Store", "location": "Bengaluru", "capacity": 40, "current_load": 37},
    {"name": "Andheri Dark Store", "location": "Mumbai", "capacity": 40, "current_load": 20},
    {"name": "Whitefield Dark Store", "location": "Bengaluru", "capacity": 35, "current_load": 9},
    {"name": "Gurgaon Sector 49 Dark Store", "location": "Gurgaon", "capacity": 35, "current_load": 30},
]

PRODUCT_SEED = [
    {"name": "Tomatoes", "category": "produce", "emoji": "🍅", "weight_kg": 0.15, "fragility_score": 45,
     "temperature_sensitive": False, "packaging_type": "loose", "historical_damage_rate": 0.12},
    {"name": "Apples", "category": "produce", "emoji": "🍎", "weight_kg": 0.18, "fragility_score": 20,
     "temperature_sensitive": False, "packaging_type": "bag", "historical_damage_rate": 0.04},
    {"name": "Milk 1L", "category": "dairy", "emoji": "🥛", "weight_kg": 1.03, "fragility_score": 25,
     "temperature_sensitive": True, "packaging_type": "carton", "historical_damage_rate": 0.06},
    {"name": "Glass Sauce Bottle", "category": "condiments", "emoji": "🍾", "weight_kg": 0.4, "fragility_score": 88,
     "temperature_sensitive": False, "packaging_type": "glass", "historical_damage_rate": 0.15},
    {"name": "Chips", "category": "snacks", "emoji": "🍟", "weight_kg": 0.09, "fragility_score": 30,
     "temperature_sensitive": False, "packaging_type": "packet", "historical_damage_rate": 0.08},
    {"name": "Eggs (dozen)", "category": "dairy", "emoji": "🥚", "weight_kg": 0.7, "fragility_score": 80,
     "temperature_sensitive": True, "packaging_type": "carton", "historical_damage_rate": 0.18},
    {"name": "Bananas", "category": "produce", "emoji": "🍌", "weight_kg": 0.9, "fragility_score": 55,
     "temperature_sensitive": False, "packaging_type": "loose", "historical_damage_rate": 0.10},
    {"name": "Bread Loaf", "category": "bakery", "emoji": "🍞", "weight_kg": 0.4, "fragility_score": 35,
     "temperature_sensitive": False, "packaging_type": "bag", "historical_damage_rate": 0.07},
    {"name": "Ice Cream Tub", "category": "frozen", "emoji": "🍦", "weight_kg": 0.6, "fragility_score": 15,
     "temperature_sensitive": True, "packaging_type": "tub", "historical_damage_rate": 0.09},
    {"name": "Chicken Breast", "category": "meat", "emoji": "🍗", "weight_kg": 0.5, "fragility_score": 10,
     "temperature_sensitive": True, "packaging_type": "vacuum_pack", "historical_damage_rate": 0.05},
    {"name": "Cola 2L Bottle", "category": "beverages", "emoji": "🥤", "weight_kg": 2.1, "fragility_score": 40,
     "temperature_sensitive": False, "packaging_type": "plastic_bottle", "historical_damage_rate": 0.06},
    {"name": "Potato Chips Multipack", "category": "snacks", "emoji": "🍿", "weight_kg": 0.35, "fragility_score": 25,
     "temperature_sensitive": False, "packaging_type": "box", "historical_damage_rate": 0.05},
    {"name": "Yogurt Cup", "category": "dairy", "emoji": "🥣", "weight_kg": 0.15, "fragility_score": 50,
     "temperature_sensitive": True, "packaging_type": "cup", "historical_damage_rate": 0.11},
    {"name": "Onions (1kg)", "category": "produce", "emoji": "🧅", "weight_kg": 1.0, "fragility_score": 15,
     "temperature_sensitive": False, "packaging_type": "bag", "historical_damage_rate": 0.03},
]

ISSUE_COMMENTS = {
    "bruised_damaged_produce": ["Tomatoes were bruised on arrival.", "Fruit looked squashed in the bag."],
    "crushed_packaging": ["Box was crushed at the bottom.", "Packaging was dented."],
    "broken_item": ["Bottle arrived broken.", "Item was shattered in the bag."],
    "temperature_issue": ["Milk was warm on arrival.", "Ice cream had melted."],
    "spoiled_product": ["Product smelled off.", "Looked spoiled when opened."],
    "other": ["Not happy with the packing.", "Minor issue, not a big deal."],
}


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def create_reference_data(db):
    warehouses = []
    for w in WAREHOUSE_SEED:
        obj = models.Warehouse(**w)
        db.add(obj)
        warehouses.append(obj)
    db.flush()

    products = []
    for p in PRODUCT_SEED:
        obj = models.Product(**p)
        db.add(obj)
        products.append(obj)
    db.flush()

    pickers, riders = [], []
    for w in warehouses:
        for i in range(3):
            u = models.User(
                name=random_name(),
                role="picker",
                warehouse_id=w.id,
                experience_years=round(random.uniform(0.2, 6.0), 1),
                avg_quality_score=round(random.uniform(65, 97), 1),
                avg_picking_speed=round(random.uniform(3.5, 9.5), 1),
            )
            db.add(u)
            pickers.append(u)
        for i in range(2):
            u = models.User(
                name=random_name(),
                role="rider",
                warehouse_id=w.id,
                experience_years=round(random.uniform(0.2, 6.0), 1),
                avg_rating=round(random.uniform(3.6, 5.0), 1),
            )
            db.add(u)
            riders.append(u)
        db.add(models.User(name=random_name(), role="manager", warehouse_id=w.id, experience_years=round(random.uniform(2, 8), 1)))
    db.flush()

    return warehouses, products, pickers, riders


def build_order_items(order, products):
    n_skus = random.randint(2, 8)
    chosen = random.sample(products, n_skus)
    for p in chosen:
        db_item = models.OrderItem(order_id=order.id, product_id=p.id, quantity=random.randint(1, 3))
        yield db_item


def choose_issue_type(items):
    has_fragile = any(oi.product.fragility_score >= 65 for oi in items)
    has_temp = any(oi.product.temperature_sensitive for oi in items)
    has_produce = any(oi.product.category == "produce" for oi in items)

    roll = random.random()
    if has_fragile and roll < 0.35:
        return "broken_item"
    if has_temp and roll < 0.55:
        return "temperature_issue"
    if has_produce and roll < 0.75:
        return "bruised_damaged_produce"
    return random.choice(["crushed_packaging", "spoiled_product", "other"])


def pick_damaged_item(items, issue_type):
    if issue_type == "temperature_issue":
        candidates = [i for i in items if i.product.temperature_sensitive]
    elif issue_type == "broken_item":
        candidates = sorted(items, key=lambda i: -i.product.fragility_score)
    elif issue_type == "bruised_damaged_produce":
        candidates = [i for i in items if i.product.category == "produce"]
    else:
        candidates = list(items)
    return candidates[0] if candidates else (items[0] if items else None)


STAGE_ORDER = ["RISK_ASSESSED", "PICKING", "PICKED", "PACKING", "PACKED", "DISPATCHED", "DELIVERED", "FEEDBACK_RECEIVED"]


def advance_order(db, order, target_stage, pickers_for_wh, riders_for_wh):
    target_idx = STAGE_ORDER.index(target_stage)
    t = order.order_time

    if target_idx >= STAGE_ORDER.index("PICKING"):
        if pickers_for_wh:
            order.picker_id = random.choice(pickers_for_wh).id
        order.status = "PICKING"
        order.picking_started_at = t + datetime.timedelta(minutes=3)

    if target_idx >= STAGE_ORDER.index("PICKED"):
        for oi in order.items:
            oi.picked = True
        order.status = "PICKED"
        order.picking_completed_at = t + datetime.timedelta(minutes=random.randint(6, 18))

    if target_idx >= STAGE_ORDER.index("PACKING"):
        services.get_or_create_packing_plan(db, order)
        order.status = "PACKING"

    if target_idx >= STAGE_ORDER.index("PACKED"):
        order.packing_plan.status = "confirmed"
        order.status = "PACKED"
        order.packing_confirmed_at = order.picking_completed_at + datetime.timedelta(minutes=random.randint(3, 10))

    if target_idx >= STAGE_ORDER.index("DISPATCHED"):
        if riders_for_wh:
            order.rider_id = random.choice(riders_for_wh).id
        di = services.get_or_create_delivery_instruction(db, order)
        di.accepted = True
        di.accepted_at = order.packing_confirmed_at + datetime.timedelta(minutes=2)
        order.status = "DISPATCHED"
        order.dispatched_at = di.accepted_at

    if target_idx >= STAGE_ORDER.index("DELIVERED"):
        order.status = "DELIVERED"
        order.delivered_at = order.dispatched_at + datetime.timedelta(minutes=random.randint(12, 45))

    if target_idx >= STAGE_ORDER.index("FEEDBACK_RECEIVED"):
        p_issue = max(0.02, min(0.55, 0.03 + (order.risk_score or 0) / 100 * 0.35))
        had_issue = random.random() < p_issue
        issue_type = choose_issue_type(order.items) if had_issue else "none"
        rating = random.choice([1, 2, 3]) if had_issue else random.choice([4, 4, 5, 5, 5])
        comments = random.choice(ISSUE_COMMENTS[issue_type]) if had_issue and random.random() < 0.5 else None

        if had_issue:
            damaged = pick_damaged_item(order.items, issue_type)
            if damaged:
                damaged.damaged_reported = True
                damaged.damage_note = comments or issue_type.replace("_", " ")

        db.add(models.Feedback(order_id=order.id, rating=rating, issue_type=issue_type, comments=comments))
        order.status = "FEEDBACK_RECEIVED"


def create_historical_order(db, warehouses, products, pickers, riders, recent: bool):
    warehouse = random.choice(warehouses)
    order_time = (
        datetime.datetime.utcnow() - datetime.timedelta(hours=random.uniform(0.2, 18))
        if recent
        else datetime.datetime.utcnow() - datetime.timedelta(days=random.uniform(1, 14))
    )

    customer = models.Customer(name=random_name())
    db.add(customer)
    db.flush()

    order = models.Order(
        order_code="PENDING",
        customer_id=customer.id,
        warehouse_id=warehouse.id,
        order_time=order_time,
        distance_km=round(random.uniform(1, 18), 1),
        status="CREATED",
    )
    db.add(order)
    db.flush()
    order.order_code = f"FG-{10000 + order.id}"

    for db_item in build_order_items(order, products):
        db.add(db_item)
    db.flush()
    db.refresh(order)
    order.total_weight = services.compute_total_weight(order)
    db.commit()
    db.refresh(order)

    services.run_risk_assessment(db, order)
    db.refresh(order)

    pickers_for_wh = [p for p in pickers if p.warehouse_id == warehouse.id]
    riders_for_wh = [r for r in riders if r.warehouse_id == warehouse.id]

    if recent:
        target = random.choices(
            STAGE_ORDER[:-1],  # not yet at feedback stage, too new
            weights=[10, 20, 15, 15, 15, 15, 10],
        )[0]
    else:
        target = random.choices(["DELIVERED", "FEEDBACK_RECEIVED"], weights=[15, 85])[0]

    advance_order(db, order, target, pickers_for_wh, riders_for_wh)
    db.commit()


def create_demo_order(db, warehouses, products):
    warehouse = next(w for w in warehouses if w.name == "Koramangala Dark Store")
    customer = models.Customer(name="Rahul Gupta")
    db.add(customer)
    db.flush()

    peak_order_time = datetime.datetime.utcnow().replace(hour=19, minute=20, second=0, microsecond=0)
    order = models.Order(
        order_code="PENDING",
        customer_id=customer.id,
        warehouse_id=warehouse.id,
        order_time=peak_order_time,
        distance_km=5.2,
        status="CREATED",
    )
    db.add(order)
    db.flush()
    order.order_code = "FG-10241"

    by_name = {p.name: p for p in products}
    demo_items = [
        ("Tomatoes", 2),
        ("Apples", 6),
        ("Milk 1L", 1),
        ("Glass Sauce Bottle", 1),
        ("Chips", 2),
    ]
    for name, qty in demo_items:
        db.add(models.OrderItem(order_id=order.id, product_id=by_name[name].id, quantity=qty))
    db.flush()
    db.refresh(order)
    order.total_weight = services.compute_total_weight(order)
    db.commit()
    db.refresh(order)

    risk = services.run_risk_assessment(db, order)
    db.commit()
    print(f"Demo order {order.order_code}: risk={risk['riskScore']} ({risk['riskLevel']})")


def main():
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        warehouses, products, pickers, riders = create_reference_data(db)
        db.commit()

        print("Generating historical orders...")
        for i in range(210):
            create_historical_order(db, warehouses, products, pickers, riders, recent=False)
        for i in range(20):
            create_historical_order(db, warehouses, products, pickers, riders, recent=True)

        print("Creating demo order FG-10241...")
        create_demo_order(db, warehouses, products)

        total_orders = db.query(models.Order).count()
        total_feedback = db.query(models.Feedback).count()
        print(f"Done. {total_orders} orders, {total_feedback} feedback records seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
