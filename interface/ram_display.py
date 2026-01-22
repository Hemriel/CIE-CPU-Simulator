from cpu.RAM import RAM

from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static, DataTable


class RAMAddressDisplay(Static):
    """Shows the address currently being accessed in RAM."""

    DEFAULT_CSS = """
    RAMAddressDisplay {
        width: 16;
        background: grey;
        content-align: center middle;
    }
    """

    def __init__(self, ram: RAM) -> None:
        super().__init__()
        self.ram = ram

    def on_mount(self) -> None:
        self.update_display()

    def update_display(self) -> None:
        address = self.ram.address_comp.address
        self.content = Text(f"RAM")


class RAMDataDisplay(DataTable):
    """Simple scrollable text that dumps neighboring RAM words."""

    def __init__(self, ram: RAM) -> None:
        super().__init__()
        self.id = "ram-data-display"
        self.ram = ram

    def on_mount(self) -> None:
        self.add_column("#")
        self.add_column("Value")
        self.update_display()

    def update_display(self) -> None:
        if self.ram.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        height = self.size.height - 2  # Account for header/footer
        focus = self.ram.address_comp.address
        start = max(0, focus - height // 2)
        lines = []
        for offset in range(height):
            addr = start + offset
            value = self.ram.memory.get(addr, 0)
            lines.append([f"{addr:04X}",f"{value:04X}"])
        self.clear()
        for line in lines:
            self.add_row(*line)
            self.move_cursor(row = focus - start)