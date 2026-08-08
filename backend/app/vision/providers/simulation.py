"""Prototype Vision Simulation provider.

This is NOT a trained defect-detection model. Per the Phase 2 brief, no
labeled defect-image dataset or vision API is available in this
environment, so defect "detection" here is a simple, honest pixel-level
heuristic: it measures the fraction of the product's surface that is
notably darker or differently-hued than its dominant color (a real,
if crude, proxy for bruises/rot/cracks/crush marks), computed from the
actual uploaded image — not random numbers. Confidence and severity scale
with how large and how uniform that anomalous area is.

Swap this class for a real model/API later — VisionService and every
caller only depend on the VisionProvider interface, not this
implementation.
"""
import numpy as np
from PIL import Image

from .base import VisionProvider

NAME = "simulation"

DARK_DELTA = 35          # luminance units below the median counted as "anomalous-dark"
BRIGHT_DELTA = 35        # luminance units above the median counted as "anomalous-bright"
                          # (reflective cracks/tears/foreign-light streaks show up light, not dark)
HUE_DELTA_DEGREES = 28    # hue distance from median counted as "anomalous-color"
MIN_SATURATION_FOR_HUE = 40  # ignore near-gray pixels for hue comparison
NO_DEFECT_RATIO_FLOOR = 0.02  # below this, we report no defect at all


def _rgb_to_hsv_arrays(arr: np.ndarray):
    img = Image.fromarray(arr.astype("uint8"), "RGB").convert("HSV")
    hsv = np.asarray(img, dtype=np.float32)
    return hsv[:, :, 0] * (360.0 / 255.0), hsv[:, :, 1] * (100.0 / 255.0), hsv[:, :, 2]


def _anomaly_ratios(image: Image.Image):
    small = image.resize((96, 96))
    arr = np.asarray(small, dtype=np.float32)
    luminance = arr.mean(axis=2)
    hue, saturation, _ = _rgb_to_hsv_arrays(arr)

    median_luminance = float(np.median(luminance))
    dark_mask = luminance < (median_luminance - DARK_DELTA)
    bright_mask = luminance > (median_luminance + BRIGHT_DELTA)
    brightness_anomaly_ratio = float(dark_mask.mean() + bright_mask.mean())

    median_hue = float(np.median(hue[saturation > MIN_SATURATION_FOR_HUE])) if (saturation > MIN_SATURATION_FOR_HUE).any() else float(np.median(hue))
    hue_distance = np.minimum(np.abs(hue - median_hue), 360 - np.abs(hue - median_hue))
    hue_mask = (hue_distance > HUE_DELTA_DEGREES) & (saturation > MIN_SATURATION_FOR_HUE)
    hue_ratio = float(hue_mask.mean())

    return brightness_anomaly_ratio, hue_ratio


def _severity_for_ratio(ratio: float) -> str:
    if ratio >= 0.11:
        return "high"
    if ratio >= 0.05:
        return "medium"
    return "low"


def _confidence_for_ratio(ratio: float) -> float:
    return round(min(0.96, max(0.30, 0.35 + ratio * 4.5)), 2)


class SimulationVisionProvider(VisionProvider):
    name = NAME

    def analyze(self, image: Image.Image, defect_group: str, defect_types: list) -> dict:
        brightness_anomaly_ratio, hue_ratio = _anomaly_ratios(image)
        primary_ratio = max(brightness_anomaly_ratio, hue_ratio)

        defects = []
        if primary_ratio >= NO_DEFECT_RATIO_FLOOR and defect_types:
            defect_type = self._pick_defect_type(defect_group, defect_types, brightness_anomaly_ratio, hue_ratio)
            defects.append(
                {
                    "type": defect_type["type"],
                    "label": defect_type["label"],
                    "confidence": _confidence_for_ratio(primary_ratio),
                    "severity": _severity_for_ratio(primary_ratio),
                    "area_ratio": round(primary_ratio, 4),
                }
            )
            # A second, independent anomaly signal (color-shift on top of a
            # dark region) is reported as a secondary lower-confidence defect
            # — this is what lets the decision engine exercise "multiple defects".
            secondary_ratio = min(brightness_anomaly_ratio, hue_ratio)
            if secondary_ratio >= NO_DEFECT_RATIO_FLOOR * 1.5 and len(defect_types) > 1:
                secondary_type = defect_types[1] if defect_types[1]["type"] != defect_type["type"] else defect_types[0]
                defects.append(
                    {
                        "type": secondary_type["type"],
                        "label": secondary_type["label"],
                        "confidence": _confidence_for_ratio(secondary_ratio * 0.8),
                        "severity": _severity_for_ratio(secondary_ratio),
                        "area_ratio": round(secondary_ratio, 4),
                    }
                )

        quality_score = round(max(0.0, min(100.0, 100 - primary_ratio * 500)), 1)

        return {
            "defects": defects,
            "quality_score": quality_score,
            "raw": {
                "provider": NAME,
                "brightness_anomaly_ratio": round(brightness_anomaly_ratio, 4),
                "hue_ratio": round(hue_ratio, 4),
                "defect_group": defect_group,
            },
        }

    @staticmethod
    def _pick_defect_type(defect_group, defect_types, brightness_anomaly_ratio, hue_ratio):
        # For produce, a color-shift-dominant anomaly reads as discoloration/rot;
        # a darkness-dominant anomaly reads as bruising. Other groups only have
        # one plausible "primary" defect type for this simple heuristic.
        if defect_group == "produce":
            rot = next((d for d in defect_types if d["type"] == "rot_discoloration"), None)
            bruise = next((d for d in defect_types if d["type"] == "bruising"), None)
            if rot and hue_ratio > brightness_anomaly_ratio and hue_ratio >= NO_DEFECT_RATIO_FLOOR:
                return rot
            if bruise:
                return bruise
        return defect_types[0]
