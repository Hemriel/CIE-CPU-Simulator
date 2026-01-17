"""Common base for every simulated CPU component to share naming and display hooks."""

from dataclasses import dataclass, field
from typing import Protocol
from constants import ComponentName


class Displayer(Protocol):
    """Simple display protocol representing UI targets that can refresh their view."""

    def update_display(self) -> None: ...

class TerminalDisplayer():
    """A displayer that outputs to the terminal for testing purposes."""
    def __init__(self, component) -> None:
        self.component = component

    def update_display(self) -> None:
        """Automatically fetches properties and prints them to the terminal."""
        print(self.component)

    def __repr__(self) -> str:
        return "TerminalDisplayer"

@dataclass
class CPUComponent(Protocol):
    """Base class for components that tracks an official ComponentName and display hook.

    The provided `name` must match a member of ComponentName so the UI can query and
    reference the component whenever it renders the RTN timeline. The optional `displayer`
    receives refresh notifications whenever the component's state changes.
    """

    name: ComponentName
    displayer: Displayer | None = None

    def _update_display(self):
        """Trigger any bound display targets to redraw this component."""
        if not self.displayer:
            self.displayer = TerminalDisplayer(self)
        if self.displayer:
            self.displayer.update_display()

    def read(self) -> int:
        """Read data from the component. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the read method.")
    
    def write(self, data: int) -> None:
        """Write data to the component. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the write method.")
