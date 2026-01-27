"""Minimal display-only buses for visualizing RTN data paths.

These buses are primarily for the UI: the control unit updates them so the
interface can highlight which data path was active on each RTN step.
"""

from dataclasses import dataclass, field
from typing import Protocol
from cpu.component import CPUComponent
from common.constants import ComponentName, WORD_SIZE


class EndPoint(Protocol):
    """Represent a visual attachment point whose position on the bus can be queried."""

    def get_position(self) -> tuple[int,int]:
        """Return the layout position used for highlighting a bus connection.
        the first element is the line, the second is the column the element sits."""
        ...


@dataclass
class Bus(CPUComponent):
    """A visual bus that connects a source list to a sink purely for display purposes."""

    name: ComponentName
    sources: list[EndPoint] = field(default_factory=list)
    sink: EndPoint | None = None
    active: bool = False
    value: int = 0

    # UI-only metadata describing the last logical connection(s) driven on this bus.
    # Most RTN steps drive a single source->destination transfer, but some visuals
    # (e.g. ALU operations) need to show multiple sources feeding one destination.
    last_connections: list[tuple[ComponentName, ComponentName]] = field(default_factory=list)

    def read(self) -> int:
        """Buses should not be read from, but this will return the current value."""
        return self.value

    def write(self, data: int) -> None:
        """Update the bus value for display purposes and refresh the UI."""
        self.value = data % (1 << WORD_SIZE)
        self._update_display()

    def set_last_connections(
        self, connections: list[tuple[ComponentName, ComponentName]] | None
    ) -> None:
        """Record which components were connected on the last cycle.

        Args:
            connections: A list of (source, destination) transfers to visualise.
                Use an empty list / None to clear.
        """

        self.last_connections = list(connections or [])
        self._update_display()

    def set_active(self, active: bool) -> None:
        """Set whether the bus is currently active for highlighting purposes."""
        self.active = active
        self._update_display()

    def __repr__(self) -> str:
        return f"{self.value:04X}"
