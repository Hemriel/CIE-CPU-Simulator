from cpu.cpu_io import IO

from textual.widgets import Label


class IODisplay(Label):
    """Displays a single IO element value and its most recent control signal."""

    def __init__(self, io_element: IO, label: str, reversed : bool = False) -> None:
        super().__init__()
        self.id = label
        self.io_element = io_element
        self.border_title = label
        self.reversed = reversed

    def on_mount(self) -> None:
        self.update_display()

    def update_display(self) -> None:
        if self.io_element.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        value = getattr(self.io_element, "contents", "")
        control = getattr(self.io_element, "_control", None)
        self.border_subtitle = f"{control or 'idle'}"
        self.content = f"{value[::-1] if self.reversed else value}"