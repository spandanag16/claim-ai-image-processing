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


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
YOLO_INPUT_SIZE = (640, 640)


@dataclass(frozen=True)
class PreparedImage:
    """Metadata produced after an image is validated and prepared."""

    upload_id: str
    original_filename: str
    original_path: Path
    processed_path: Path
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int
    original_size_bytes: int


def _safe_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only JPG, JPEG, and PNG vehicle images are supported.")
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

    expected_formats = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}
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
    original_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    original_path = original_dir / f"{upload_id}{extension}"
    processed_path = processed_dir / f"{upload_id}.jpg"
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
    except (UnidentifiedImageError, OSError) as exc:
        original_path.unlink(missing_ok=True)
        processed_path.unlink(missing_ok=True)
        raise ValueError("The uploaded image could not be prepared.") from exc

    return PreparedImage(
        upload_id=upload_id,
        original_filename=Path(filename).name,
        original_path=original_path,
        processed_path=processed_path,
        original_width=width,
        original_height=height,
        processed_width=YOLO_INPUT_SIZE[0],
        processed_height=YOLO_INPUT_SIZE[1],
        original_size_bytes=len(content),
    )


def yolo_inference_status() -> dict[str, object]:
    """Return the honest integration status for the not-yet-configured YOLO stage."""
    return {
        "status": "not_configured",
        "message": "Processed images are ready, but no trained YOLO model is configured yet.",
        "detections": [],
    }
