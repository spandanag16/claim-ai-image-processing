"""Vehicle-image preparation utilities for the insurance claim workflow.

This module intentionally stops before model inference. It produces a clean,
letterboxed image that a future YOLO service can consume while preserving the
user's original upload unchanged.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import cv2
    import numpy as np
except ImportError:  # OpenCV is optional; the pipeline falls back to PIL output.
    cv2 = None
    np = None


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
YOLO_INPUT_SIZE = (640, 640)
DEFAULT_YOLO_MODEL = Path(__file__).resolve().parent / "models" / "vehicle_damage.pt"


@dataclass(frozen=True)
class PreparedImage:
    """Metadata produced after an image is validated and prepared."""

    upload_id: str
    original_filename: str
    original_path: Path
    processed_path: Path
    ai_ready_path: Path | None
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int
    original_size_bytes: int


def cv_refine_image(padded_path: Path, ai_ready_path: Path) -> bool:
    """Synopsis §4.2 stage: OpenCV noise reduction + normalization.

    Operates on the already-padded 640x640 image and writes a separate
    AI-ready file so the YOLO-format padded image stays untouched.
    """
    if cv2 is None:
        return False

    image = cv2.imread(str(padded_path), cv2.IMREAD_COLOR)
    if image is None:
        return False

    # Edge-preserving noise reduction.
    denoised = cv2.fastNlMeansDenoisingColored(image, None, h=7, hColor=7,
                                                templateWindowSize=7, searchWindowSize=21)
    denoised = cv2.bilateralFilter(denoised, d=5, sigmaColor=40, sigmaSpace=40)

    # Normalize contrast per channel (CLAHE in LAB space keeps colour stable).
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    l_channel = cv2.normalize(l_channel, None, 0, 255, cv2.NORM_MINMAX)
    l_channel = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l_channel)
    normalized = cv2.cvtColor(cv2.merge((l_channel, a_channel, b_channel)), cv2.COLOR_LAB2BGR)

    # Final 0-1 float normalization is what a model tensor would use; the
    # stored JPEG keeps the uint8 form for inspection and classic-CV analysis.
    success = cv2.imwrite(str(ai_ready_path), normalized)
    return bool(success)


def _safe_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only JPG, JPEG, PNG, and WEBP vehicle images are supported.")
    return extension


def _validate_image_bytes(content: bytes, extension: str) -> tuple[int, int]:
    """Validate file content, not only the browser-provided MIME type."""
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            detected_format = image.format
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("The uploaded file is not a readable image.") from exc

    expected_formats = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".webp": "WEBP",
    }
    if detected_format != expected_formats[extension]:
        raise ValueError("The file extension does not match its image content.")
    return width, height


def prepare_vehicle_image(
    *, filename: str, content: bytes, upload_root: Path
) -> PreparedImage:
    """Validate, preserve, and prepare one vehicle image for future YOLO use."""
    if not content:
        raise ValueError("The uploaded image is empty.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValueError("Vehicle images must be 10 MB or smaller.")

    extension = _safe_extension(filename)
    width, height = _validate_image_bytes(content, extension)

    upload_id = uuid4().hex
    original_dir = upload_root / "original"
    processed_dir = upload_root / "processed"
    ai_ready_dir = upload_root / "ai_ready"
    original_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    ai_ready_dir.mkdir(parents=True, exist_ok=True)

    original_path = original_dir / f"{upload_id}{extension}"
    processed_path = processed_dir / f"{upload_id}.jpg"
    ai_ready_path = ai_ready_dir / f"{upload_id}.jpg"
    original_path.write_bytes(content)

    try:
        with Image.open(original_path) as image:
            # RGB conversion makes PNG/RGBA input safe for JPEG output.
            prepared = ImageOps.pad(
                image.convert("RGB"),
                YOLO_INPUT_SIZE,
                method=Image.Resampling.LANCZOS,
                color=(114, 114, 114),
                centering=(0.5, 0.5),
            )
            prepared.save(processed_path, format="JPEG", quality=92, optimize=True)
        cv_applied = cv_refine_image(processed_path, ai_ready_path)
    except (UnidentifiedImageError, OSError) as exc:
        original_path.unlink(missing_ok=True)
        processed_path.unlink(missing_ok=True)
        ai_ready_path.unlink(missing_ok=True)
        raise ValueError("The uploaded image could not be prepared.") from exc

    return PreparedImage(
        upload_id=upload_id,
        original_filename=Path(filename).name,
        original_path=original_path,
        processed_path=processed_path,
        ai_ready_path=ai_ready_path if cv_applied else None,
        original_width=width,
        original_height=height,
        processed_width=YOLO_INPUT_SIZE[0],
        processed_height=YOLO_INPUT_SIZE[1],
        original_size_bytes=len(content),
    )


def model_status() -> dict[str, object]:
    """Honest report of the damage-detection stage.

    A fine-tuned YOLO model can be enabled with CLAIMAI_YOLO_MODEL=path/to.pt.
    Until then detection runs on classical OpenCV heuristics, which is stated
    explicitly instead of pretending a trained model exists.
    """
    import os

    configured_path = os.environ.get("CLAIMAI_YOLO_MODEL", "")
    model_path = configured_path or str(DEFAULT_YOLO_MODEL)
    if model_path and Path(model_path).exists():
        try:
            from ultralytics import YOLO  # optional dependency

            YOLO(model_path)
            return {
                "status": "yolo_configured",
                "model": model_path,
                "message": "Fine-tuned YOLO model loaded for damage detection.",
            }
        except Exception as exc:  # ultralytics missing or model unusable
            return {
                "status": "yolo_error",
                "model": model_path,
                "message": f"YOLO model could not be loaded: {exc}",
            }
    return {
        "status": "cv_fallback",
        "model": None,
        "message": (
            "No trained YOLO damage model is configured; classical OpenCV "
            "heuristics analyze the image and report damage-suspect regions."
        ),
    }


def yolo_inference_status() -> dict[str, object]:
    """Return the honest integration status for the YOLO stage."""
    status = model_status()
    if status["status"] == "yolo_configured":
        return {
            "status": "configured",
            "model": status["model"],
            "message": "A fine-tuned vehicle-damage YOLO model is ready for inference.",
            "detections": [],
        }
    return {
        "status": "not_configured",
        "message": status["message"],
        "detections": [],
    }
