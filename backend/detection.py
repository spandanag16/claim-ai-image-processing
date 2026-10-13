"""Damage detection for prepared vehicle images.

Two engines, chosen honestly by `image_pipeline.model_status`:

1. A fine-tuned YOLO model (CLAIMAI_YOLO_MODEL=... .pt) when configured.
2. A classical OpenCV fallback that finds damage-suspect regions using edge
   density, colour discontinuity, and elongated-contour heuristics, then maps
   each region to a vehicle part using its position in the frame.

The fallback is NOT a trained model and its output is labelled
`engine: "opencv_heuristic"` everywhere so results are never overstated.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np


VEHICLE_PARTS = ["Bumper", "Headlight", "Door", "Bonnet", "Fender", "Windshield", "Mirror"]
DAMAGE_TYPES = ["Scratch", "Dent", "Crack", "Broken Component", "Deformation"]

# Base severity weights per synopsis §4.5 (minor -> severe).
DAMAGE_BASE_SCORE = {
    "Scratch": 15,
    "Dent": 30,
    "Crack": 45,
    "Broken Component": 70,
    "Deformation": 60,
}


@dataclass
class Detection:
    part: str
    damage_type: str
    confidence: float
    box: tuple[int, int, int, int]  # x1, y1, x2, y2 in 640x640 space
    area_ratio: float  # fraction of the frame the region covers
    engine: str


def _region_to_part(x1: int, y1: int, x2: int, y2: int, frame: int = 640) -> str:
    """Map a damage region to a vehicle part from its relative position."""
    cx, cy = (x1 + x2) / 2 / frame, (y1 + y2) / 2 / frame
    w_ratio = (x2 - x1) / frame

    if cy > 0.78 and w_ratio > 0.45:
        return "Bumper"
    if cy < 0.30 and 0.20 < cx < 0.80:
        return "Windshield" if w_ratio > 0.35 else "Bonnet"
    if cy < 0.45 and (cx < 0.22 or cx > 0.78):
        return "Headlight"
    if 0.30 <= cy <= 0.78 and (cx < 0.18 or cx > 0.82):
        return "Fender"
    if 0.25 <= cy <= 0.80:
        return "Door"
    return "Mirror" if w_ratio < 0.12 else "Bumper"


def _classify_damage(contour, region: np.ndarray, gray_region: np.ndarray) -> tuple[str, float]:
    """Heuristic damage-type guess with a soft confidence."""
    x, y, w, h = cv2.boundingRect(contour)
    area = cv2.contourArea(contour)
    box_area = max(w * h, 1)
    aspect = max(w, h) / max(min(w, h), 1)
    extent = area / box_area
    solidity = area / max(cv2.contourArea(cv2.convexHull(contour)), 1)

    edges = cv2.Canny(gray_region, 60, 160)
    edge_density = float(np.count_nonzero(edges)) / max(region.shape[0] * region.shape[1], 1)

    if aspect > 6 and min(w, h) < 25:
        return "Scratch", 0.62
    if extent < 0.35 and aspect > 3:
        return "Crack", 0.55
    if edge_density > 0.22 and solidity < 0.80:
        return "Broken Component", 0.50
    if aspect < 2.5 and 0.45 < extent < 0.85 and edge_density > 0.08:
        return "Dent", 0.58
    if extent < 0.60:
        return "Deformation", 0.48
    return "Dent", 0.45


def detect_with_opencv(image_path: Path) -> list[Detection]:
    """Find damage-suspect regions in one AI-ready 640x640 image."""
    image = cv2.imread(str(image_path))
    if image is None:
        return []
    image = cv2.resize(image, (640, 640))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 40, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections: list[Detection] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 700 or area > 0.55 * 640 * 640:
            continue
        x1, y1, x2, y2 = cv2.boundingRect(contour)
        if x2 - x1 < 30 or y2 - y1 < 20:
            continue

        region = image[y1:y2, x1:x2]
        gray_region = gray[y1:y2, x1:x2]

        damage_type, base_conf = _classify_damage(contour, region, gray_region)
        conf = min(0.85, base_conf + min(area / (640 * 640) * 2, 0.15))
        detections.append(Detection(
            part=_region_to_part(x1, y1, x2, y2),
            damage_type=damage_type,
            confidence=round(float(conf), 2),
            box=(int(x1), int(y1), int(x2), int(y2)),
            area_ratio=round(area / (640 * 640), 4),
            engine="opencv_heuristic",
        ))

    detections.sort(key=lambda d: d.area_ratio, reverse=True)
    return detections[:6]


def detect_with_yolo(image_path: Path, model_path: str) -> list[Detection]:
    """Run a fine-tuned YOLO damage model; class names come from the model."""
    model = _load_yolo_model(model_path)
    results = model.predict(str(image_path), conf=0.35, verbose=False)
    detections: list[Detection] = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        for box, score, cls_id in zip(
            boxes.xyxy.tolist(), boxes.conf.tolist(), boxes.cls.tolist()
        ):
            x1, y1, x2, y2 = [int(v) for v in box]
            name = str(result.names[int(cls_id)])
            detections.append(Detection(
                part=name if name in VEHICLE_PARTS else _region_to_part(x1, y1, x2, y2),
                damage_type=_map_class_to_damage(name),
                confidence=round(float(score), 2),
                box=(x1, y1, x2, y2),
                area_ratio=round((x2 - x1) * (y2 - y1) / (640 * 640), 4),
                engine="yolo",
            ))
    return detections


@lru_cache(maxsize=4)
def _load_yolo_model(model_path: str):
    """Load each configured checkpoint once per worker process."""
    from ultralytics import YOLO

    return YOLO(model_path)


def _map_class_to_damage(class_name: str) -> str:
    """Map common YOLO class-name conventions to the report damage taxonomy."""
    lowered = class_name.lower().replace("_", " ").replace("-", " ")
    for damage_type in DAMAGE_TYPES:
        if damage_type.lower() in lowered:
            return damage_type
    keyword_map = {
        "scratch": "Scratch",
        "dent": "Dent",
        "crack": "Crack",
        "broken": "Broken Component",
        "break": "Broken Component",
        "lamp": "Broken Component",
        "glass": "Crack",
        "shatter": "Crack",
        "tire": "Deformation",
        "tyre": "Deformation",
        "deform": "Deformation",
    }
    for keyword, damage_type in keyword_map.items():
        if keyword in lowered:
            return damage_type
    return "Scratch"


def _map_class_to_part(class_name: str) -> str:
    lowered = class_name.lower()
    for part in VEHICLE_PARTS:
        if part.lower().replace(" ", "") in lowered.replace(" ", ""):
            return part
    return "Unknown Part"


def detect(image_path: Path) -> dict[str, object]:
    """Entry point used by the analysis service."""
    default_model = Path(__file__).resolve().parent / "models" / "vehicle_damage.pt"
    model_path = os.environ.get("CLAIMAI_YOLO_MODEL", "") or str(default_model)
    engine = "opencv_heuristic"
    try:
        if model_path and Path(model_path).exists():
            engine = "yolo"
            detections = detect_with_yolo(image_path, model_path)
        else:
            detections = detect_with_opencv(image_path)
    except Exception:
        # Any YOLO failure falls back without breaking the claim flow.
        engine = "opencv_heuristic"
        detections = detect_with_opencv(image_path)

    return {
        "engine": engine,
        "model_note": (
            "Classical OpenCV heuristics; not a trained damage model."
            if engine == "opencv_heuristic"
            else "Fine-tuned YOLO model inference."
        ),
        "detections": [asdict(d) for d in detections],
    }
