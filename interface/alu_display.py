from cpu.ALU import ALU

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class ALUDisplay(Static):
    """Simple ALU widget that echoes operands, mode, and flags."""

    def __init__(self, alu: ALU) -> None:
        super().__init__()
        self.alu = alu
        self.update_display()

    def update_display(self) -> None:
        alu = self.alu
        flag = self.alu.flag_component
        text = Text(
            f"Operand A: {alu.operand_a:04X}\n"
            f"Operand B: {alu.operand_b:04X}\n"
            f"Mode: {alu.control}\n"
            f"Result: {alu.result:04X}\n"
            f"Flag: {flag.value}"
        )
        panel = Panel(text, title="ALU", border_style="red")
        self.update(panel)
