"""Real (non-simulated) image-quality checks computed from actual pixel
data — brightness, blur/sharpness, and resolution. This runs before any
defect classification, and a poor-quality image is never sent to the
defect classifier (per the Phase 2 brief).
"""
from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter, UnidentifiedImageError

from .. import config


class InvalidImageError(Exception):
    pass


def load_image(image_bytes: bytes) -> Image.Image:
    try:
        img = Image.open(BytesIO(image_bytes))
        img.load()
    except (UnidentifiedImageError, OSError) as e:
        raise InvalidImageError("File is not a readable image") from e
    return img.convert("RGB")


def _brightness(gray: np.ndarray) -> float:
    return float(gray.mean())


def _sharpness(gray: np.ndarray) -> float:
    """Edge-energy proxy for blur: variance of a simple Laplacian-like
    second-derivative filter. Low variance ~= few sharp edges ~= blurry."""
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    padded = np.pad(gray, 1, mode="edge").astype(np.float32)
    conv = (
        kernel[0, 1] * padded[:-2, 1:-1]
        + kernel[1, 0] * padded[1:-1, :-2]
        + kernel[1, 1] * padded[1:-1, 1:-1]
        + kernel[1, 2] * padded[1:-1, 2:]
        + kernel[2, 1] * padded[2:, 1:-1]
    )
    return float(conv.var())


def assess_image_quality(image_bytes: bytes) -> dict:
    """Returns {score, status, issues[]} — 'status' is 'good' or 'poor'.
    Never raises for a valid-but-poor-quality image; raises InvalidImageError
    only when the bytes aren't a decodable image at all."""
    img = load_image(image_bytes)
    width, height = img.size
    gray = np.asarray(img.convert("L"), dtype=np.float32)

    brightness = _brightness(gray)
    sharpness = _sharpness(gray)
    thresholds = config.IMAGE_QUALITY_THRESHOLDS

    issues = []
    if width < thresholds["min_width_px"] or height < thresholds["min_height_px"]:
        issues.append("Product too small / image resolution too low")
    if brightness < thresholds["min_brightness"]:
        issues.append("Image too dark")
    if brightness > thresholds["max_brightness"]:
        issues.append("Image overexposed / product not clearly visible")
    if sharpness < thresholds["min_sharpness"]:
        issues.append("Image too blurry")

    # Normalize brightness/sharpness into a 0-100 quality score.
    brightness_mid = (thresholds["min_brightness"] + thresholds["max_brightness"]) / 2
    brightness_range = (thresholds["max_brightness"] - thresholds["min_brightness"]) / 2
    brightness_score = max(0.0, 100 - abs(brightness - brightness_mid) / brightness_range * 100)
    sharpness_score = min(100.0, (sharpness / (thresholds["min_sharpness"] * 4)) * 100)
    resolution_score = 100.0 if width >= thresholds["min_width_px"] and height >= thresholds["min_height_px"] else 30.0

    score = round(0.35 * brightness_score + 0.45 * sharpness_score + 0.20 * resolution_score, 1)
    score = max(0.0, min(100.0, score))
    status = "good" if not issues and score >= 55 else "poor"

    return {
        "score": score,
        "status": status,
        "issues": issues,
        "width": width,
        "height": height,
        "brightness": round(brightness, 1),
        "sharpness": round(sharpness, 1),
    }
