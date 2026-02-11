"""Visual display component for the Control Unit (CU) state.

Responsibility:
- Display the CU's current instruction, decoded assembly, RTN step, and phase.
- Highlight when the CU is active vs. idle during execution.

Entry point:
- :class:`ControlUnitDisplay`: Main widget bound to a CU instance.

Design choices:
- The back end CU component doesn't know about the UI; instead, it uses a
    displayer hook to notify the UI when its state changes.
- The ControlUnitDisplay formats CU state for visualization, but performs no
    control logic itself and waits for the CU to request display updates.
"""

from simulator.CU import CU  # the displayer needs to know about the CU it displays
from common.constants import DisplayMode
from common.utils import formatted_value

# textual specific imports. For more information, see https://textual.textualize.io/
from textual.app import ComposeResult
from textual.widgets import Label
from textual.containers import Vertical, Horizontal


class ControlUnitDisplay(Vertical):
    """Visual widget that displays CU state during execution.

    Shows the current instruction, decoded assembly text, RTN step, and phase.
    The display updates whenever the CU state changes and highlights active
    vs. idle periods.
    """

    def __init__(self, cu: CU) -> None:
        """Create a CU display bound to the given CU instance.

        Args:
            cu: The control unit component to visualize.
        """
        super().__init__()
        self.id = "control-unit-display"
        self.border_title = "CU"
        self.instr_label = Label("Instr.", classes="cu-titles")
        self.assembly_label = Label("Assembly", classes="cu-titles")
        self.step_label = Label("Step", classes="cu-titles")
        self.phase_label = Label("Phase", classes="cu-titles")
        self.inst_value = Label("", classes="cu-values")
        self.assembly_value = Label("", classes="cu-values")
        self.step_value = Label("", classes="cu-values")
        self.phase_value = Label("", classes="cu-values")
        self.cu = cu
        self.number_display_mode = DisplayMode.HEX

    def compose(self) -> ComposeResult:
        """Build the widget layout with instruction/phase rows."""
        with Horizontal():
            yield self.instr_label
            yield self.inst_value
        with Horizontal():
            yield self.assembly_label
            yield self.assembly_value
        with Horizontal():
            yield self.step_label
            yield self.step_value
        with Horizontal():
            yield self.phase_label
            yield self.phase_value
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
        """Refresh the display with current CU state.

        Updates the current instruction, assembly string, RTN step, and phase,
        and applies active/idle styling.
        """
        cu = self.cu

        # Apply active/inactive styling based on RTN step participation
        if cu.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")

        # Update displayed values
        instruction = (
            formatted_value(cu.current_instruction, self.number_display_mode)
            if cu.current_instruction is not None
            else "None"
        )
        rtn_step = cu.current_RTNStep or "Idle"
        phase = getattr(cu.current_phase, "name", cu.current_phase)
        self.inst_value.content = f"{instruction}"
        self.assembly_value.content = f"{cu.stringified_instruction or 'None'}"
        self.step_value.content = f"{rtn_step}"
        self.phase_value.content = f"{phase}"
