# ClaimAI — AI-Powered Insurance Claim Estimator

## Damage detection and classification

The current implementation uses a trained **YOLO11n damage detector** when the bundled model is available. It accepts 1–8 JPG, PNG, or WEBP vehicle images and detects four SYNDCAR damage classes: broken glass, cracks, scratches, and broken lights. The system maps detector confidence and bounding-box size to the project severity classes:

- **Minor**: score below 0.40 — light visual damage signals such as scratches or small dents
- **Moderate**: score from 0.40 to 0.67 — stronger deformation/crack/impact signals
- **Severe**: score 0.68 or above — strong structural or heavily deformed visual signals

The overall claim severity is the most severe classification across the uploaded images. The review page displays each image score, detected region, aggregate score, and the engine disclaimer.

If the YOLO package or model is unavailable, the backend automatically falls back to the explainable edge-and-texture baseline. This keeps the application runnable while making the model dependency explicit.

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

Open `http://localhost:5173`, start a claim, complete the vehicle and accident forms, upload at least one image, and select **Continue to Review**.

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

## Integrated workflow

1. Vehicle details and accident details are captured in the claim flow and retained in browser storage.
2. The image-upload step validates and previews 1–8 vehicle images.
3. `POST /api/analyze-claim` validates the files and runs YOLO11n, with the baseline as fallback.
4. Each image receives a damaged-part label, normalized damage score, severity, and repair estimate.
5. Overall severity is the highest severity across all images.
6. Repair costs are consolidated by unique damaged part; multiple photos of the same part do not multiply the final estimate.
7. The review screen displays per-image detections, overall severity, unique damaged parts, parts cost, labour cost, and total INR estimate.

For local verification, the frontend build/lint and the backend multipart workflow should both pass before presenting the project.

## YOLO model and training

The bundled model is `ml-models/syndcar-damage/weights/best.pt`. It was fine-tuned from YOLO11n for 30 epochs on the public SYNDCAR dataset, which provides 245 images and YOLO-format damage labels. The training split used 171 images, with 49 validation images and 25 test images. The final validation mAP50 was approximately 0.67 on the held-out validation split.

The training dataset is not stored in GitHub because its published ZIP is approximately 3.2 GB. To retrain, download SYNDCAR from [Mendeley Data](https://data.mendeley.com/datasets/hzpj48krdt/1), extract it into `ml-data/SYNDCAR`, install `ultralytics`, prepare the 70/20/10 split, and run Ultralytics training with `data_damage.yaml`. The dataset is intended for research and educational use under its published license.

The model is suitable for academic demonstration, not for making real insurance claim decisions. Real deployment would require a larger representative dataset, independent testing, calibration, and expert review.

## Damage type, recommendation, and report

The integrated review now also classifies the baseline visual signal as scratch, dent, crack, broken component, or deformation. Each type maps to a repair recommendation such as paint repair, PDR, component replacement, or professional inspection. The user can download a JSON claim assessment report containing vehicle details, accident details, detections, severity, recommendations, and the itemized repair estimate.
