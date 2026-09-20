# AI-Powered Automated Insurance Claim Estimator

This repository contains the existing React/Vite frontend and FastAPI backend for the college project. The `spandana-image-processing` branch extends the existing three-step claim flow with a real vehicle-image input and preparation pipeline.

## Current implementation

The current workflow is:

```text
Vehicle image selected in React
        ↓
Local preview and client-side JPG/JPEG/PNG + 10 MB validation
        ↓
Multipart upload to FastAPI
        ↓
Server-side MIME, extension, size, and image-content validation
        ↓
Original image saved with a UUID filename
        ↓
Separate 640 × 640 RGB/JPEG image created with aspect-ratio-preserving padding
        ↓
JSON response marks the processed image ready for future YOLO inference
```

The original upload is never overwritten. Generated files are written under `backend/uploads/original/` and `backend/uploads/processed/` during local development; those directories are ignored by Git.

The existing frontend route is `http://localhost:5173/new-claim/images`. The backend endpoint is:

```text
POST http://127.0.0.1:8000/api/images/upload
Content-Type: multipart/form-data
Field: file
```

The endpoint returns the upload ID, original dimensions and path, processed dimensions and path, and an explicit YOLO status. The current status is `not_configured` with an empty `detections` list. No trained model or damage result is claimed.

## Planned YOLO stage

YOLO is being considered because it can perform object detection in a single image pass and return both class predictions and bounding boxes. For this project, possible classes could include damaged bumper, damaged bonnet, damaged door, damaged fender, broken headlight, cracked windshield, and damaged mirror. The final class list should be decided from the dataset rather than assumed in advance.

A training dataset will require representative vehicle images with annotations. Each damaged region should have a bounding box and a class label in the format required by the selected YOLO implementation. The box describes the damaged region using its image coordinates. During inference, the model would return a class, a box, and a confidence score. A confidence threshold can filter uncertain detections, but the threshold must be selected and evaluated using validation data.

The later insurance-estimation stage can combine detected parts, box size or region characteristics, confidence-aware rules, and other claim information to estimate severity. Repair-cost estimation must be designed and validated separately; a bounding box alone is not a repair price and this branch does not fabricate cost, accuracy, dataset, or training results.

## Setup

### Backend

From the repository root:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- API root: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`
- Upload: `POST http://127.0.0.1:8000/api/images/upload`
- YOLO integration status: `GET http://127.0.0.1:8000/api/yolo/status`

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173/`

The frontend already uses Axios in `frontend/api.js`; no new frontend package was needed.

## Testing

Backend tests are in `backend/test_main.py` and cover JPG, JPEG, PNG, invalid extension/type, mismatched image content, missing file, oversized file, 640 × 640 preprocessing, preservation of original files, and explicit YOLO-not-configured behavior.

Run them with:

```bash
cd backend
pytest -q
```

Build and lint the frontend with:

```bash
cd frontend
npm run lint
npm run build
```

## Current versus future work

### Currently implemented

- Existing React claim steps remain in place.
- Image selection, drag-and-drop, previews, removal, and an eight-image limit remain in the frontend.
- JPG, JPEG, and PNG validation is performed in the browser and again in the backend.
- A 10 MB per-image limit is enforced.
- Uploaded files receive safe unique names and originals are preserved.
- A separate padded 640 × 640 RGB/JPEG preparation is generated.
- Upload/loading/success/error states are shown in the image step.
- A review screen summarizes preparation and explicitly reports that YOLO is not configured.

### Planned / future work

- Select or collect a labeled vehicle-damage dataset.
- Define and review the final vehicle-part and damage-class taxonomy.
- Train and validate a YOLO model; record real evaluation metrics only after experiments.
- Replace the status-only YOLO interface with an actual model adapter.
- Map validated detections to severity rules and then to a separately validated insurance estimate.

## Project-guide explanation

I implemented the vehicle-image input pipeline inside the existing claim flow. The user selects and previews vehicle photos, and the frontend uploads them to FastAPI as multipart files. The backend checks the file type and size, verifies that the content is a real supported image, saves the original safely, and creates a separate normalized 640 × 640 image for future computer-vision inference. YOLO is being considered because it can locate damaged vehicle parts with bounding boxes and confidence scores. The next development step is to prepare an annotated dataset, train and validate a YOLO model, and then connect its real detections to damage severity and insurance estimation.
