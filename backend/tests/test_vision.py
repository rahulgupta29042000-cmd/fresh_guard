from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.vision import decision
from app.vision.quality import InvalidImageError, assess_image_quality, load_image
from app.vision.service import get_vision_service


def make_jpeg(color=(200, 60, 45), size=(300, 300), noise_sigma=12.0, brightness_scale=1.0, blotch_ratio=None, blotch_darken=0.4):
    arr = np.zeros((size[1], size[0], 3), dtype=np.float32)
    arr[:, :] = color
    if noise_sigma > 0:
        rng = np.random.default_rng(3)
        arr = arr + rng.normal(0, noise_sigma, arr.shape)
    if blotch_ratio:
        import math

        w, h = size
        radius = math.sqrt(blotch_ratio * w * h / math.pi)
        yy, xx = np.mgrid[0:h, 0:w]
        mask = ((xx - w / 2) ** 2 + (yy - h / 2) ** 2) <= radius**2
        arr[mask] = arr[mask] * blotch_darken
    arr = np.clip(arr * brightness_scale, 0, 255).astype("uint8")
    img = Image.fromarray(arr, "RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class FakeProduct:
    def __init__(self, category="produce", packaging_type="loose"):
        self.category = category
        self.packaging_type = packaging_type


# ---------------------------------------------------------------------------
# Image quality validation
# ---------------------------------------------------------------------------


def test_valid_image_passes_quality_gate():
    data = make_jpeg()
    result = assess_image_quality(data)
    assert result["status"] == "good"
    assert result["issues"] == []


def test_invalid_image_raises():
    with pytest.raises(InvalidImageError):
        load_image(b"this is not an image, just garbage bytes")


def test_dark_image_flagged():
    data = make_jpeg(brightness_scale=0.15)
    result = assess_image_quality(data)
    assert result["status"] == "poor"
    assert any("dark" in issue.lower() for issue in result["issues"])


def test_blurry_image_flagged():
    data = make_jpeg(noise_sigma=0.0)  # flat color = no edges = blurry
    result = assess_image_quality(data)
    assert result["status"] == "poor"
    assert any("blurry" in issue.lower() for issue in result["issues"])


def test_too_small_image_flagged():
    data = make_jpeg(size=(50, 50))
    result = assess_image_quality(data)
    assert result["status"] == "poor"
    assert any("small" in issue.lower() or "resolution" in issue.lower() for issue in result["issues"])


# ---------------------------------------------------------------------------
# Vision analysis (PASS / REVIEW / REJECT via the real pipeline)
# ---------------------------------------------------------------------------


def test_vision_pass_no_defect():
    svc = get_vision_service()
    data = make_jpeg()
    result = svc.analyze(data, FakeProduct())
    assert result["status"] == "PASS"
    assert result["defects"] == []


def test_vision_review_moderate_defect():
    svc = get_vision_service()
    data = make_jpeg(blotch_ratio=0.055)
    result = svc.analyze(data, FakeProduct())
    assert result["status"] == "REVIEW"
    assert len(result["defects"]) >= 1


def test_vision_reject_severe_defect():
    svc = get_vision_service()
    data = make_jpeg(blotch_ratio=0.16)
    result = svc.analyze(data, FakeProduct())
    assert result["status"] == "REJECT"
    assert result["defects"][0]["severity"] == "high"


def test_vision_returns_structured_result_with_model_version():
    svc = get_vision_service()
    result = svc.analyze(make_jpeg(), FakeProduct())
    assert result["model_version"]
    assert result["vision_mode"] == "simulation"
    assert "quality_score" in result
    assert "recommendation" in result


# ---------------------------------------------------------------------------
# Decision engine (independent of the vision provider)
# ---------------------------------------------------------------------------


def test_decision_no_defect_high_score_is_pass():
    assert decision.decide(95, []) == "PASS"


def test_decision_high_confidence_high_severity_defect_is_reject():
    defects = [{"type": "bruising", "confidence": 0.95, "severity": "high"}]
    assert decision.decide(40, defects) == "REJECT"


def test_decision_low_confidence_defect_never_auto_rejects():
    """Human-in-the-loop rule: low model confidence must route to REVIEW,
    never REJECT, even if the raw score dips into review territory."""
    defects = [{"type": "bruising", "confidence": 0.45, "severity": "low"}]
    assert decision.decide(70, defects) == "REVIEW"


def test_decision_multiple_defects_high_severity_dominates():
    defects = [
        {"type": "bruising", "confidence": 0.65, "severity": "medium"},
        {"type": "rot_discoloration", "confidence": 0.9, "severity": "high"},
    ]
    assert decision.decide(50, defects) == "REJECT"


def test_decision_medium_severity_without_high_confidence_is_review():
    defects = [{"type": "bruising", "confidence": 0.65, "severity": "medium"}]
    assert decision.decide(70, defects) == "REVIEW"
