from cpu.ALU import ALU

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label


class ALUDisplay(Vertical):
    """Simple ALU widget that echoes operands, mode, and flags."""

    def __init__(self, alu: ALU) -> None:
        super().__init__()
        self.id = "alu-display"
        self.alu = alu
        self.border_title = "ALU"
        self.acc_title = Label("Accumulator:")
        self.operand_title = Label("Operand:")
        self.result_title = Label("Result:")
        self.flag_title = Label("Flag:")
        self.acc_value = Label("", classes="alu-values")
        self.operand_value = Label("", classes="alu-values")
        self.result_value = Label("", classes="alu-values")
        self.flag_value = Label("", classes="alu-values")

    def compose(self) -> ComposeResult:
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

    def update_display(self) -> None:
        alu = self.alu
        if alu.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        flag = self.alu.flag_component
        self.acc_value.content = f"{alu.acc:04X}"
        self.operand_value.content = f"{alu.operand:04X}"
        self.result_value.content = f"{alu.result:04X}"
        self.flag_value.content = f"{flag.value}"
        self.border_subtitle = f"{alu.control or 'idle'}"

