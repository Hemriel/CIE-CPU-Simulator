from cpu.cpu_io import IO

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class IODisplay(Static):
    """Displays a single IO element value and its most recent control signal."""

    def __init__(self, io_element: IO, label: str) -> None:
        super().__init__()
        self.io_element = io_element
        self.label = label
        self.update_display()

    def update_display(self) -> None:
        value = getattr(self.io_element, "_value", 0)
        control = getattr(self.io_element, "_control", None)
        text = Text(
            f"Value: {value}\n"
            f"Control: {control or 'idle'}"
        )
        panel = Panel(text, title=self.label, border_style="cyan")
        self.update(panel)
