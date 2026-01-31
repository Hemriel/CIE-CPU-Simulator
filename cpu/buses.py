"""Minimal display-only buses for visualizing RTN data paths.

Responsibility:
- Provide visual representation of data and address buses for the UI.
- Track which components are connected during each RTN step so the interface can
  highlight active data paths.
- Store the current bus value for display purposes.

CIE 9618 reference:
- 4.1 Central Processing Unit (CPU) Architecture:
    - Show understanding of how data are transferred between various components using the address bus, data bus, and control bus.

Design note:
- CIE 9618 requires understanding that data and addresses move along buses.
  However, in this simulation, actual data transfer happens directly between
  components (registers, memory, ALU). Bus components exist purely for visualization.
- The control bus (CIE 9618 §4.1) is omitted from this implementation. Instead,
  control signals are visualized directly on the components themselves (registers
  show control signals, ALU shows operation mode).
- The data bus was also split into separate internal and external data buses to accomodate
  limitations of the UI layout. The internal data bus connects CPU components,
  while the external data bus connects the CPU to RAM.

Entry point:
- The :class:`Bus` class is instantiated for each bus (address bus, data bus,
  internal data bus) and updated by the Control Unit during RTN step execution.

Includes:
- :class:`EndPoint` protocol: Interface for components that can connect to buses
- :class:`Bus`: Display-only bus component for visualization
"""

from dataclasses import dataclass, field
from typing import Protocol
from cpu.component import CPUComponent
from common.constants import ComponentName, WORD_SIZE, AbnormalComponentUseError


### Educational notes on Python features used in this module ###
#
# Protocol (appears in EndPoint class):
# Protocol is NOT in the curriculum but is a useful Python typing feature.
# A Protocol defines an interface: any class that has the required methods
# (get_position in this case) automatically satisfies the protocol without
# needing to explicitly inherit from it. This is called "structural subtyping"
# or "duck typing with type hints."
# More info: https://docs.python.org/3/library/typing.html#typing.Protocol
#
# Dataclasses with default_factory (field(default_factory=list)):
# Dataclasses are NOT in the curriculum but are a convenient way to define
# simple classes that primarily store data.
# Dataclasses automatically generate __init__, __repr__, and other methods
# based on class attributes.
# The default_factory pattern creates a fresh list for each Bus instance.
# Without default_factory, all Bus instances would share the same list
# (mutable default argument problem in Python).
# More info: https://docs.python.org/3/library/dataclasses.html#mutable-default-values
# 

class EndPoint(Protocol):
    """Interface for components that can connect to buses for visualization.
    
    Any component that implements get_position() can be used as a bus endpoint.
    This allows the UI to draw connections between components along the bus paths.
    """

    def get_position(self) -> tuple[int, int]: # type: ignore (some type checkers might complain about return type)
        """Return the layout position used for highlighting a bus connection.
        
        Returns:
            A tuple of (line, column) indicating where the component sits in the UI layout.
        """
        pass


@dataclass
class Bus(CPUComponent):
    """A visual bus that connects components purely for display purposes.
    
    This class models the address and data buses described in CIE 9618 §4.1, but
    only for visualization. Actual data transfers occur directly between component
    objects in the Python code.
    
    The bus tracks:
    - Which components are logically connected (last_connections)
    - Whether the bus is currently active (for UI highlighting)
    """

    name: ComponentName
    sources: list[EndPoint] = field(default_factory=list)
    sink: EndPoint | None = None
    active: bool = False

    # UI-only metadata describing the last logical connection(s) driven on this bus.
    # Most RTN steps drive a single source->destination transfer, but some visuals
    # (e.g. ALU operations) need to show multiple sources feeding one destination.
    last_connections: list[tuple[ComponentName, ComponentName]] = field(default_factory=list)

    def read(self) -> int:
        """Buses should not be read from directly in this simulation."""
        raise AbnormalComponentUseError("Buses should not be read directly")

    def write(self, data: int) -> None:
        """Buses should not be written to directly in this simulation."""
        raise AbnormalComponentUseError("Buses should not be written directly")

    def set_last_connections(
        self, connections: list[tuple[ComponentName, ComponentName]] | None
    ) -> None:
        """Record which components were connected during the last RTN step.
        
        The UI uses this to draw highlighted paths showing data flow between
        components. For example, during MAR ← PC, the connection would be
        [(ComponentName.PC, ComponentName.MAR)].

        Args:
            connections: A list of (source, destination) transfers to visualise.
                Use an empty list or None to clear the connections.
        """

        self.last_connections = list(connections or [])
        self._update_display()

    def set_active(self, active: bool) -> None:
        """Set whether the bus is currently active for highlighting purposes.
        
        The UI highlights active buses to show which data paths are in use during
        the current RTN step.
        
        Args:
            active: True to highlight the bus, False to dim it.
        """
        self.active = active
        self._update_display()
