"""Local-disk image storage for the prototype, behind an interface that a
future S3/Cloud Storage/Azure Blob implementation could satisfy without
changing any caller.
"""
import os
import uuid
from abc import ABC, abstractmethod

from .. import config


class ImageStorageService(ABC):
    @abstractmethod
    def save(self, file_bytes: bytes, extension: str) -> str:
        """Returns a storage-relative path/key."""
        raise NotImplementedError

    @abstractmethod
    def read(self, path: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def resolve_absolute_path(self, path: str) -> str:
        raise NotImplementedError


class LocalImageStorageService(ImageStorageService):
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or config.IMAGE_STORAGE_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, file_bytes: bytes, extension: str) -> str:
        filename = f"{uuid.uuid4().hex}.{extension.lstrip('.')}"
        path = os.path.join(self.base_dir, filename)
        with open(path, "wb") as f:
            f.write(file_bytes)
        return filename  # storage-relative key; base_dir is an implementation detail

    def read(self, path: str) -> bytes:
        with open(self.resolve_absolute_path(path), "rb") as f:
            return f.read()

    def resolve_absolute_path(self, path: str) -> str:
        return os.path.join(self.base_dir, path)


_storage = None


def get_storage() -> ImageStorageService:
    global _storage
    if _storage is None:
        _storage = LocalImageStorageService()
    return _storage
