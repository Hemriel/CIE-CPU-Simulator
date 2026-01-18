from typing import Any

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class ControlUnitDisplay(Static):
    """Minimal CU widget that mirrors the current instruction and RTN step."""

    def __init__(self, cpu: Any) -> None:
        super().__init__()
        self.cpu = cpu
        self.update_display()

    def update_display(self) -> None:
        cu = self.cpu.cu
        instruction = cu.current_instruction or "None"
        operand = cu.operand if cu.operand is not None else "-"
        rtn_step = cu.current_RTNStep or "Idle"
        phase = getattr(cu.current_phase, "name", cu.current_phase)
        text = Text(
            f"Instruction: {instruction}\n"
            f"Operand: {operand}\n"
            f"RTN Step: {rtn_step}\n"
            f"Phase: {phase}"
        )
        panel = Panel(text, title="Control Unit", border_style="green")
        self.update(panel)
