from typing import Any

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class OuterBusDisplay(Static):
    """Generic outer bus representation (address or data)."""

    def __init__(self, bus: Any, title: str, color: str) -> None:
        super().__init__()
        self.bus = bus
        self.title = title
        self.color = color
        self.update_display()

    def update_display(self) -> None:
        text = Text(
            f"Value: {self.bus.value:04X}\n"
            f"Active: {self.bus.active}"
        )
        panel = Panel(text, title=self.title, border_style=self.color)
        self.update(panel)
