"""Visual display component for a register's value and control signal.

Responsibility:
- Display a register's current value and last control signal in the UI.
- Highlight when the register is active vs. idle during execution.

Entry point:
- :class:`RegisterDisplay`: Main widget bound to a Register instance.

Design choices:
- The back end Register component doesn't know about the UI; instead, it uses a
    displayer hook to notify the UI when its state changes.
- The RegisterDisplay formats register state for visualization, but performs no
    register logic itself and waits for the Register to request display updates.
"""

from common.constants import DisplayMode, formatted_value
from cpu.register import Register  # the displayer needs to know about the register it displays

from rich.text import Text
# textual specific imports. For more information, see https://textual.textualize.io/
from textual.widgets import Label


class RegisterDisplay(Label):
    """Visual widget that displays register state during execution.

    Shows the register's current value and last control signal, and highlights
    active vs. idle periods.
    """

    def __init__(self, register: Register, label: str) -> None:
        """Create a register display bound to the given register instance.

        Args:
            register: The register component to visualize.
            label: The label shown in the UI border (e.g., "PC", "ACC").
        """
        super().__init__()
        self.id = label
        self.register = register
        self.border_title = label

        self.number_display_mode = DisplayMode.HEX

    def on_mount(self) -> None:
        """Initialize the display once the widget is mounted."""
        self.update_display()
        
    def set_number_display_mode(self, mode: DisplayMode) -> None:
        """Set the number display mode for the ALU values.
        
        Args:
            mode: One of "decimal", "hexadecimal", or "binary"
        """
        # Currently, this display only supports hexadecimal.
        # This method is a placeholder for future extensions.
        self.number_display_mode = mode

    def update_display(self) -> None:
        """Refresh the display with current register state.

        Updates the visible value, shows the last control signal, and applies
        active/idle styling.
        """
        # Apply active/inactive styling based on RTN step participation
        if self.register.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
            
        # Update displayed values
        value = getattr(self.register, "_value", 0)
        control = getattr(self.register, "_control", None)
        self.border_subtitle = f"{control or 'idle'}"
        self.content = Text(f"{formatted_value(value, self.number_display_mode)}")