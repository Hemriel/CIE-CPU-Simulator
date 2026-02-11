"""Visual display component for the ALU, showing operands, results, and control signals.

Responsibility:
- Display ALU state (operands, result, flag) in the UI during CPU execution.
- Highlight when the ALU is active vs. idle during RTN steps.

Entry point:
- :class:`ALUDisplay`: Main widget bound to an ALU instance.

Design choices:
- The back end ALU component doesn't know about the UI; instead, it uses a
  displayer hook to notify the UI when its state changes.
- The ALUDisplay knows how to extract and format ALU state for visualization,
  but does not perform any ALU logic itself, and waits for the ALU to ask for
  display updates.
"""

from simulator.ALU import ALU # the displayer needs to know about the ALU it displays
from common.constants import DisplayMode
from common.utils import formatted_value

# textual specific imports. For more information, see https://textual.textualize.io/
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label



class ALUDisplay(Vertical):
    """Visual widget that displays ALU state during execution.
    
    Shows the ALU's current operands, computed result, and comparison flag.
    The display is automatically updated whenever the ALU state changes,
    and visually highlights when the ALU is actively computing vs. idle.
    """

    def __init__(self, alu: ALU) -> None:
        """Create an ALU display bound to the given ALU instance.
        
        Args:
            alu: The ALU component to visualize.
        """
        super().__init__()
        self.id = "alu-display"
        self.alu = alu
        self.border_title = "ALU"
        # Create labels for each displayed value
        self.acc_title = Label("Accumulator:")
        self.operand_title = Label("Operand:")
        self.result_title = Label("Result:")
        self.flag_title = Label("Flag:")
        self.acc_value = Label("", classes="alu-values")
        self.operand_value = Label("", classes="alu-values")
        self.result_value = Label("", classes="alu-values")
        self.flag_value = Label("", classes="alu-values")

        self.number_display_mode = DisplayMode.HEX

    def compose(self) -> ComposeResult:
        """Build the widget layout with operand/result rows."""
        with Horizontal():
            yield self.acc_title
            yield self.acc_value
        with Horizontal():
            yield self.operand_title
            yield self.operand_value
        with Horizontal():
            yield self.result_title
            yield self.result_value
        with Horizontal():
            yield self.flag_title
            yield self.flag_value
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
        """Refresh the display with current ALU state.
        
        Updates operand/result values in hexadecimal, shows the flag state,
        and applies visual styling to highlight active/idle status.
        """
        alu = self.alu
        # Apply active/inactive styling based on RTN step participation
        if alu.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        # Update displayed values
        flag = self.alu.flag_component
        self.acc_value.content = formatted_value(alu.acc, self.number_display_mode)
        self.operand_value.content = formatted_value(alu.operand, self.number_display_mode)
        self.result_value.content = formatted_value(alu.result, self.number_display_mode)
        self.flag_value.content = f"{flag.value}"
        # Show current control signal (operation mode) in the border subtitle
        self.border_subtitle = f"{alu.control or 'idle'}"

