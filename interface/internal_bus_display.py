from cpu.buses import Bus

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class InternalBusDisplay(Static):
    """Placeholder for the inner data bus between the CU/ALU and the registers."""

    def __init__(self, bus: Bus) -> None:
        super().__init__()
        self.id = "internal-bus-display"
        self.bus = bus
        self.update_display()

    def update_display(self) -> None:
        text = Text(
            f"Values: {self.bus.value:04X}\n"
            f"Active: {self.bus.active}"
        )
        if self.bus.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        panel = Panel(text, title="Inner Data Bus")
        self.update(panel)
