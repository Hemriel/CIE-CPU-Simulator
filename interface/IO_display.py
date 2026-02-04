"""Visual display component for the I/O queue state.

Responsibility:
- Display the current I/O contents and last control signal for an I/O component.
- Highlight when the I/O component is active vs. idle during execution.

Entry point:
- :class:`IODisplay`: Main widget bound to an I/O instance.

Design choices:
- The back end I/O component doesn't know about the UI; instead, it uses a
    displayer hook to notify the UI when its state changes.
- The IODisplay formats I/O state for visualization, but performs no I/O logic
    itself and waits for the I/O component to request display updates.
"""

from cpu.cpu_io import IO  # the displayer needs to know about the I/O it displays

# textual specific imports. For more information, see https://textual.textualize.io/
from textual.widgets import Label


class IODisplay(Label):
    """Visual widget that displays I/O contents during execution.

    Shows the current character queue and the last control signal, and highlights
    active vs. idle periods.
    """

    def __init__(self, io_element: IO, label: str, reversed : bool = False) -> None:
        """Create an I/O display bound to the given I/O instance.

        Args:
            io_element: The I/O component to visualize.
            label: The label shown in the UI border (e.g., "IN" or "OUT").
            reversed: Whether to reverse the displayed string for right-to-left layouts.
        """
        super().__init__()
        self.id = label
        self.io_element = io_element
        self.border_title = label
        self.reversed = reversed

    def on_mount(self) -> None:
        """Initialize the display once the widget is mounted."""
        self.update_display()

    def update_display(self) -> None:
        """Refresh the display with current I/O state.

        Updates the visible contents, shows the last control signal, and applies
        active/idle styling.
        """
        # Apply active/inactive styling based on RTN step participation
        if self.io_element.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        
        # Update displayed values
        value = getattr(self.io_element, "contents", "")
        control = getattr(self.io_element, "_control", None)
        self.border_subtitle = f"{control or 'idle'}"
        self.content = f"{value[::-1] if self.reversed else value}"