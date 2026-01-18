from typing import Any

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class RegisterDisplay(Static):
    """Displays a single register value and its most recent control signal."""

    def __init__(self, register: Any, label: str) -> None:
        super().__init__()
        self.register = register
        self.label = label
        self.update_display()

    def update_display(self) -> None:
        value = getattr(self.register, "_value", 0)
        control = getattr(self.register, "_control", None)
        text = Text(
            f"Value: {value:04X}\n"
            f"Control: {control or 'idle'}"
        )
        panel = Panel(text, title=self.label, border_style="cyan")
        self.update(panel)
