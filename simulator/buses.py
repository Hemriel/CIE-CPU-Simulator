"""Minimal display-only buses for visualizing RTN data paths.

Responsibility:
- Provide visual representation of data and address buses for the UI.
- Track which components are connected during each RTN step so the interface can
  highlight active data paths.
- Store the current bus value for display purposes.

Illustrates:
- CIE 9618: 4.1 Central Processing Unit (CPU) Architecture:
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
from simulator.component import CPUComponent
from common.constants import ComponentName, WORD_SIZE, AbnormalComponentUseError


### Educational notes on Python features used in this module ###
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

if __name__ == "__main__":
    from common.tester import run_tests_for_function, test_module

    VERBOSE = False
    # Default verbose value for all tests, to change the value for 1 test only, 
    # pass the value as an argument to the tester at the bottom of this file
    
    class NonDisplayer:
        """Bypass of default displayer to avoid terminal spaming"""
        def update_display(self) -> None:
            pass

    def test_write():
        """Test write() method raises appropriate error."""
        bus = Bus(ComponentName.INNER_DATA_BUS)
        
        return run_tests_for_function(
            [(42,)],
            ["error"],
            bus.write,
            "direct write to bus should raise an error")
    
    def test_read():
        """Test read() method returns most recent result."""
        bus = Bus(ComponentName.INNER_DATA_BUS)
        
        return run_tests_for_function(
            [(42,)],
            ["error"],
            bus.read,
            "direct write to bus should raise an error")
        
    def test_set_last_connection():
        """Test set_last_connections() updates the last_connections attribute."""
        bus = Bus(ComponentName.INNER_DATA_BUS, displayer=NonDisplayer())
        
        test_args = [
            ([(ComponentName.PC, ComponentName.MAR)],),
            ([],),
            (None,),
        ]
        test_expected = [
            [(ComponentName.PC, ComponentName.MAR)],
            [],
            [],
        ]

        def test_last_connections_setter(connections):
            bus.set_last_connections(connections)
            return bus.last_connections
        
        return run_tests_for_function(
            test_args,
            test_expected,
            test_last_connections_setter,
            "set_last_connections should update the last_connections attribute"
        )
    
    test_module(
        "buses",
        [
            test_write,
            test_read,
            test_set_last_connection,
        ],
        verbose=VERBOSE
    )
        
    