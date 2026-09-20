from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from image_pipeline import (
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_CONTENT_TYPES,
    prepare_vehicle_image,
    yolo_inference_status,
)


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = BASE_DIR / "uploads"

app = FastAPI(
    title="AI Insurance Claim Estimator",
    description="AI-powered vehicle damage and insurance claim estimation system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "AI Insurance Claim Estimator API is running!"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/yolo/status")
def yolo_status():
    """Expose the future inference integration without claiming detections."""
    return yolo_inference_status()


@app.post("/api/images/upload")
async def upload_vehicle_image(file: UploadFile = File(...)):
    """Validate and prepare one vehicle image for future damage detection."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please select a vehicle image.")

    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only JPG, JPEG, and PNG vehicle images are supported.",
        )

    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Vehicle images must be 10 MB or smaller.",
        )

    try:
        prepared = prepare_vehicle_image(
            filename=file.filename,
            content=content,
            upload_root=UPLOAD_ROOT,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "prepared",
        "message": "Vehicle image uploaded and prepared for future YOLO inference.",
        "upload_id": prepared.upload_id,
        "original_filename": prepared.original_filename,
        "original_image": {
            "path": f"uploads/original/{prepared.original_path.name}",
            "width": prepared.original_width,
            "height": prepared.original_height,
            "size_bytes": prepared.original_size_bytes,
        },
        "processed_image": {
            "path": f"uploads/processed/{prepared.processed_path.name}",
            "width": prepared.processed_width,
            "height": prepared.processed_height,
            "format": "JPEG",
            "ready_for_yolo": True,
        },
        "yolo": yolo_inference_status(),
    }
