from pathlib import Path

from textual.app import App
from textual.widgets import Footer, Header, TextArea
from textual.containers import Horizontal

from cpu.cpu import CPU
from assembler.assembler import compile
from interface.CPUDisplayer import CPUDisplay


def load_fib2_program(cpu: CPU, source: Path) -> None:
    """Populate RAM with the Fibonacci program stored in ``source``."""

    with source.open("r") as handle:
        lines = [line.strip() for line in handle.readlines() if line.strip()]
    program = [int(line, 16) for line in lines]
    cpu.load_program(program)


class CPUInterfaceApp(App):
    """Minimal Textual app that hooks the CPU display and drives a simple clock."""

    CSS_PATH = "interface/styles.tcss"

    BINDINGS = [
        ("ctrl+s", "compile", "Compile"),
        ("t", "tick", "Tick"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, cpu: CPU) -> None:
        super().__init__()
        self.cpu = cpu
        self.cpu_display = CPUDisplay(cpu)
        self.code_editor = TextArea(id="code-editor")
        self.code_editor.show_line_numbers = True
        self.code_editor.line_number_start = 0
        self._finished = False
        self.code_ready = False

    def compose(self):
        yield Header()
        with Horizontal():
            yield self.code_editor
            yield self.cpu_display
        yield Footer()

    def action_tick(self) -> None:
        """Advance the simulation by exactly one RTN step.

        This is intended for debugging / teaching: users can step through the
        fetch-decode-execute micro-operations one at a time and inspect the
        bus wiring and component highlights.
        """

        if self._finished:
            return

        self._finished = self.cpu.step()
        self.cpu_display.refresh_all()

    def action_compile(self) -> None:
        """Compile the code in the code editor and load it into RAM."""

        code = self.code_editor.text
        lines = [line.strip() for line in code.splitlines() if line.strip()]
        program = compile(lines)
        self.cpu.load_program(program)
        self.cpu_display.refresh_all()
        self.code_editor.read_only = True
        self.code_editor.add_class("inactive")
        self.cpu_display.focus()
        self.code_ready = True

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "quit":
            return True
        elif action == "tick":
            return self.code_ready
        elif action == "compile":
            return not self.code_ready
        return None


def main() -> None:
    cpu = CPU()
    program_path = Path(__file__).parent / "examples" / "fibo2.bin"
    load_fib2_program(cpu, program_path)
    app = CPUInterfaceApp(cpu)
    app.run()


if __name__ == "__main__":
    main()