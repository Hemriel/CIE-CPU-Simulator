from cpu.buses import Bus

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class OuterBusDisplay(Static):
    """Generic outer bus representation (address or data)."""

    def __init__(self, bus: Bus, title: str) -> None:
        super().__init__()
        self.id = title
        self.bus = bus
        self.title = title
        self.update_display()

    def update_display(self) -> None:
        text = Text(
            f"Value: {self.bus.value:04X}\n"
            f"Active: {self.bus.active}"
        )
        if self.bus.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        panel = Panel(text, title=self.title)
        self.update(panel)
