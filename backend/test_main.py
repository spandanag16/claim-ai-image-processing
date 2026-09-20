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
    assert payload["yolo"]["status"] == "not_configured"
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


def test_yolo_status_is_explicitly_not_configured():
    response = client.get("/api/yolo/status")
    assert response.status_code == 200
    assert response.json()["status"] == "not_configured"
