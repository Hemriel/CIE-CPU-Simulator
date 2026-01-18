from typing import Any

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class RAMAddressDisplay(Static):
    """Shows the address currently being accessed in RAM."""

    def __init__(self, cpu: Any) -> None:
        super().__init__()
        self.cpu = cpu
        self.update_display()

    def update_display(self) -> None:
        address = self.cpu.ram_address.address
        text = Text(f"Focused Address: {address:04X}")
        panel = Panel(text, title="RAM Address", border_style="magenta")
        self.update(panel)


class RAMDataDisplay(Static):
    """Simple scrollable text that dumps neighboring RAM words."""

    WINDOW = 8

    def __init__(self, cpu: Any) -> None:
        super().__init__()
        self.cpu = cpu
        self.update_display()

    def update_display(self) -> None:
        focus = self.cpu.ram_address.address
        start = max(0, focus - self.WINDOW // 2)
        lines = []
        for offset in range(self.WINDOW):
            addr = start + offset
            value = self.cpu.ram.memory.get(addr, 0)
            marker = ">" if addr == focus else " "
            lines.append(f"{marker} {addr:04X}: {value:04X}")
        text = Text("\n".join(lines))
        panel = Panel(text, title="RAM Data", border_style="purple")
        self.update(panel)
