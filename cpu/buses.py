"""Minimal display-only buses for visualizing RTN data paths in the supervisor UI."""

from dataclasses import dataclass, field
from typing import Protocol
from component import CPUComponent
from constants import ComponentName, WORD_SIZE


class EndPoint(Protocol):
    """Represent a visual attachment point whose position on the bus can be queried."""

    def get_position(self) -> int:
        """Return the layout position used for highlighting a bus connection."""
        ...


@dataclass
class Bus(CPUComponent):
    """A visual bus that connects a source list to a sink purely for display purposes."""
    name: ComponentName
    sources: list[EndPoint] = field(default_factory=list)
    sink: EndPoint | None = None
    value : int = 0

    def read(self) -> int:
        """Buses should not be read from, but this will return the current value."""
        return self.value

    def write(self, data: int) -> None:
        """Update the bus value for display purposes and refresh the UI."""
        self.value = data % (1 << WORD_SIZE)
        self._update_display()

    def __repr__(self) -> str:
        return f"{self.value:04X}"