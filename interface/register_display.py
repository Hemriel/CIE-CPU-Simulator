from cpu.register import Register

from rich.text import Text
from textual.widgets import Label


class RegisterDisplay(Label):
    """Displays a single register value and its most recent control signal."""

    def __init__(self, register: Register, label: str) -> None:
        super().__init__()
        self.id = label
        self.register = register
        self.border_title = label

    def on_mount(self) -> None:
        self.update_display()

    def update_display(self) -> None:
        if self.register.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        value = getattr(self.register, "_value", 0)
        control = getattr(self.register, "_control", None)
        self.border_subtitle = f"{control or 'idle'}"
        self.content = Text(f"     {value:04X}")