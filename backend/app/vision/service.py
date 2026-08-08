"""VisionService — the single entrypoint routers call. Wires together
image-quality validation, the swappable defect-detection provider, and
the (separate) decision engine. Callers never talk to a provider or the
decision engine directly.
"""
from .. import config
from . import categories, decision, quality
from .providers.simulation import SimulationVisionProvider


class VisionAnalysisUnavailable(Exception):
    """Raised when the vision provider fails — callers must treat this as
    'AI unavailable, continue with manual inspection', never block fulfillment."""


class VisionService:
    def __init__(self):
        self.mode = config.VISION_MODE
        # Only a simulation provider ships in Phase 2; the mode check keeps
        # the swap point explicit for when a real provider is added.
        if self.mode == "simulation":
            self.provider = SimulationVisionProvider()
        else:
            raise ValueError(f"Unknown VISION_MODE: {self.mode}")

    def validate_image(self, image_bytes: bytes) -> dict:
        return quality.assess_image_quality(image_bytes)

    def analyze(self, image_bytes: bytes, product) -> dict:
        try:
            img = quality.load_image(image_bytes)
            defect_group = categories.defect_group_for_product(product.category, product.packaging_type)
            defect_types = categories.defect_types_for_product(product.category, product.packaging_type)
            result = self.provider.analyze(img, defect_group, defect_types)
        except Exception as e:  # noqa: BLE001 — any provider failure must degrade gracefully
            raise VisionAnalysisUnavailable(str(e)) from e

        status = decision.decide(result["quality_score"], result["defects"])
        recommendation = decision.recommendation_text(status, result["defects"])

        return {
            "quality_score": result["quality_score"],
            "status": status,
            "defects": result["defects"],
            "recommendation": recommendation,
            "model_version": config.VISION_MODEL_VERSION,
            "vision_mode": self.mode,
            "raw": result["raw"],
        }


_service = None


def get_vision_service() -> VisionService:
    global _service
    if _service is None:
        _service = VisionService()
    return _service
