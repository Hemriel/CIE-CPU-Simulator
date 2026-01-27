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

    LIMIT_ROWS = 5

    def __init__(self, ram: RAM) -> None:
        super().__init__()
        self.id = "ram-data-display"
        self.ram = ram
        self.display_start = 0
        self.cursor_type = "row"

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
        self.update_start(focus, height)
        lines = []
        for offset in range(height):
            addr = self.display_start + offset
            value = self.ram.memory.get(addr, 0)
            lines.append([f"{addr:04X}",f"{value:04X}"])
        self.clear()
        for line in lines:
            self.add_row(*line)
            self.move_cursor(row = focus - self.display_start)

    def update_start(self, focus, height) -> None:
        """ Determine the first address to display based on the newly focused address. 
        Should keep the same start if still visible and out of the LIMIT_ROWS range.
        Else, center the focus address in the display.
        """
        not_visible = focus < self.display_start or focus >= self.display_start + height
        in_limit_rows = (focus < self.display_start + self.LIMIT_ROWS) or (focus >= self.display_start + height - self.LIMIT_ROWS)
        if not_visible or in_limit_rows:
            self.display_start = max(0, focus - height // 2)