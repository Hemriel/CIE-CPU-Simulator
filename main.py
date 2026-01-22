import asyncio
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

    def __init__(self, cpu: CPU) -> None:
        super().__init__()
        self.cpu = cpu
        self.cpu_display = CPUDisplay(cpu)

    def compose(self):
        yield Header()
        yield self.cpu_display
        yield Footer()

    async def on_mount(self) -> None:
        self._cpu_task = asyncio.create_task(self._run_cpu_loop())

    async def _run_cpu_loop(self) -> None:
        while True:
            finished = self.cpu.step()
            # self.cpu_display.refresh_all()
            if finished:
                break
            await asyncio.sleep(1)


def main() -> None:
    cpu = CPU()
    program_path = Path(__file__).parent / "examples" / "fibo2.bin"
    load_fib2_program(cpu, program_path)
    app = CPUInterfaceApp(cpu)
    app.run()


if __name__ == "__main__":
    main()