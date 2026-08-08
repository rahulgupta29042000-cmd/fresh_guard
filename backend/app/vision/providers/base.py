"""Provider interface. A future real vision model/API integration would
implement this same interface — VisionService and everything above it
(routers, decision engine) is provider-agnostic."""
from abc import ABC, abstractmethod


class VisionProvider(ABC):
    name: str

    @abstractmethod
    def analyze(self, image, defect_group: str, defect_types: list) -> dict:
        """Returns {defects: [{type, confidence, severity}], quality_score: float,
        raw: dict}. `image` is a PIL.Image already validated as decodable."""
        raise NotImplementedError
