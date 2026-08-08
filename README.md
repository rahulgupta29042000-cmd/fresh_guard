# Fresh_Guard

AI-powered quality-risk prediction and handling-guidance platform for
quick-commerce/e-commerce fulfillment.

> **Phase 1 uses synthetic data and is a prototype for validating the
> product concept.** It is not a production-ready damage-prediction
> system. See [Known Limitations](#known-limitations).

## What Fresh_Guard Is

Fresh_Guard identifies which orders are most likely to have quality
problems — damaged, bruised, crushed, or temperature-mishandled items —
**before** they're picked, and tells warehouse and delivery teams exactly
what to do about that risk: which items need careful handling, how to pack
the order, and what instructions the delivery partner needs. It applies
extra quality controls only where the AI identifies meaningful risk,
instead of treating every order the same way.

## Problem Statement

Quick-commerce customers often receive damaged, bruised, crushed, or
temperature-sensitive products because warehouse pickers and delivery
partners prioritize speed over careful product handling. Existing quality
checks are largely reactive, leading to customer dissatisfaction, refunds,
product waste, and reduced trust.

The opportunity is to use AI to predict quality risks and provide timely
picking, packing, and delivery-handling recommendations — improving
product quality without significantly compromising delivery speed.

## Phase 1 Scope

**In scope:** a predictive AI risk engine trained on a seeded/synthetic
historical dataset; order-level risk scoring (0–100) built from product,
order-complexity, warehouse-load, picker/handling, delivery, and
temperature-sensitivity risk; explainable risk factors and risk-based
recommendations; a picker workflow, packing plan, delivery handling
screen, and customer feedback capture; an operations dashboard with
analytics; and a feedback loop that stores outcomes for future retraining.

**Out of scope (future phases):** computer vision / real camera QC, real
IoT temperature sensors, robotics/autonomous warehouse or delivery
systems, real payments, real logistics/GPS integrations, and
production-scale ML infrastructure.

## Architecture

Two services, kept deliberately simple:

```
Synthetic Dataset (ml/generate_dataset.py)
        ↓
Feature Engineering + Model Training (ml/train_model.py)
        ↓
model.pkl  ──────────────────────────────┐
                                          ↓
                              Backend (FastAPI, backend/app/)
                              ├─ risk_engine.py   → loads model.pkl directly,
                              │                      computes interpretable
                              │                      component breakdown,
                              │                      rule-based fallback
                              ├─ recommendations.py → decision engine
                              │                      (separate from the model)
                              ├─ routers/*.py       → orders, picking, packing,
                              │                      delivery, feedback,
                              │                      dashboard
                              └─ models.py (SQLAlchemy) + SQLite
                                          ↓
                              Frontend (Next.js 14 + TypeScript + Tailwind)
                              7 screens: dashboard, orders, order detail,
                              picker, packing, delivery, feedback
```

- **Backend: Python FastAPI**, not Next.js API routes — the backend
  imports the trained scikit-learn model directly (no cross-language
  shelling out) and owns all business logic.
- **Frontend: Next.js 14 (App Router) + TypeScript + Tailwind CSS**,
  calling the backend over HTTP (`NEXT_PUBLIC_API_URL`).
- **Database: SQLite** for local development (Postgres-compatible schema
  via SQLAlchemy — swapping the `DATABASE_URL` is enough to move to
  Postgres later).
- **ML: scikit-learn**, trained standalone in `/ml`, loaded once by the
  backend at prediction time.

## AI/ML Approach

1. **Synthetic dataset** (`ml/generate_dataset.py`) — ~7,000 historical
   orders generated with realistic, hand-specified correlations (fragile
   items → more damage, high warehouse load → more damage, longer
   distance → more damage, temperature-sensitive items → more risk,
   inexperienced/lower-quality-score pickers and riders → more risk),
   plus random noise, producing a binary `had_quality_issue` label.
2. **Training** (`ml/train_model.py`) — a `GradientBoostingClassifier`
   (scikit-learn) trained on a 17-feature vector (order size/complexity,
   product fragility/temperature-sensitivity/historical damage rate,
   warehouse load + peak-hour flag, picker experience/quality/speed,
   rider experience/rating, distance). Saved to `ml/model.pkl`.
3. **Evaluation** (`ml/evaluate.py`) — accuracy/precision/recall/F1/
   ROC-AUC + confusion matrix on a held-out 20% split, saved to
   `ml/metrics.json`. Current prototype numbers (synthetic validation
   data only): **accuracy 0.83, precision 0.76, recall 0.67, F1 0.71,
   ROC-AUC 0.89**. These describe the modeling pipeline working
   end-to-end — **not** a real-world accuracy claim.
4. **Prediction** — `risk_engine.py` builds the same feature vector from
   live order/warehouse/picker/rider data, calls the model, and scales
   the predicted probability to a 0–100 **Damage Risk Score**.
5. **Explainability (separate from the model)** — `risk_engine.py` also
   computes an interpretable component breakdown (Product Risk, Order
   Complexity, Warehouse Risk, Delivery Risk, Handling Risk) via
   transparent weighted formulas, and derives human-readable risk factors
   from the same underlying features. This is what the "Risk Breakdown"
   and "Top Risk Factors" panels show — the app never presents a bare
   score with no explanation.
6. **Recommendation engine (separate from the model)** —
   `recommendations.py` maps risk level + item-level context (fragile,
   temperature-sensitive, produce, lightweight) to concrete pick/pack/
   delivery instructions. It has no dependency on the ML model, so it
   keeps working even if the model fails to load.
7. **Fallback** — if the model can't be loaded or prediction throws,
   `risk_engine.py` falls back to a rule-based score built from the same
   weighted components (`config.COMPONENT_WEIGHTS`), and order creation
   is **never blocked** by an AI failure — see `services.run_risk_assessment`.
8. **Configurable thresholds** — risk-level bands (LOW 0–30, MEDIUM
   31–60, HIGH 61–80, CRITICAL 81–100) and component weights live in
   `backend/app/config.py`, not hard-coded across the app.

Wording throughout the UI says "Predicted damage risk", never "this order
will be damaged" — predictions always show the score, model version,
source (AI vs. rule-based fallback), contributing factors, and
recommended action, and a human can always override by continuing the
standard workflow.

## Data Model

SQLAlchemy models in `backend/app/models.py`:

`customers`, `warehouses`, `users` (pickers/riders/managers via `role`),
`products`, `orders`, `order_items`, `risk_predictions` (full scoring
history — score, factors, component scores, model version, source),
`recommendations`, `packing_plans`, `delivery_instructions`, `feedback`.

`orders` holds the *latest* `risk_score`/`risk_level` for fast listing;
`risk_predictions` keeps every assessment (including re-assessments after
a picker is assigned) for audit/history.

## Project Structure

```
fresh_guard/
  ml/                       synthetic data, training, evaluation, prediction
    generate_dataset.py
    train_model.py
    evaluate.py
    predict.py
    feature_schema.py       canonical feature list shared by all of the above
    dataset.csv / model.pkl / metrics.json   (generated — already included)
  backend/
    app/
      main.py                FastAPI app + router wiring
      config.py               risk thresholds, component weights (configurable)
      models.py / database.py SQLAlchemy schema + session
      schemas.py               Pydantic request/response models
      risk_engine.py           ML prediction + interpretable breakdown + fallback
      recommendations.py       risk-based decision engine (separate from the model)
      services.py               order/risk/packing/delivery orchestration
      seed.py                   synthetic historical orders + demo order FG-10241
      routers/                  orders, picking, packing, delivery, feedback, dashboard, reference
    tests/                     pytest: risk engine, API, full e2e workflow
  frontend/
    app/                       dashboard, orders, orders/[id], picker,
                                packing/[orderId], delivery/[orderId], feedback/[orderId]
    components/                RiskBadge, RiskGauge, NavBar, StatCard, States
    lib/api.ts                 typed fetch client for the backend
```

## API

```
POST   /api/orders                          create order (runs risk assessment automatically)
GET    /api/orders                           list orders (filter: risk_level, warehouse_id, status, date)
GET    /api/orders/:id                        order detail (items + latest risk)
GET    /api/orders/:id/risk                    latest risk result
POST   /api/orders/:id/recalculate-risk        re-run the risk engine (e.g. after picker assignment)
GET    /api/orders/:id/recommendations         current recommendations

POST   /api/orders/:id/picking                 {action: start | mark_item_picked | report_damaged | complete}
GET    /api/orders/:id/packing-plan            AI-generated bag-by-bag packing plan
POST   /api/orders/:id/packing                 {action: confirm | modify | report_issue}
GET    /api/orders/:id/delivery                delivery handling instructions
POST   /api/orders/:id/delivery                {action: accept_instructions | mark_delivered}
POST   /api/orders/:id/feedback                customer feedback

GET    /api/dashboard                          KPIs + analytics
GET    /api/products, /api/warehouses, /api/users   reference data
```

## How to Run Locally

Requires Python 3.11+ and Node 20+.

```bash
# 1. ML pipeline (already run once — dataset.csv/model.pkl/metrics.json are committed)
cd ml
pip install -r requirements.txt
python3 generate_dataset.py
python3 train_model.py
python3 evaluate.py

# 2. Backend
cd ../backend
pip install -r requirements.txt
python3 -m app.seed        # resets the DB and seeds ~230 historical orders + demo order FG-10241
python3 -m uvicorn app.main:app --reload --port 8000

# 3. Frontend (separate terminal)
cd ../frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000 — it redirects to `/dashboard`.

## How to Train the Model

```bash
cd ml
python3 generate_dataset.py   # regenerate dataset.csv
python3 train_model.py        # trains + saves model.pkl, holds out 20% to holdout.csv
python3 evaluate.py           # scores model.pkl on holdout.csv, writes metrics.json
python3 predict.py            # quick CLI sanity check against one example feature vector
```

The backend automatically picks up a re-trained `model.pkl` on next
restart (or immediately, since it's loaded lazily on first prediction).

## How to Start the Application

See "How to Run Locally" above — backend on `:8000`, frontend on `:3000`.
Run `python3 -m app.seed` again any time to reset the database to a clean
demo state (it recreates all tables and reseeds).

## Demo Workflow

The seeded database includes a polished demo order, **FG-10241**
(2 Tomatoes, 6 Apples, 1 Milk, 1 Glass Sauce Bottle, 2 Chips), created at
a peak hour in a near-saturated warehouse. It scores **~65, HIGH risk**,
driven by the fragile glass bottle, the temperature-sensitive milk, order
size, and warehouse load — with recommendations to inspect the tomatoes,
handle the glass bottle separately, keep the milk protected, keep the
chips on top, and alert the delivery partner.

Walk it end-to-end without touching the database:

1. **Dashboard** (`/dashboard`) — see the operational KPIs.
2. **Orders** (`/orders`) — find `FG-10241`, filter by risk level.
3. **Order detail** (`/orders/:id`) — see the risk gauge, component
   breakdown, top risk factors, and recommended actions.
4. **Picker** (`/picker`) — select the order, start picking, mark each
   item picked (fragile/temperature-sensitive items are flagged), complete.
5. **Packing** (`/packing/:orderId`) — review the AI-generated bag plan
   (Fragile / Cold / Produce / Lightweight), confirm or modify it.
6. **Delivery** (`/delivery/:orderId`) — review handling instructions,
   accept them, mark delivered.
7. **Feedback** (`/feedback/:orderId`) — submit customer feedback; it's
   immediately reflected back on the dashboard.

## Testing

```bash
cd backend
python3 -m pytest tests/ -v
```

20 tests: risk-engine unit tests (LOW/MEDIUM/HIGH/CRITICAL bands,
rule-based fallback, bounded component scores), API tests (validation,
missing warehouse/product, missing risk prediction, duplicate feedback,
404s), and one full `create → risk → pick → pack → deliver → feedback →
dashboard` end-to-end test.

## Known Limitations

- **Synthetic data.** All historical/training data is generated, not
  real operational data. Model metrics describe the pipeline working
  correctly on synthetic validation data, not real-world accuracy.
- **No auth/multi-tenancy.** Single shared dataset, no login, no
  per-warehouse/per-role access control — out of scope for a Phase 1
  product-concept prototype.
- **SQLite, single-process.** Fine for a local prototype; would need
  Postgres + connection pooling for concurrent multi-user use.
- **Next.js 14.2.x, not the latest.** `npm audit` flags advisories fixed
  only in Next.js 15/16; since this prototype runs locally and isn't
  publicly deployed, we stayed on the latest 14.x patch to avoid a
  breaking App Router migration mid-build. Upgrade before any real
  deployment.
- **No computer vision / IoT / real logistics integrations** — explicitly
  deferred to later phases (see below).
- **Packing "modify" is a simple bag reassignment UI**, not a full
  drag-and-drop packing simulator.

## Future Phases

- **Phase 2 — Computer Vision QC:** product camera → image → vision
  model → defect detection → quality score → pass/reject, feeding into
  the same risk pipeline.
- **Phase 3 — Temperature intelligence:** real IoT sensor integration for
  cold-chain items.
- **Phase 4 — Advanced packing optimization.**
- **Phase 5 — Real warehouse/logistics integrations** (WMS, live GPS,
  route optimization).
- **Phase 6 — Continuous learning & production ML monitoring:** retrain
  on real outcome data captured via the feedback loop already built in
  Phase 1, with drift monitoring and model versioning in production.
