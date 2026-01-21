from cpu.RAM import RAM

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static


class RAMAddressDisplay(Static):
    """Shows the address currently being accessed in RAM."""

    def __init__(self, ram: RAM) -> None:
        super().__init__()
        self.ram = ram
        self.update_display()

    def update_display(self) -> None:
        address = self.ram.address_comp.address
        text = Text(f"Focused Address: {address:04X}")
        panel = Panel(text)
        self.update(panel)


class RAMDataDisplay(Static):
    """Simple scrollable text that dumps neighboring RAM words."""

    WINDOW = 8

    def __init__(self, ram: RAM) -> None:
        super().__init__()
        self.ram = ram
        self.update_display()

    def update_display(self) -> None:
        focus = self.ram.address_comp.address
        start = max(0, focus - self.WINDOW // 2)
        lines = []
        for offset in range(self.WINDOW):
            addr = start + offset
            value = self.ram.memory.get(addr, 0)
            marker = ">" if addr == focus else " "
            lines.append(f"{marker} {addr:04X}: {value:04X}")
        text = Text("\n".join(lines))
        panel = Panel(text, title="RAM Data", border_style="purple")
        self.update(panel)
