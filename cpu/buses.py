"""Minimal display-only buses for visualizing RTN data paths in the supervisor UI."""

from dataclasses import dataclass
from typing import Protocol
from component import CPUComponent


class EndPoint(Protocol):
    """Represent a visual attachment point whose position on the bus can be queried."""

    def get_position(self) -> int:
        """Return the layout position used for highlighting a bus connection."""
        ...


@dataclass
class Bus(CPUComponent):
    """A visual bus that connects a source list to a sink purely for display purposes."""

    sources: list[EndPoint] = []
    sink: EndPoint | None = None
