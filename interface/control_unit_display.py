from cpu.CU import CU

from textual.app import ComposeResult
from textual.widgets import Label
from textual.containers import Vertical, Horizontal


class ControlUnitDisplay(Vertical):
    """Minimal CU widget that mirrors the current instruction and RTN step."""

    def __init__(self, cu: CU) -> None:
        super().__init__()
        self.id = "control-unit-display"
        self.border_title = "CU"
        self.instr_label = Label("Instr.", classes="cu-titles")
        self.operand_label = Label("Operand", classes="cu-titles")
        self.step_label = Label("Step", classes="cu-titles")
        self.phase_label = Label("Phase", classes="cu-titles")
        self.inst_value = Label("", classes="cu-values")
        self.operand_value = Label("", classes="cu-values")
        self.step_value = Label("", classes="cu-values")
        self.phase_value = Label("", classes="cu-values")
        self.cu = cu

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield self.instr_label
            yield self.inst_value
        with Horizontal():
            yield self.operand_label
            yield self.operand_value
        with Horizontal():
            yield self.step_label
            yield self.step_value
        with Horizontal():
            yield self.phase_label
            yield self.phase_value
        self.update_display()

    def update_display(self) -> None:
        cu = self.cu
        if cu.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        instruction = cu.current_instruction or "None"
        operand = cu.stringify_operand()
        rtn_step = cu.current_RTNStep or "Idle"
        phase = getattr(cu.current_phase, "name", cu.current_phase)
        self.inst_value.content = f"{instruction}"
        self.operand_value.content = f"{operand}"
        self.step_value.content = f"{rtn_step}"
        self.phase_value.content = f"{phase}"