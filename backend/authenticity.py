"""Conservative image authenticity-risk screening.

This module does not claim to prove whether an image is real or AI-generated.
It combines explainable signals into a review risk score so suspicious claims
can be escalated for live capture or human inspection.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

from PIL import Image, ExifTags


EDITING_SOFTWARE_KEYWORDS = (
    "photoshop", "gimp", "lightroom", "snapseed", "canva", "picsart",
    "stable diffusion", "midjourney", "dall-e", "firefly", "generative",
)


def _perceptual_hash(image: Image.Image, size: int = 16) -> int:
    """Return a simple average perceptual hash as an integer."""
    gray = image.convert("L").resize((size, size))
    pixels = list(gray.getdata())
    average = sum(pixels) / len(pixels)
    value = 0
    for pixel in pixels:
        value = (value << 1) | int(pixel >= average)
    return value


def _hamming_distance(first: int, second: int) -> int:
    return (first ^ second).bit_count()


def _metadata(image: Image.Image) -> dict[str, str]:
    metadata: dict[str, str] = {}
    try:
        exif = image.getexif()
        for key, value in exif.items():
            name = ExifTags.TAGS.get(key, str(key))
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="replace")
            metadata[name] = str(value)
    except Exception:
        pass

    for key in ("software", "Software", "comment", "Comment", "parameters"):
        if key in image.info:
            metadata[key] = str(image.info[key])
    return metadata


def inspect_image(content: bytes | Path) -> dict[str, object]:
    """Return explainable authenticity signals for one image."""
    if isinstance(content, Path):
        image = Image.open(content)
    else:
        image = Image.open(io.BytesIO(content))

    with image:
        metadata = _metadata(image)
        metadata_text = " ".join(metadata.values()).lower()
        flags: list[str] = []
        risk_score = 0

        if not metadata:
            # Metadata is commonly removed by messaging apps, so this is only
            # a small signal and never proves that an image is fake.
            risk_score += 5
        if any(keyword in metadata_text for keyword in EDITING_SOFTWARE_KEYWORDS):
            risk_score += 45
            flags.append("Editing or synthetic-generation software metadata found")
        if "software" in {key.lower() for key in metadata} and not metadata.get("DateTimeOriginal"):
            risk_score += 10
            flags.append("Software metadata is present without original capture time")

        return {
            "risk_score": min(100, risk_score),
            "status": "review_required" if risk_score >= 40 else "low_risk",
            "flags": flags,
            "metadata_present": bool(metadata),
            "capture_time_present": "DateTimeOriginal" in metadata,
            "perceptual_hash": format(_perceptual_hash(image), "064x"),
        }


def compare_duplicates(results: list[dict[str, object]]) -> list[dict[str, object]]:
    """Flag exact or near-duplicate images within one claim."""
    updated = [dict(result) for result in results]
    for index, current in enumerate(updated):
        current_hash = int(str(current["perceptual_hash"]), 16)
        for previous in updated[:index]:
            previous_hash = int(str(previous["perceptual_hash"]), 16)
            distance = _hamming_distance(current_hash, previous_hash)
            if distance <= 8:
                flags = list(current.get("flags", []))
                flags.append("Image is identical or visually very similar to another claim image")
                current["flags"] = sorted(set(flags))
                current["risk_score"] = max(int(current["risk_score"]), 55)
                current["status"] = "review_required"
                break
    return updated


def summarize(results: Iterable[dict[str, object]]) -> dict[str, object]:
    items = list(results)
    high_risk = any(item["status"] == "high_risk" for item in items)
    review_required = any(item["status"] == "review_required" for item in items)
    for item in items:
        if int(item["risk_score"]) >= 70:
            item["status"] = "high_risk"
            high_risk = True
    status = "high_risk" if high_risk else "review_required" if review_required else "low_risk"
    return {
        "status": status,
        "risk_score": max((int(item["risk_score"]) for item in items), default=0),
        "images": items,
        "recommendation": (
            "Request a live camera capture or manual surveyor verification before settlement."
            if status != "low_risk"
            else "No strong authenticity-risk signal was found; retain normal human review."
        ),
        "note": "This is a risk screen, not proof that an image is real or AI-generated.",
    }
