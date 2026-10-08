"""ClaimAI backend: upload vehicle images and classify visible damage severity.

This is an explainable baseline computer-vision pipeline. It detects high-texture/
edge regions as potential damage and maps the resulting score to minor, moderate,
or severe. It is intentionally structured so a trained detector can replace
`analyze_image` later without changing the frontend API.
"""

from io import BytesIO
from typing import Annotated

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

app = FastAPI(
    title="AI Insurance Claim Estimator",
    description="Vehicle damage detection and severity classification API",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_IMAGES = 8
MAX_FILE_SIZE = 10 * 1024 * 1024
SEVERITIES = ("minor", "moderate", "severe")

PART_CATALOG = {
    "front bumper": {"parts_cost": 8500, "labour_cost": 2500},
    "rear bumper": {"parts_cost": 8500, "labour_cost": 2500},
    "hood": {"parts_cost": 12000, "labour_cost": 3500},
    "door panel": {"parts_cost": 18000, "labour_cost": 5000},
    "fender": {"parts_cost": 7000, "labour_cost": 2500},
    "headlight": {"parts_cost": 7000, "labour_cost": 1500},
    "body panel": {"parts_cost": 9000, "labour_cost": 3000},
}

SEVERITY_MULTIPLIERS = {
    "minor": {"parts": 0.35, "labour": 0.50},
    "moderate": {"parts": 0.70, "labour": 0.85},
    "severe": {"parts": 1.00, "labour": 1.30},
}


def classify_severity(score: float) -> str:
    """Map a normalized visual-damage score to the three project classes."""
    if score < 0.40:
        return "minor"
    if score < 0.68:
        return "moderate"
    return "severe"


def infer_part(x1: float, y1: float, x2: float, y2: float) -> str:
    """Infer a likely body part from the strongest image region.

    This spatial mapping is a baseline. A trained detector should return the
    actual part label and bounding box in a production implementation.
    """
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    if center_y > 0.72:
        return "front bumper"
    if center_y < 0.25:
        return "hood"
    if center_x < 0.30:
        return "fender"
    if center_x > 0.70:
        return "door panel"
    return "body panel"


def estimate_repair(part: str, severity: str) -> dict:
    """Calculate itemized parts, labour, and total repair costs in INR."""
    base = PART_CATALOG.get(part, PART_CATALOG["body panel"])
    multiplier = SEVERITY_MULTIPLIERS[severity]
    parts_cost = round(base["parts_cost"] * multiplier["parts"])
    labour_cost = round(base["labour_cost"] * multiplier["labour"])
    return {
        "part": part,
        "severity": severity,
        "parts_cost": parts_cost,
        "labour_cost": labour_cost,
        "total_cost": parts_cost + labour_cost,
        "currency": "INR",
    }


def analyze_image(image: Image.Image) -> dict:
    """Return explainable baseline detections for one image.

    High local edges and texture are useful first-pass signals for scratches,
    dents, cracks, and broken contours. This is not a substitute for a trained
    vehicle-damage dataset/model; the response labels this method explicitly.
    """
    image = image.convert("RGB")
    image.thumbnail((640, 640))
    rgb = np.asarray(image, dtype=np.float32) / 255.0
    gray = rgb.mean(axis=2)

    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    edge_signal = float(np.clip((gx + gy) * 7.0, 0.0, 1.0))
    texture_signal = float(np.clip(gray.std() * 2.2, 0.0, 1.0))

    # Scan a 4x4 grid and keep the strongest local candidate region.
    height, width = gray.shape
    tiles = []
    for row in range(4):
        for col in range(4):
            y1, y2 = row * height // 4, (row + 1) * height // 4
            x1, x2 = col * width // 4, (col + 1) * width // 4
            tile = gray[y1:y2, x1:x2]
            if tile.size == 0:
                continue
            local_edges = 0.0
            if tile.shape[1] > 1:
                local_edges += float(np.abs(np.diff(tile, axis=1)).mean())
            if tile.shape[0] > 1:
                local_edges += float(np.abs(np.diff(tile, axis=0)).mean())
            local_score = float(np.clip(local_edges * 9.0 + tile.std() * 1.5, 0.0, 1.0))
            tiles.append((local_score, x1 / width, y1 / height, x2 / width, y2 / height))

    tiles.sort(reverse=True, key=lambda item: item[0])
    local_score, x1, y1, x2, y2 = tiles[0]
    damage_score = round(float(np.clip(0.55 * local_score + 0.30 * edge_signal + 0.15 * texture_signal, 0.0, 1.0)), 3)
    severity = classify_severity(damage_score)
    part = infer_part(x1, y1, x2, y2)
    repair_estimate = estimate_repair(part, severity)

    return {
        "damage_score": damage_score,
        "severity": severity,
        "detections": [
            {
                "label": "potential damaged vehicle panel",
                "part": part,
                "confidence": round(max(0.5, damage_score), 3),
                "severity": severity,
                "bbox": [round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3)],
            }
        ],
        "signals": {
            "edge_signal": round(edge_signal, 3),
            "texture_signal": round(texture_signal, 3),
        },
        "repair_estimate": repair_estimate,
    }


@app.get("/")
def root():
    return {"message": "AI Insurance Claim Estimator API is running!"}


@app.get("/health")
def health():
    return {"status": "healthy", "analysis_engine": "baseline-computer-vision"}


@app.post("/api/analyze-claim")
async def analyze_claim(files: Annotated[list[UploadFile], File(...)]):
    """Analyze 2–8 vehicle images and return per-image and overall severity."""
    if not 2 <= len(files) <= MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Upload between 2 and {MAX_IMAGES} images.")

    results = []
    for file in files:
        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=400, detail=f"{file.filename} must be JPG, PNG, or WEBP.")
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"{file.filename} is larger than 10 MB.")
        try:
            image = Image.open(BytesIO(content))
            image.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a readable image.") from exc

        analysis = analyze_image(image)
        results.append({"filename": file.filename, **analysis})

    worst = max(results, key=lambda result: result["damage_score"])
    overall = worst["severity"]
    average_score = round(sum(item["damage_score"] for item in results) / len(results), 3)
    total_repair_estimate = {
        "parts_cost": sum(item["repair_estimate"]["parts_cost"] for item in results),
        "labour_cost": sum(item["repair_estimate"]["labour_cost"] for item in results),
        "total_cost": sum(item["repair_estimate"]["total_cost"] for item in results),
        "currency": "INR",
    }

    return {
        "overall_severity": overall,
        "overall_score": round(worst["damage_score"], 3),
        "average_score": average_score,
        "repair_estimate": total_repair_estimate,
        "images_analyzed": len(results),
        "results": results,
        "engine": "baseline-computer-vision",
        "disclaimer": "Prototype estimate. Replace the baseline with a trained detector before production or real claim decisions.",
    }
