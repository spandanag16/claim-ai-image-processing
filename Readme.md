# AI-Powered Automated Insurance Claim Estimator

React/Vite frontend + FastAPI backend for the college project. This branch (`spandana-image-processing`) implements the full synopsis pipeline: claim creation, vehicle/accident details, image collection, preprocessing, damage detection, severity assessment, repair-cost estimation, recommendations, and the claim report.

## Pipeline

```text
Create claim (vehicle details)
        ↓
Accident details (date/time, location, type, description)
        ↓
Upload one vehicle image
        ↓
Validation → original preserved → 640×640 letterbox (PIL)
        ↓
OpenCV noise reduction + normalization → uploads/ai_ready/
        ↓
Damage detection (YOLO if configured, else OpenCV heuristics)
        ↓
Damage type + vehicle part + confidence + bounding box
        ↓
Severity score 0-100 → Minor / Moderate / Severe
        ↓
Repair cost from predefined pricing database (parts + labour)
        ↓
Repair recommendation → claim report → saved to SQLite
```

## Backend modules

| File | Synopsis stage |
| --- | --- |
| `image_pipeline.py` | 4 — validation, resize, OpenCV denoise/normalize |
| `detection.py` | 5, 6 — YOLO adapter + OpenCV fallback, part & damage-type mapping |
| `analysis.py` | 7, 8, 9, 10 — severity, cost estimation, recommendations, report |
| `database.py` | SQLite persistence for generated claim reports |

## Detection engine (honest status)

`GET /api/yolo/status` reports the real engine. Without a trained model the
service runs **classical OpenCV heuristics** and labels every detection
`engine: "opencv_heuristic"` — these are rule-based regions, not trained-model
predictions, and no accuracy is claimed.

This branch includes a fine-tuned YOLO11m vehicle-damage checkpoint at
`backend/models/vehicle_damage.pt`. It detects `dent`, `scratch`, `crack`,
`shattered_glass`, `broken_lamp`, and `flat_tire`. The backend loads this
checkpoint automatically. To use another compatible model, set:

```bash
export CLAIMAI_YOLO_MODEL=backend/models/vehicle_damage.pt
pip install ultralytics
```

`detection.detect()` then runs YOLO inference instead of heuristics; the rest
of the pipeline is unchanged.

The repository installs the `ultralytics` runtime and includes the trained
checkpoint under the model author's MIT license. A general COCO YOLO model
must not be used as a damage model because its classes do not represent
scratches, dents, or broken parts. If the bundled or configured checkpoint
cannot be loaded, the API reports `cv_fallback` and labels its results as
heuristic.

The checkpoint was obtained from the public
[YOLO11m Car Body Damage Detector repository](https://github.com/ReverendBayes/YOLO11m-Car-Damage-Detector).
Its published model metrics are not independently reproduced by this project;
claims should therefore be treated as assistive estimates and reviewed by a
human.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/images/upload` | Validate + preprocess one image |
| `POST` | `/api/analysis/run` | Detect damage, score severity, estimate cost, build report |
| `GET` | `/api/claims/{claim_id}/report` | Fetch the stored claim report |
| `GET` | `/api/yolo/status` | Real detection-engine status |
| `GET` | `/health` | Health check |

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173/`. The Vite dev server proxies `/api` to
`http://127.0.0.1:8000`; set `VITE_BACKEND_URL` to point elsewhere.

## Testing

```bash
cd backend && pytest -q          # upload validation, preprocessing, full analysis pipeline
cd frontend && npm run build
cd frontend && npm run lint
```

## Pricing database

`analysis.PART_PRICING` holds INR part + labour baselines for Bumper, Headlight,
Door, Bonnet, Fender, Windshield and Mirror. Severity bands apply labour
multipliers (1.0 / 1.5 / 2.2) and damage types apply cost factors, per synopsis
§4.6. These are demo baselines, not insurer-approved rates.

## Remaining work

- Collect an annotated vehicle-damage dataset and train/validate YOLO; record real metrics.
- Replace heuristic part mapping with model-predicted parts.
- Validate cost factors against actual repair-shop data.
- Authentication, claim history UI, MySQL deployment.

## Explanation for the project guide

The claim flow starts with vehicle and accident details, then collects damage
photographs. Each image is validated, preserved, resized to 640×640, and passed
through OpenCV noise reduction and contrast normalization. The prepared image
goes to the damage-detection stage, which reports damaged parts, damage type,
bounding box and confidence. Those detections produce a 0-100 severity score
(Minor/Moderate/Severe), a repair-cost estimate from the part pricing database,
a repair recommendation, and a claim report stored in the database. YOLO is
wired in as an adapter: the moment a fine-tuned model is available it replaces
the heuristic engine with no other code changes.
