"""SigLIP model wrapper with lazy loading and device control."""

import logging
from pathlib import Path
from typing import Optional

from PIL import Image
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("photor")


class SigLipModel:
    """Lazy-loaded SigLIP model with device control."""

    def __init__(self, model_name: str = "google/siglip-so400m-patch14-384",
                 device: str = "auto"):
        self.model_name = model_name
        self._device = device
        self._model: Optional[SentenceTransformer] = None

    @property
    def device(self) -> str:
        """Resolve device: auto → cuda if available else cpu."""
        if self._device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
            return "cpu"
        return self._device

    def load(self):
        """Load the model if not already loaded."""
        if self._model is None:
            logger.info(f"Cargando modelo {self.model_name} en {self.device}...")
            self._model = SentenceTransformer(
                self.model_name, device=self.device
            )
            logger.info("Modelo cargado ✅")

    def encode_text(self, text: str) -> list[float]:
        """Encode text query and return normalized embedding."""
        self.load()
        emb = self._model.encode(text).tolist()
        return self._normalize(emb)

    def encode_image(self, image: Image.Image) -> list[float]:
        """Encode PIL image and return normalized embedding."""
        self.load()
        emb = self._model.encode(image).tolist()
        return self._normalize(emb)

    def encode(self, input_data):
        """Encode text or image, return normalized embedding."""
        self.load()
        emb = self._model.encode(input_data).tolist()
        return self._normalize(emb)

    @staticmethod
    def _normalize(embedding: list[float]) -> list[float]:
        """Normalize embedding to unit length for cosine similarity."""
        norm = sum(v * v for v in embedding) ** 0.5
        if norm > 0:
            return [v / norm for v in embedding]
        return embedding
