# Fresh_Guard

An AI-powered Quality Assurance MVP for quick-commerce/e-commerce
fulfillment: **Predict → Inspect → Act → Learn.**

> **This is an MVP prototype built on synthetic/simulated data.** It
> validates a product concept, not a production-grade damage-prediction
> or quality-control system. See [Known Limitations](#known-limitations).

- **Predict** — identify which orders/products are more likely to have
  quality issues before fulfillment starts.
- **Inspect** — AI-assisted visual inspection for the specific high-risk
  products a risk-based rule flags, not every item.
- **Act** — turn predictions into concrete pick/pack/delivery instructions
  for pickers, QC reviewers, and delivery partners.
- **Learn** — capture every human decision and customer feedback event so
  future quality intelligence has real outcome data to learn from.

Three lightweight roles — **Operations Manager**, **Picker**, **QC
Reviewer** — switchable from the nav bar (no real auth; see
[MVP additions](#mvp-additions)) — shape which screens are emphasized.

## What Fresh_Guard Is

Fresh_Guard doesn't just predict that an order is risky — it helps the
warehouse verify the actual product before it reaches the customer.

- **Phase 1 — Predict the risk.** Identify which orders are most likely
  to have quality problems *before* they're picked, and tell warehouse
  and delivery teams what to do about that risk.
- **Phase 2 — Inspect the product.** For the specific items a HIGH/CRITICAL
  risk order flagged, let a picker run an AI visual quality check *before*
  packing — catch a bruised tomato or a crushed packet before it ships,
  not after a customer complains.

Extra quality controls are applied only where the AI identifies
meaningful risk — not to every order, and not to every item.

## Problem Statement

Quick-commerce customers often receive damaged, bruised, crushed, or
temperature-sensitive products because warehouse pickers and delivery
partners prioritize speed over careful product handling. Existing quality
checks are largely reactive, leading to customer dissatisfaction, refunds,
product waste, and reduced trust.

## Phase 1 Scope — Order Risk Prediction

**In scope:** a predictive AI risk engine trained on a seeded/synthetic
historical dataset; order-level risk scoring (0–100) built from product,
order-complexity, warehouse-load, picker/handling, delivery, and
temperature-sensitivity risk; explainable risk factors and risk-based
recommendations; a picker workflow, packing plan, delivery handling
screen, and customer feedback capture; an operations dashboard with
analytics; and a feedback loop that stores outcomes for future retraining.

## Phase 2 Scope — AI Computer Vision Quality Inspection

**In scope:** risk-based visual inspection integrated into the existing
picker workflow (not a separate app); a swappable `VisionService`
abstraction; real image-quality validation (brightness/blur/resolution);
category-specific visible-defect detection (produce: bruising/cuts/rot/
deformation; fragile/glass: crack/broken seal/leakage/packaging damage;
packaged goods: crushed packaging/broken seal/leakage/deformation); a
quality score (0–100) and PASS/REVIEW/REJECT decision engine, separate
from the vision model itself; mandatory human review for CRITICAL-risk
orders even on an AI PASS; a reject → replace → reinspect loop with
repeated-failure escalation; a QC human-review queue; inspection history;
and inspection/defect analytics wired into the Phase 1 dashboard.

**Out of scope (explicitly, per the brief):** physical warehouse cameras,
real conveyor/robotic integration, real IoT temperature sensors,
autonomous (human-free) rejection, a custom-trained vision model, and
production-scale CV infrastructure. Fresh_Guard does **not** claim to
detect internal spoilage or any defect that isn't visible in the photo —
the UI always says "visible quality inspection," never "quality
guarantee."

## MVP Additions

Everything above (Phase 1 risk prediction, Phase 2 vision inspection,
picker/packing/delivery/feedback workflow, ~230 seeded orders + ~540 real
seeded inspections) already existed going into the MVP round. What's new
here is turning that into a coherent, navigable **product**, not new
prediction/inspection capability:

- **Role-based navigation** (`frontend/lib/role.tsx`) — a lightweight
  Operations Manager / Picker / QC Reviewer switcher (localStorage, no
  real auth) that reorders the nav bar and sets the default landing route
  per role. Every route stays reachable regardless of role — this is
  about surfacing the right screen first, not access control.
- **`/analytics`** — a dedicated page (separate from the operational
  `/dashboard`) with Quality/AI-Decisions/Defects/Operational sections and
  a 14-day quality trend chart, backed by a single `GET
  /api/analytics/overview` endpoint. Adds metrics that didn't exist
  before: **replacement rate**, **high-risk order rate**, and **customer
  issue rate** as explicit KPIs.
- **Orders search** — search by order code or product name (`?search=`),
  plus a per-order **Inspection Status** column (Not Required / Pending /
  Passed / Issues, computed from that order's non-replaced items).
- **Per-item risk labels** — order detail now shows a LOW/MEDIUM/HIGH/
  CRITICAL badge next to each item's numeric product-risk score, not just
  the number.
- **`.env.example`** (`backend/.env.example`) — `DATABASE_URL`,
  `VISION_MODE`, `VISION_API_KEY`, `MODEL_VERSION`, `DEMO_MODE`, all with
  working defaults. `DEMO_MODE` (default `true`) surfaces as a small
  badge in the nav bar via `GET /api/health`.
- **A committed Playwright end-to-end test**
  (`frontend/e2e/critical-path.spec.ts`) — the brief's most important
  test (order → risk → inspect → REJECT → replace → reinspect → PASS →
  pack → deliver → feedback → analytics), run against the real seeded
  `FG-10241` order through the real UI, not mocked.

**Decisions made without asking**, in order of how much they trade off:
staying on **SQLite** instead of standing up Postgres (schema is already
Postgres-compatible via `DATABASE_URL`; a real Postgres server adds infra
risk to a "must demo reliably" requirement with no functional upside at
this scale); **not renaming** the order-status enum to the brief's
suggested `CREATED/PICKING/INSPECTION_REQUIRED/PACKING/
READY_FOR_DELIVERY/DELIVERED` list, since the existing one (`CREATED →
RISK_ASSESSED → PICKING → PICKED → PACKING → PACKED → DISPATCHED →
DELIVERED → FEEDBACK_RECEIVED`) is a strict superset with finer
granularity and renaming it would touch every router/test/frontend call
site for no behavioral change; and **skipping Docker**, since nothing
here needs it and it was explicitly P2.

## Architecture

```
              ┌───────────────────────┐        ┌───────────────────────────┐
              │   Phase 1: Risk ML    │        │   Phase 2: Vision Service  │
              │  ml/ (GradientBoost)  │        │  backend/app/vision/       │
              │  risk_engine.py       │        │  quality.py (real checks)  │
              │                       │        │  providers/simulation.py   │
              └──────────┬────────────┘        └──────────────┬─────────────┘
                         │                                    │
                         ▼                                    ▼
              recommendations.py                      decision.py (PASS/
              (risk → pick/pack/                        REVIEW/REJECT,
               deliver instructions)                    separate from CV)
                         │                                    │
                         └───────────────┬────────────────────┘
                                         ▼
                         Backend (FastAPI, backend/app/)
                         routers/: orders, picking, packing, delivery,
                         feedback, dashboard, images, inspections, qc,
                         analytics — SQLAlchemy models + SQLite
                                         │
                                         ▼
                         Frontend (Next.js 14 + TypeScript + Tailwind)
                         dashboard, orders, order detail, picker,
                         packing, delivery, feedback, inspection,
                         inspections history, qc/review
```

- **Backend: Python FastAPI** — imports the trained risk model directly
  and runs the vision pipeline in-process; owns all business logic.
- **Frontend: Next.js 14 (App Router) + TypeScript + Tailwind CSS.**
- **Database: SQLite** (Postgres-compatible schema via SQLAlchemy).
- **Risk ML:** scikit-learn, trained standalone in `/ml`.
- **Vision:** a provider-agnostic `VisionService` (see below) — Phase 2
  ships one provider (`simulation`); a real model/API would implement the
  same `VisionProvider` interface without touching any caller.

## AI/ML Approach — Order Risk (Phase 1)

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
5. **Explainability (separate from the model)** — an interpretable
   component breakdown (Product Risk, Order Complexity, Warehouse Risk,
   Delivery Risk, Handling Risk) via transparent weighted formulas, and
   human-readable risk factors from the same features.
6. **Recommendation engine (separate from the model)** —
   `recommendations.py` maps risk level + item-level context to concrete
   pick/pack/delivery instructions, with no dependency on the ML model.
7. **Fallback** — if the model can't load, `risk_engine.py` falls back to
   a rule-based score built from the same weighted components
   (`config.COMPONENT_WEIGHTS`); order creation is **never blocked**.
8. **Configurable thresholds** — risk-level bands and component weights
   live in `backend/app/config.py`, not hard-coded across the app.

## Computer Vision Approach (Phase 2)

**Why introduce computer vision now?** Phase 1 predicts which *orders*
are risky before fulfillment starts. It can't tell you whether the
specific tomato the picker just grabbed is actually bruised. Phase 2
closes that gap at the one moment it's cheapest to act: after picking,
before packing.

**Provider selection.** No labeled defect-image dataset and no vision
API/credentials are available in this environment. Per the brief's
explicit instruction for that situation, Phase 2 ships a clearly-labeled
**"Prototype Vision Simulation"** rather than pretending to have
real-world defect-detection accuracy — but it is not random-number
theater:

- **Image-quality validation is real**, computed from actual pixel data
  (`backend/app/vision/quality.py`, PIL + numpy): mean luminance
  (too dark / overexposed), a Laplacian-variance sharpness proxy (too
  blurry), and resolution (product too small). A poor-quality image is
  never sent to the defect classifier.
- **Defect "detection" is a grounded heuristic**
  (`backend/app/vision/providers/simulation.py`): it measures the
  fraction of the image that is notably darker, brighter, or differently
  hued than the item's dominant color — a real, if crude, proxy for
  bruises, rot, cracks, or crush marks — computed from the actual
  uploaded image, then mapped to a **category-specific** defect type
  (`backend/app/vision/categories.py`: produce vs. fragile-glass vs.
  packaged-goods each have their own defect vocabulary). Confidence and
  severity scale with how large the anomalous area is.
- **The decision engine is separate from both** (`decision.py`):
  PASS/REVIEW/REJECT thresholds live in `config.VISION_DECISION_THRESHOLDS`,
  not inside the vision code. Rule: REJECT requires a low overall score
  **or** a high-severity/high-confidence defect; **low model confidence
  always routes to REVIEW, never REJECT** — the human-in-the-loop
  guarantee from the brief.
- **`VisionService`** (`service.py`) is the only thing routers call —
  swap `SimulationVisionProvider` for a real model/API later by adding a
  new class that implements `VisionProvider.analyze()` and pointing
  `config.VISION_MODE` at it. Nothing else changes.

**Risk-based inspection, not inspect-everything**
(`backend/app/vision/eligibility.py` + `config.INSPECTION_RULES`):

| Order risk | Produce items | Fragile-glass / packaged-goods items |
|---|---|---|
| LOW | not flagged | not flagged |
| MEDIUM | optional if fragility ≥ 50 | optional |
| HIGH | required if fragility ≥ 40, else optional if ≥ 20 | required |
| CRITICAL | required for all | required for all, **+ mandatory human review even on AI PASS** |

Plain (non-glass) dairy is never visually inspected — spoilage/
temperature issues aren't a *visible* defect a camera can assess, which
is also why Fresh_Guard never claims to catch hidden/internal problems.

**Human-in-the-loop, always.** Every inspection shows the score, the
detected defect(s) with confidence framed as High/Medium/Low (never a
bare percentage presented as certainty), and an explicit PASS/REVIEW/
REJECT recommendation — never a bare score. A human can Accept or Reject
any AI result, including overriding a PASS or a REJECT. Overrides are
stored (`human_decision` alongside the untouched `ai_decision`) and
tracked in `/api/analytics/inspections`.

**Reject → replace → reinspect.** Rejecting a product prompts the picker
to pick a replacement (any product in the same category), which gets its
own fresh inspection. Three rejected inspections for the same category
within one order triggers an escalation flag (a manager-alert
recommendation, reusing the Phase 1 `recommendations` table) rather than
looping forever.

**Simulation mode.** `VISION_MODE=simulation` (the default and only
implemented mode) is surfaced in the UI on every inspection screen —
"Prototype Vision Simulation" — so it's never mistaken for a certified
vision model. Eight deterministic sample images (good/bruised/severe
tomato, good/crushed chips, good/cracked glass, dark/blurry — generated
by `data/seed/generate_sample_images.py`, real pixel content, not stock
photos) let you exercise every PASS/REVIEW/REJECT/quality-gate path from
the inspection screen without a camera or real product photos.

## Data Model

SQLAlchemy models in `backend/app/models.py`.

**Phase 1:** `customers`, `warehouses`, `users` (pickers/riders/managers
via `role`), `products`, `orders`, `order_items`, `risk_predictions`
(full scoring history), `recommendations`, `packing_plans`,
`delivery_instructions`, `feedback`.

**Phase 2** (all FK back into Phase 1 entities — no Phase 1 tables were
changed): `inspections` (order/item/product, quality score, AI decision,
human decision, mandatory-review flag, model version, vision mode,
inspection time), `inspection_defects` (type/confidence/severity per
inspection), `inspection_images` (file path + image-quality score/status,
one-way FK to `inspections` to avoid a circular dependency),
`replacement_events` (original/replacement product, reason, linked
inspection), `model_predictions` (raw structured vision output — the
ground-truth/prediction/confidence record a future retraining pipeline
would consume). `order_items` gained `requires_inspection`
(none/recommended/required), `quality_check_status`
(PENDING/PASSED/FAILED), and `replaced`/`replaced_by_item_id` for the
replacement lineage.

## Project Structure

```
fresh_guard/
  ml/                       Phase 1 risk model: synthetic data, training, evaluation
  data/
    images/samples/          8 generated demo inspection photos + manifest.json
    seed/generate_sample_images.py
  backend/
    app/
      main.py                 FastAPI app + router wiring
      config.py                risk + vision thresholds (all configurable)
      models.py / database.py  SQLAlchemy schema + session
      schemas.py                Pydantic request/response models
      risk_engine.py            Phase 1: ML prediction + breakdown + fallback
      recommendations.py        Phase 1: risk -> pick/pack/deliver instructions
      services.py                 Phase 1: order/risk/packing/delivery orchestration
      inspection_service.py       Phase 2: image/inspection/replacement orchestration
      inspection_analytics.py     shared AI-inspection KPI computation
      seed.py                     seeds ~230 historical orders + ~540 real
                                   inspections (run through the actual vision
                                   pipeline) + demo order FG-10241
      vision/                     Phase 2 vision service
        service.py                 VisionService — the only thing routers call
        quality.py                  real image-quality checks (PIL/numpy)
        decision.py                  PASS/REVIEW/REJECT, separate from the model
        categories.py                 category -> defect-group/type mapping
        eligibility.py                 risk level -> inspection required/recommended
        storage.py                     local image storage behind an interface
        providers/simulation.py        the "Prototype Vision Simulation" provider
        providers/base.py               VisionProvider interface for a future real provider
      routers/                    orders, picking, packing, delivery, feedback,
                                   dashboard, reference (Phase 1); images,
                                   inspections, qc, analytics (Phase 2)
    tests/                       pytest: 50 tests across both phases
    .env.example                 DATABASE_URL, VISION_MODE, VISION_API_KEY,
                                  MODEL_VERSION, DEMO_MODE
  frontend/
    app/                         dashboard, orders, orders/[id], picker,
                                  packing/[orderId], delivery/[orderId],
                                  feedback/[orderId] (Phase 1); inspection/
                                  [orderId]/[itemId], inspections, qc/review
                                  (Phase 2); analytics (MVP)
    components/                  RiskBadge/RiskGauge (Phase 1);
                                  InspectionStatusBadge/QualityScoreGauge (Phase 2)
    lib/api.ts                   typed fetch client for the backend
    lib/role.tsx                 role-based nav (MVP)
    e2e/critical-path.spec.ts    Playwright end-to-end test (MVP)
    playwright.config.ts
```

## API

**Phase 1:**
```
POST   /api/orders                          create order (runs risk assessment automatically)
GET    /api/orders                           list orders (filter: risk_level, warehouse_id, status,
                                               date, search — order code or product name)
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
GET    /api/dashboard                          KPIs + analytics (now includes an ai_inspection summary)
GET    /api/products, /api/warehouses, /api/users   reference data
```

**Phase 2:**
```
POST   /api/images/upload                    multipart file upload (validates size/format, runs quality check)
POST   /api/images/upload-sample              {sample_key} — "captures" a bundled demo photo
GET    /api/images/samples                    list bundled sample images
GET    /api/images/:id/file                   raw image bytes

POST   /api/inspections                      {order_id, order_item_id, image_id} — create (PENDING)
GET    /api/inspections                       list (filter: order_id, order_item_id, product_id,
                                                defect_type, status, warehouse_id, min_confidence, date)
GET    /api/inspections/:id                    detail (defects, image, review info)
POST   /api/inspections/:id/image              attach/replace the image on a PENDING inspection
POST   /api/inspections/:id/analyze            run the vision pipeline -> quality score + defects + decision
POST   /api/inspections/:id/accept             human ACCEPT (may override AI)
POST   /api/inspections/:id/reject             human REJECT (may override AI)
POST   /api/inspections/:id/review             force into the review queue
POST   /api/inspections/:id/reinspect          fresh attempt on the SAME item (e.g. bad photo)
POST   /api/inspections/:id/replace            {replacement_product_id, reason} — reject -> new item + inspection

GET    /api/qc/review-queue                   inspections awaiting human decision
GET    /api/analytics/inspections              inspected/passed/review/rejected, reject rate,
                                                human override rate + transition breakdown, avg quality
                                                score, avg inspection time, most common defect
GET    /api/analytics/defects                  defects by type/category/SKU/warehouse/day
```

**MVP:**
```
GET    /api/analytics/overview                single-fetch payload for /analytics: quality
                                                (damage-free/customer-issue rate, rejected products,
                                                inspection volume), ai (pass/review/reject, overrides),
                                                defects by type, operational (avg inspection time,
                                                replacement rate, high-risk order rate), 14-day
                                                quality trend
GET    /api/health                            {status, demoMode, visionMode, modelVersion}
```

## How to Run Locally

Requires Python 3.11+ and Node 20+.

```bash
# 1. Risk ML pipeline (already run once — dataset.csv/model.pkl/metrics.json are committed)
cd ml
pip install -r requirements.txt
python3 generate_dataset.py
python3 train_model.py
python3 evaluate.py

# 2. Vision sample images (already generated and committed under data/images/samples/)
cd ../data/seed
python3 generate_sample_images.py

# 3. Backend
cd ../../backend
pip install -r requirements.txt
cp .env.example .env       # optional — every value has a working default
python3 -m app.seed        # resets the DB; seeds ~230 orders + ~540 real inspections + demo order FG-10241
python3 -m uvicorn app.main:app --reload --port 8000

# 4. Frontend (separate terminal)
cd ../frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000 — it redirects to `/dashboard`.

## How to Train the Risk Model

```bash
cd ml
python3 generate_dataset.py   # regenerate dataset.csv
python3 train_model.py        # trains + saves model.pkl, holds out 20% to holdout.csv
python3 evaluate.py           # scores model.pkl on holdout.csv, writes metrics.json
python3 predict.py            # quick CLI sanity check against one example feature vector
```

## How to Upload / Test Inspection Images

On any `/inspection/:orderId/:itemId` screen:

- **Capture Image** opens the device camera on mobile (`capture="environment"`)
  or a file picker on desktop.
- **Upload Image** opens a plain file picker (JPEG/PNG/WebP, ≤ 8MB).
- **Prototype Vision Simulation** quick-picks let you "capture" one of the 8
  bundled sample photos instead — the fastest way to see every PASS/
  REVIEW/REJECT/poor-image-quality path without a real product photo.

To add your own permanent sample images, edit `data/seed/generate_sample_images.py`
and rerun it — or drop any real photo into the upload flow; the same
real image-quality checks and heuristic defect detection run on it.

## How to Evaluate the Vision Model

There's no separate offline evaluation script for Phase 2 (unlike the
Phase 1 risk model) because there's no labeled ground-truth defect
dataset in this environment — the honest thing to evaluate here is the
**pipeline**, which the test suite does:

```bash
cd backend
python3 -m pytest tests/test_vision.py -v
```

For a live/manual read on how the simulation is behaving, `GET
/api/analytics/inspections` reports **model behavior** (inspected/passed/
review/rejected counts, reject rate, avg quality score, avg inspection
time) and **human-in-the-loop metrics** (human-reviewed count, override
rate, and the full AI→human transition breakdown: PASS→REJECT,
REJECT→ACCEPT, REVIEW→ACCEPT, REVIEW→REJECT) — kept as two distinct
things, per the brief. A future real evaluation would need an
`{image, product, ground_truth, prediction, confidence, human_decision}`
dataset (the `model_predictions` table already stores the prediction/
confidence/raw-result half of that) and would report precision/recall/F1
alongside business metrics (false-accept rate, false-reject rate,
inspection time) — **not** the same thing as a damage-reduction claim,
which needs a real before/after experiment.

## How to Start the Application

See "How to Run Locally" above — backend on `:8000`, frontend on `:3000`.
Run `python3 -m app.seed` again any time to reset the database to a clean
demo state (it recreates all tables and reseeds, including inspections).

## Demo Workflow

The seeded database includes a polished demo order, **FG-10241**
(2 Tomatoes, 6 Apples, 1 Milk, 1 Glass Sauce Bottle, 2 Chips), created at
a peak hour in a near-saturated warehouse. It scores **~65, HIGH risk**.
Tomatoes, Glass Sauce Bottle, and Chips are flagged **required** for AI
inspection; Apples is **optional**; Milk isn't visually inspectable.

Walk it end-to-end without touching the database:

1. **Dashboard** (`/dashboard`) — operational KPIs + the AI Inspection
   summary and defect charts.
2. **Orders** (`/orders`) → **Order detail** (`/orders/:id`) — risk gauge,
   breakdown, factors, recommendations, and a per-item AI Inspection column.
3. **Picker** (`/picker`) — select `FG-10241`, start picking. Tomatoes/
   Glass Sauce/Chips show a red **Inspect with AI** button; Apples shows
   an outlined **(optional)** one; Milk shows no inspect button.
4. Click **Inspect with AI** on Tomatoes → use the **"Tomato — severe
   visible damage"** sample → quality score ~22, **REJECT** (bruising,
   high confidence) → **Reject** → pick a replacement product → **Scan
   Replacement** → you land on a fresh inspection for the new item → use
   the **"Tomato — no visible defect"** sample → **PASS** → **Accept**.
5. Back on the order, inspect Glass Sauce Bottle with the **"intact"**
   sample → PASS → Accept. Back to **Picker**, mark items picked, complete.
6. **Packing** (`/packing/:orderId`) — the replaced (bruised) tomato line
   is excluded from the bag plan; confirm.
7. **Delivery** (`/delivery/:orderId`) — accept instructions, mark delivered.
8. **Feedback** (`/feedback/:orderId`) — submit; reflected on the dashboard.
9. **Inspection History** (`/inspections`) and **QC Review Queue**
   (`/qc/review`) — see the reject/pass pair you just created, plus ~540
   seeded historical inspections (all run through the real pipeline, not
   fabricated numbers) for realistic analytics.

## Testing

```bash
# Backend (pytest)
cd backend
python3 -m pytest tests/ -v

# Frontend end-to-end (Playwright) — needs BOTH servers running (see
# "How to Run Locally") and a fresh `python3 -m app.seed`, since the test
# consumes FG-10241's pristine state exactly like a real demo would.
cd frontend
npx playwright test
```

**50 backend tests** (all passing):

- **Phase 1 (20):** risk-level bands, rule-based fallback, bounded
  component scores; API validation (missing warehouse/product, invalid
  quantity, missing risk prediction, duplicate feedback, 404s); one full
  create→risk→pick→pack→deliver→feedback→dashboard workflow test.
- **Phase 2 (30):** image-quality gate (valid/invalid/dark/blurry/too-small),
  vision analysis (PASS/REVIEW/REJECT via the real simulation pipeline),
  decision-engine rules (high-confidence defect → REJECT, low-confidence
  defect never auto-rejects → REVIEW, multiple defects, no-defect PASS);
  image upload validation (too large, unsupported format); human review
  (accept AI PASS, override AI REJECT, confirm AI REJECT, REVIEW-queue
  resolution); the replacement loop (reject → replace → reinspect → pass,
  plus a guard against replacing without a rejection); and one full
  order→risk→inspect→reject→replace→reinspect→pass→packing (replaced
  item correctly excluded)→delivery→feedback→analytics test.

**1 Playwright end-to-end test** (`frontend/e2e/critical-path.spec.ts`,
passing) drives the exact same critical path through the real rendered
UI, clicking real buttons against the real FG-10241 demo order: risk →
pick → inspect → REJECT (bruising) → replace → reinspect → PASS → accept
→ pack → deliver → feedback → analytics — with no manual database
intervention at any step.

## MVP Success Criteria

All pass against a freshly-seeded database, verified both via the
Playwright test above and manually in a real browser:

- [x] Select a role (Operations Manager / Picker / QC Reviewer)
- [x] Open dashboard, see operational quality metrics
- [x] Open an order, understand its risk (score, factors, recommendations)
- [x] Start picking
- [x] Inspect a high-risk product with AI
- [x] Receive a quality score, defect, confidence, and PASS/REVIEW/REJECT
- [x] Accept/reject/review the product (human-in-the-loop)
- [x] Replace a rejected product
- [x] Reinspect the replacement
- [x] Complete picking
- [x] Follow packing recommendations
- [x] Complete delivery
- [x] Submit customer feedback
- [x] See analytics update — no manual DB edits anywhere in the loop

## Known Limitations

**General:**
- **No auth/multi-tenancy**, single shared dataset — out of scope for a
  concept prototype. Role switching (Operations Manager/Picker/QC
  Reviewer) only changes nav emphasis and the default landing route; it
  is not access control — every route stays reachable from every role.
- **SQLite, single-process** — fine locally; would need Postgres +
  connection pooling for concurrent multi-user use.
- **Next.js 14.2.x, not the latest.** `npm audit` flags advisories fixed
  only in Next.js 15/16; since this runs locally and isn't publicly
  deployed, we stayed on the latest 14.x patch rather than a breaking
  migration mid-build. Upgrade before any real deployment.

**Phase 1 (risk model):**
- All historical/training data is synthetic. Reported metrics describe
  the pipeline working correctly on synthetic validation data, not
  real-world accuracy.

**Phase 2 (vision) — read this before treating any inspection result as
real:**
- **This is a simulation, not a trained defect classifier.** The
  "Prototype Vision Simulation" heuristic (pixel-anomaly area vs. the
  item's dominant color) has no relationship to a real computer-vision
  model's accuracy. It will not generalize to arbitrary real photos the
  way a trained model would.
- **No hidden/internal defects.** Spoilage, internal bruising, or
  anything not visible in the photo is explicitly out of scope — the UI
  always says "visible quality inspection."
- **Lighting and camera-angle sensitive.** The brightness/blur/anomaly
  checks are simple pixel statistics; unusual lighting, shadows, or
  reflections can trigger false quality-gate failures or false defect
  signals that a trained model would likely handle better.
- **No product variation modeling.** The heuristic doesn't know what a
  tomato is *supposed* to look like beyond "close to its own dominant
  color" — it can't distinguish natural variation (a yellow-shouldered
  tomato) from an actual defect the way a model trained on real labeled
  examples could.
- **No bounding boxes.** The brief is explicit that fabricated
  localization is worse than none — Phase 2 reports a defect *type* and
  confidence, never a made-up bounding box, since no real localization
  model is in use.
- **Packing "modify" is a simple bag reassignment UI**, not a full
  drag-and-drop packing simulator.

## Future Phases

- **Phase 3 — Temperature & Cold-Chain Intelligence** *(recommended
  next)*: real IoT sensor integration for cold-chain items, closing the
  gap Phase 2 explicitly can't — Milk and other dairy items are excluded
  from visual inspection today precisely because temperature/spoilage
  risk isn't visible in a photo. This directly extends Phase 1's existing
  temperature-sensitivity risk factor and Phase 2's category-eligibility
  logic, and is more foundational to trust in the product than packing
  optimization.
- **Phase 4 — Advanced Smart Packing Optimization**: builds on both the
  risk-based packing plan (Phase 1) and inspection outcomes (Phase 2),
  but is an efficiency improvement rather than a new trust/quality
  capability — reasonable to sequence after cold-chain.
- **Phase 5 — Real warehouse/logistics integrations** (WMS, live GPS,
  route optimization, real camera/hardware integration for Phase 2).
- **Phase 6 — Continuous learning & production ML monitoring**: retrain
  the risk model and (once a real vision provider exists) the vision
  model on real outcome data captured via the feedback loops already
  built in Phases 1–2, with drift monitoring and model versioning.
