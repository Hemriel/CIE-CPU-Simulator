from pathlib import Path

from textual.app import App
from textual.widgets import Footer, Header

from cpu.cpu import CPU
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
        ("t", "tick", "Tick"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, cpu: CPU) -> None:
        super().__init__()
        self.cpu = cpu
        self.cpu_display = CPUDisplay(cpu)
        self._finished = False

    def compose(self):
        yield Header()
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


def main() -> None:
    cpu = CPU()
    program_path = Path(__file__).parent / "examples" / "fibo2.bin"
    load_fib2_program(cpu, program_path)
    app = CPUInterfaceApp(cpu)
    app.run()


if __name__ == "__main__":
    main()