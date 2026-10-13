"""Severity, repair-cost estimation, recommendation, and claim report.

Implements synopsis stages 7-10:
- 0-100 severity score categorised as Minor / Moderate / Severe (§4.5)
- repair-cost estimation from a predefined part pricing database (§4.6)
- repair recommendation rules (§4.7)
- claim report with decision-support information (§4.8)
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from detection import DAMAGE_BASE_SCORE


PART_PRICING = {
    "Bumper": {"part_cost": 5500, "labour_cost": 1500},
    "Headlight": {"part_cost": 4000, "labour_cost": 900},
    "Door": {"part_cost": 7000, "labour_cost": 1800},
    "Bonnet": {"part_cost": 8500, "labour_cost": 2200},
    "Fender": {"part_cost": 4500, "labour_cost": 1600},
    "Windshield": {"part_cost": 9500, "labour_cost": 2500},
    "Mirror": {"part_cost": 2500, "labour_cost": 600},
    "Unknown Part": {"part_cost": 3500, "labour_cost": 1200},
}

# Synopsis §4.5 typical-damage mapping.
SEVERITY_RANGES = [
    ("Minor", 0, 34),
    ("Moderate", 34, 67),
    ("Severe", 67, 101),
]

# Labour multiplier per severity band (synopsis §4.6 labour cost input).
SEVERITY_LABOUR_FACTOR = {"Minor": 1.0, "Moderate": 1.5, "Severe": 2.2}

DAMAGE_COST_FACTOR = {
    "Scratch": 0.15,
    "Dent": 0.30,
    "Crack": 0.45,
    "Deformation": 0.65,
    "Broken Component": 1.00,
}


def score_detection(damage_type: str, area_ratio: float, confidence: float) -> float:
    base = DAMAGE_BASE_SCORE.get(damage_type, 25)
    area_bonus = min(25.0, area_ratio * 250)
    return min(100.0, base + area_bonus) * (0.6 + 0.4 * confidence)


def classify_severity(score: float) -> str:
    for label, low, high in SEVERITY_RANGES:
        if low <= score < high:
            return label
    return "Severe"


def assess_image(detections: list[dict]) -> dict:
    """Stage 7: severity score for one analysed image."""
    if not detections:
        return {"score": 0.0, "severity": "Minor", "damage_summary": "No damage-suspect regions detected."}

    scores = sorted(
        (score_detection(d["damage_type"], d["area_ratio"], d["confidence"]) for d in detections),
        reverse=True,
    )
    score = scores[0]
    if len(scores) >= 3:
        score = min(100.0, score + 0.15 * scores[1])

    severity = classify_severity(score)
    parts = sorted({d["part"] for d in detections})
    types = sorted({d["damage_type"] for d in detections})
    summary = (
        f"{len(detections)} damage-suspect region(s) across "
        f"{', '.join(parts)}; damage types: {', '.join(types)}."
    )
    return {"score": round(score, 1), "severity": severity, "damage_summary": summary}


def estimate_cost(detections: list[dict], severity: str) -> dict:
    """Stage 8: repair-cost estimation from the predefined pricing database."""
    factor = SEVERITY_LABOUR_FACTOR[severity]
    lines: list[dict] = []
    total = 0.0

    seen: set[tuple[str, str]] = set()
    for detection in detections:
        key = (detection["part"], detection["damage_type"])
        if key in seen:
            continue
        seen.add(key)
        pricing = PART_PRICING.get(detection["part"], PART_PRICING["Unknown Part"])
        cost_factor = DAMAGE_COST_FACTOR.get(detection["damage_type"], 0.3)
        parts_cost = pricing["part_cost"] * cost_factor
        labour_cost = pricing["labour_cost"] * cost_factor * factor
        line_total = parts_cost + labour_cost
        total += line_total
        lines.append({
            "part": detection["part"],
            "damage_type": detection["damage_type"],
            "parts_cost": round(parts_cost, 2),
            "labour_cost": round(labour_cost, 2),
            "subtotal": round(line_total, 2),
        })

    return {
        "currency": "INR",
        "lines": lines,
        "estimated_repair_cost": round(total, 2),
        "basis": "Predefined part pricing database x damage-type and severity factors.",
    }


def recommend_repairs(detections: list[dict], severity: str) -> list[str]:
    """Stage 9 rules from synopsis §4.7."""
    if severity == "Severe":
        return ["Professional inspection"]

    recommendations: list[str] = []
    for detection in detections:
        damage_type = detection["damage_type"]
        if damage_type == "Scratch" and "Paint repair" not in recommendations:
            recommendations.append("Paint repair")
        elif damage_type == "Dent" and "Paintless Dent Repair (PDR)" not in recommendations:
            recommendations.append("Paintless Dent Repair (PDR)")
        elif damage_type in ("Broken Component", "Crack") and "Component replacement" not in recommendations:
            recommendations.append("Component replacement")
    if not recommendations:
        recommendations.append("Professional inspection")
    return recommendations


def build_report(*, claim_id: str, vehicle: dict, accident: dict, image_results: list[dict],
                  severity: dict, cost: dict, recommendations: list[str]) -> dict:
    """Stage 10: claim report with decision-support information."""
    damaged_parts = sorted({d["part"] for r in image_results for d in r["detections"]})
    damage_types = sorted({d["damage_type"] for r in image_results for d in r["detections"]})

    if severity["severity"] == "Severe":
        decision = "Escalate to field surveyor before settlement."
    elif not damaged_parts:
        decision = "No damage detected; verify images manually before proceeding."
    else:
        decision = "Supports standard cashless settlement review."

    return {
        "report_id": f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8].upper()}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_id": claim_id,
        "vehicle": vehicle,
        "accident": accident,
        "damage_summary": {
            "damaged_parts": damaged_parts,
            "damage_types": damage_types,
            "images_analysed": len(image_results),
        },
        "per_image": [
            {
                "upload_id": r["upload_id"],
                "engine": r["engine"],
                "severity": r["severity"],
                "detections": r["detections"],
            }
            for r in image_results
        ],
        "severity": severity,
        "repair_recommendations": recommendations,
        "cost_estimate": cost,
        "claim_decision_support": decision,
        "model_transparency": {
            "engines_used": sorted({d["engine"] for r in image_results for d in r["detections"]}) or ["none"],
            "note": (
                "opencv_heuristic detections are rule-based analysis, not trained-model "
                "predictions; connect a fine-tuned YOLO model for production estimates."
            ),
        },
    }
