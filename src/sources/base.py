"""Abstract base class for source adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MediaRecord:
    """Normalized media record that all source adapters produce."""
    filepath: str
    source: str
    media_type: str  # "photo" or "video"
    timestamp: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    duration_seconds: float | None = None


class SourceAdapter(ABC):
    """Interface that all source adapters must implement."""

    @abstractmethod
    def parse_metadata(self) -> list[MediaRecord]:
        """Read source-specific export format, return normalized records."""
        ...

    @abstractmethod
    def get_media_files(self) -> list[Path]:
        """Return list of media file paths from this source."""
        ...
