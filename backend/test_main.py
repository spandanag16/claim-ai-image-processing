import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app
from image_pipeline import MAX_FILE_SIZE_BYTES


client = TestClient(app)


def image_bytes(image_format: str, size: tuple[int, int] = (320, 180)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, (80, 90, 100)).save(output, format=image_format)
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "content_type", "image_format"),
    [
        ("front.jpg", "image/jpeg", "JPEG"),
        ("side.jpeg", "image/jpeg", "JPEG"),
        ("rear.png", "image/png", "PNG"),
        ("closeup.webp", "image/webp", "WEBP"),
    ],
)
def test_valid_vehicle_images_are_prepared(tmp_path: Path, monkeypatch, filename, content_type, image_format):
    monkeypatch.setattr("main.UPLOAD_ROOT", tmp_path / "uploads")
    response = client.post(
        "/api/images/upload",
        files={"file": (filename, image_bytes(image_format), content_type)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "prepared"
    assert payload["processed_image"]["ready_for_yolo"] is True
    assert payload["processed_image"]["width"] == 640
    assert payload["processed_image"]["height"] == 640
    assert (tmp_path / "uploads" / "original" / f"{payload['upload_id']}{Path(filename).suffix}").exists()
    assert (tmp_path / "uploads" / "processed" / f"{payload['upload_id']}.jpg").exists()
    assert payload["yolo"]["status"] == "configured"
    assert payload["yolo"]["detections"] == []


def test_invalid_extension_is_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("main.UPLOAD_ROOT", tmp_path / "uploads")
    response = client.post(
        "/api/images/upload",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415


def test_mismatched_image_content_is_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("main.UPLOAD_ROOT", tmp_path / "uploads")
    response = client.post(
        "/api/images/upload",
        files={"file": ("fake.jpg", image_bytes("PNG"), "image/jpeg")},
    )
    assert response.status_code == 400
    assert "extension" in response.json()["detail"]


def test_missing_file_is_rejected():
    response = client.post("/api/images/upload")
    assert response.status_code == 422


def test_oversized_file_is_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("main.UPLOAD_ROOT", tmp_path / "uploads")
    oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)
    response = client.post(
        "/api/images/upload",
        files={"file": ("large.jpg", oversized, "image/jpeg")},
    )
    assert response.status_code == 413


def test_yolo_status_reports_real_engine():
    response = client.get("/api/yolo/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "yolo_configured"
    assert payload["detections"] == []


def test_full_analysis_pipeline(tmp_path: Path, monkeypatch):
    import io
    import numpy as np
    import cv2

    monkeypatch.setattr("main.UPLOAD_ROOT", tmp_path / "uploads")

    # Synthetic damaged-vehicle-style image: base + bright scratch band + dark blob.
    frame = np.full((480, 800, 3), 90, np.uint8)
    frame[100:400, 80:720] = (60, 70, 130)
    cv2.line(frame, (150, 180), (620, 210), (240, 240, 240), 6)
    cv2.circle(frame, (400, 320), 60, (20, 20, 30), -1)
    buffer = io.BytesIO()
    Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).save(buffer, format="JPEG")

    upload = client.post(
        "/api/images/upload",
        files={"file": ("damaged.jpg", buffer.getvalue(), "image/jpeg")},
    )
    assert upload.status_code == 200
    payload = upload.json()
    assert payload["ai_ready_image"] is not None
    assert (tmp_path / "uploads" / "ai_ready" / f"{payload['upload_id']}.jpg").exists()

    response = client.post(
        "/api/analysis/run",
        json={
            "claim_id": "CLAIM-TEST-1",
            "upload_ids": [payload["upload_id"]],
            "vehicle": {"manufacturer": "Hyundai", "model": "i20"},
            "accident": {"type": "Minor collision"},
        },
    )
    assert response.status_code == 200
    report = response.json()["report"]
    assert 0 <= report["severity"]["score"] <= 100
    assert report["severity"]["severity"] in {"Minor", "Moderate", "Severe"}
    assert report["cost_estimate"]["estimated_repair_cost"] >= 0
    assert report["repair_recommendations"]
    assert report["claim_decision_support"]
    assert report["model_transparency"]["engines_used"]

    stored = client.get("/api/claims/CLAIM-TEST-1/report")
    assert stored.status_code == 200
    assert stored.json()["report"]["report_id"] == report["report_id"]


def test_analysis_rejects_unknown_upload():
    response = client.post("/api/analysis/run", json={"upload_ids": ["missing-id"]})
    assert response.status_code == 404


def test_analysis_requires_one_to_eight_uploads():
    empty_response = client.post("/api/analysis/run", json={"upload_ids": []})
    assert empty_response.status_code == 422

    multiple_response = client.post(
        "/api/analysis/run", json={"upload_ids": [f"upload-{index}" for index in range(9)]}
    )
    assert multiple_response.status_code == 422


def test_cost_estimate_consolidates_same_part_across_damage_types():
    import analysis

    detections = [
        {"part": "Door", "damage_type": "Scratch", "area_ratio": 0.02, "confidence": 0.8},
        {"part": "Door", "damage_type": "Dent", "area_ratio": 0.04, "confidence": 0.8},
        {"part": "Bumper", "damage_type": "Crack", "area_ratio": 0.03, "confidence": 0.8},
    ]
    result = analysis.estimate_cost(detections, "Moderate")

    assert len(result["lines"]) == 2
    assert {line["part"] for line in result["lines"]} == {"Door", "Bumper"}


def test_structural_damage_is_not_downgraded_by_low_confidence_or_small_area():
    import analysis

    result = analysis.assess_image([
        {
            "part": "Door",
            "damage_type": "Deformation",
            "area_ratio": 0.01,
            "confidence": 0.45,
        }
    ])

    assert result["score"] >= 68
    assert result["severity"] == "Severe"


def test_authenticity_screen_flags_editing_metadata_and_duplicates():
    import authenticity

    output = io.BytesIO()
    image = Image.new("RGB", (64, 64), (120, 120, 120))
    image.save(output, format="JPEG", comment=b"created with Photoshop")
    first = authenticity.inspect_image(output.getvalue())
    second = authenticity.inspect_image(output.getvalue())
    results = authenticity.compare_duplicates([first, second])

    assert results[0]["status"] == "review_required"
    assert results[0]["risk_score"] >= 40
    assert any("similar" in flag for flag in results[1]["flags"])
