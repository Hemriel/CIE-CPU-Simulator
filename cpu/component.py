"""Shared component interfaces for the CPU simulator.

Responsibility:
- Define the minimal interfaces that all CPU components share
    (naming, read/write behavior, and display refresh hooks).

Illustrates:
- CIE 9618: 9.1 Computational Thinking Skills:
    - Show an understanding of abstraction (component interfaces as abstraction layer).
    - Describe and use decomposition (breaking CPU into modular components).
- CIE 9618: 10.4 Introduction to Abstract Data Types:
    - Show understanding that an ADT is a collection of data and a set of operations on those data.
- CIE 9618: 12.3 Program testing and maintenance:
    - Show understanding of the methods of testing available and select appropriate data for a given method.
    - Show understanding of the need for a test strategy and test plan and their likely content.
- CIE 9618: 13.1 User-defined data types (depper than intended by curriculum, this could serve as a complex example):
    - Show understanding of why user-defined data types are necessary.
    - Chose and define an appropriate user defined data type for a given problem.

Design choices:
- Components expose a small, explicit API (`read`, `write`, `set_last_active`) that 
    all components must implement. This keeps the CPU control logic simple and uniform.
- A lightweight display hook is provided to keep UI updates separate from
    component logic. This allows to implement the logic of components
    independently of any specific UI framework.

Entry points / public API:
- `CPUComponent` protocol: implemented by registers, memory, buses...
- `Displayer` protocol: implemented by UI widgets or test display helpers.
- `TerminalDisplayer`: a simple fallback for non-UI debugging.

Contained classes and protocols:
- `CPUComponent`
- `Displayer`
- `TerminalDisplayer`
"""

from dataclasses import dataclass
from typing import Protocol
from common.constants import ComponentName

### Educational notes on Python features used in this module ###
#
# Protocol:
# Protocol is NOT in the curriculum but is a useful Python typing feature.
# A Protocol defines an interface: any class that has the required methods
# automatically satisfies the protocol without needing to explicitly inherit from it.
# This is called "structural subtyping" or "duck typing with type hints."
# More info: https://docs.python.org/3/library/typing.html#typing.Protocol
#
# Dataclasses:
# Dataclasses are NOT in the curriculum but are a convenient way to define
# simple classes that primarily store data.
# Dataclasses automatically generate __init__, __repr__, and other methods
# based on class attributes.
# More info: https://docs.python.org/3/library/dataclasses.html

class Displayer(Protocol):
    """Protocol for UI targets that can refresh their view.

    This keeps UI logic separate from CPU state updates. Any class with an
    `update_display()` method can act as a displayer.
    """

    def update_display(self) -> None:
        """Refresh the on-screen display for the bound component."""
        pass

# Although this is interface related code , and therefore shouldn't be here, 
# it is included here as it was used during devellopment to test and debug 
# CPU components before the UI was implemented.
class TerminalDisplayer:
    """A displayer that outputs component state to the terminal.

    This is a fallback used when no graphical UI has been
    attached. It makes component state visible without requiring Textual.
    """

    def __init__(self, component: "CPUComponent") -> None:
        """Create a terminal displayer for the given component.

        Args:
            component: The CPU component whose state should be printed when
                `update_display()` is called.
        """
        self.component = component

    def update_display(self) -> None:
        """Print the component state to the terminal.

        This uses the component's `__str__` or `__repr__` implementation.
        """
        print(self.component)

    def __repr__(self) -> str:
        return "TerminalDisplayer"


@dataclass
class CPUComponent(Protocol):
    """Protocol describing the common API for all CPU components.

    The `name` must be a member of `ComponentName` so the UI can identify and
    label the component in the RTN timeline. The optional `displayer` receives
    refresh notifications whenever the component's state changes.
    """

    name: ComponentName
    last_active: bool = False
    displayer: Displayer | None = None

    def _update_display(self) -> None:
        """Trigger any bound display targets to redraw this component.

        This implements a simple *display hook* pattern: component logic remains
        independent, while observers update their visual state on demand.
        """
        if not self.displayer:
            # If no UI is connected, fall back to terminal output so we 
            # can still see changes during simple runs or tests.
            self.displayer = TerminalDisplayer(self)
        if self.displayer:
            self.displayer.update_display()

    def read(self) -> int:
        """Read the component's current data value.

        Returns:
            The integer value currently held or produced by the component.
        """
        raise NotImplementedError("Subclasses must implement the read method.")

    def write(self, data: int) -> None:
        """Write a new data value into the component.

        Args:
            data: The integer value to store or consume.
        """
        raise NotImplementedError("Subclasses must implement the write method.")

    def set_last_active(self, active: bool) -> None:
        """Record whether the component was active during the last cycle.

        Args:
            active: True if the component participated in the latest CPU tick.
        """
        self.last_active = active
        self._update_display()