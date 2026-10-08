# ClaimAI — AI-Powered Insurance Claim Estimator

## Damage detection and classification

The current implementation includes an explainable **baseline computer-vision engine**. It accepts 2–8 JPG, PNG, or WEBP vehicle images, detects the strongest high-texture/high-edge region as a potential damaged panel, and classifies each image as:

- **Minor**: score below 0.40 — light visual damage signals such as scratches or small dents
- **Moderate**: score from 0.40 to 0.67 — stronger deformation/crack/impact signals
- **Severe**: score 0.68 or above — strong structural or heavily deformed visual signals

The overall claim severity is the most severe classification across the uploaded images. The review page displays each image score, detected region, aggregate score, and the engine disclaimer.

> This is a project baseline for demonstration. A production or real insurance workflow should replace `analyze_image` in `backend/main.py` with a trained detector/classifier validated on a labeled vehicle-damage dataset.

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, start a claim, complete the vehicle and accident forms, upload at least two images, and select **Continue to Review**.

## API

- `GET /health` — backend status
- `POST /api/analyze-claim` — multipart request with repeated `files` fields

The analysis response contains `overall_severity`, `overall_score`, `average_score`, and per-image `results` with a normalized bounding box, confidence, severity, and visual signals.

## Repair estimation

Each detected region is mapped to a likely part for the prototype (front bumper, hood, fender, door panel, or body panel). The estimator then applies severity multipliers to the base catalog:

| Severity | Parts multiplier | Labour multiplier |
|---|---:|---:|
| Minor | 35% | 50% |
| Moderate | 70% | 85% |
| Severe | 100% | 130% |

The review page shows per-image parts cost, labour cost, and total cost, plus a combined estimate in INR. The catalog and multipliers are defined in `backend/main.py` and should be replaced with local workshop/insurer rates for a real deployment.
