from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import analysis
import database
import detection
from image_pipeline import (
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_CONTENT_TYPES,
    model_status,
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

database.init_db()

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
    """Report the real detection-engine status."""
    return {**model_status(), "detections": []}


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
        "ai_ready_image": (
            f"uploads/ai_ready/{prepared.ai_ready_path.name}"
            if prepared.ai_ready_path
            else None
        ),
        "yolo": yolo_inference_status(),
    }


class AnalyzeRequest(BaseModel):
    claim_id: str = "CLAIM-LOCAL"
    upload_ids: list[str] = Field(min_length=1, max_length=1)
    vehicle: dict = Field(default_factory=dict)
    accident: dict = Field(default_factory=dict)


@app.post("/api/analysis/run")
def run_analysis(request: AnalyzeRequest):
    """Full pipeline for one previously uploaded image."""
    image_results = []
    for upload_id in request.upload_ids[:8]:
        ai_ready = UPLOAD_ROOT / "ai_ready" / f"{upload_id}.jpg"
        processed = UPLOAD_ROOT / "processed" / f"{upload_id}.jpg"
        image_path = ai_ready if ai_ready.exists() else processed
        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Prepared image {upload_id} not found.")

        result = detection.detect(image_path)
        result["upload_id"] = upload_id
        result["severity"] = analysis.assess_image(result["detections"])
        image_results.append(result)

    # Claim-level severity: weighted blend of the worst images.
    scores = sorted((r["severity"]["score"] for r in image_results), reverse=True)
    claim_score = scores[0] if len(scores) == 1 else min(100.0, scores[0] * 0.85 + scores[1] * 0.15)
    severity_label = analysis.classify_severity(claim_score)
    severity = {
        "score": round(claim_score, 1),
        "severity": severity_label,
        "damage_summary": " | ".join(
            r["severity"]["damage_summary"] for r in image_results if r["detections"]
        ) or "No damage-suspect regions detected.",
    }

    all_detections = [d for r in image_results for d in r["detections"]]
    cost = analysis.estimate_cost(all_detections, severity_label)
    recommendations = analysis.recommend_repairs(all_detections, severity_label)
    report = analysis.build_report(
        claim_id=request.claim_id,
        vehicle=request.vehicle,
        accident=request.accident,
        image_results=image_results,
        severity=severity,
        cost=cost,
        recommendations=recommendations,
    )
    report["analysis_row_id"] = database.save_analysis(request.claim_id, report)
    return {"status": "completed", "model": model_status(), "report": report}


@app.get("/api/claims/{claim_id}/report")
def claim_report(claim_id: str):
    report = database.get_analysis(claim_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No analysis found for this claim.")
    return {"status": "found", "report": report}
