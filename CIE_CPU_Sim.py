from pathlib import Path

from textual.app import App
from textual.widgets import Footer, Header, Label, TextArea
from textual.containers import Horizontal, Vertical

from cpu.cpu import CPU
from assembler.assembler import AssemblerStepper
from interface.CPUDisplayer import CPUDisplay
from interface.instruction_label_display import InstructionLabelDisplay
from interface.variable_label_display import VariableLabelDisplay


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

        self.instruction_labels_display = InstructionLabelDisplay()
        self.variable_labels_display = VariableLabelDisplay()

        self.status_line = Label("please input source code", id="status-line")

        self.assembler_stepper: AssemblerStepper | None = None
        self.assembling = False

        self._finished = False
        self.code_ready = False

    def compose(self):
        yield Header()
        with Horizontal():
            yield self.code_editor
            with Vertical(id="labels-column"):
                yield self.instruction_labels_display
                yield self.variable_labels_display
            yield self.cpu_display
        yield self.status_line
        yield Footer()

    def action_tick(self) -> None:
        """Advance the simulation by exactly one RTN step.

        This is intended for debugging / teaching: users can step through the
        fetch-decode-execute micro-operations one at a time and inspect the
        bus wiring and component highlights.
        """

        if self.assembling and self.assembler_stepper is not None:
            snapshot = self.assembler_stepper.step()
            if snapshot.editor_text is not None:
                self.code_editor.text = snapshot.editor_text

            # Keep the modified line in view.
            if snapshot.cursor_row is not None:
                self.code_editor.select_line(max(0, snapshot.cursor_row))
                self.code_editor.scroll_cursor_visible(center=True)

            self.instruction_labels_display.update_labels(
                snapshot.instruction_labels, highlight=snapshot.highlight_instruction_label
            )
            self.variable_labels_display.update_labels(
                snapshot.variable_labels, highlight=snapshot.highlight_variable_label
            )

            if snapshot.message:
                self.status_line.update(snapshot.message)

            # Stream any emitted words into RAM so students can watch memory fill.
            if not snapshot.ram_writes:
                self.cpu_display.ram_data_display.add_class("inactive")
                self.cpu.ram.last_active = False
            else:
                self.cpu_display.ram_data_display.remove_class("inactive")
                self.cpu.ram.last_active = True
            for write in snapshot.ram_writes:
                self.cpu.ram_address.write(write.address)
                self.cpu.ram.write(write.value)

            self.cpu_display.refresh_all()

            if snapshot.phase == "DONE":
                self.assembling = False
                self.code_ready = True
                self.code_editor.read_only = True
                self.code_editor.add_class("inactive")
                self.instruction_labels_display.add_class("inactive")
                self.variable_labels_display.add_class("inactive")
                self.cpu_display.focus()
            return

        if self._finished:
            return

        self._finished = self.cpu.step()
        self.status_line.update("running program" if not self._finished else "program finished")
        self.cpu_display.refresh_all()

    def action_compile(self) -> None:
        """Start the interactive (tickable) two-pass assembly process."""

        if not self.code_editor.text.strip():
            self.status_line.update("please input source code")
            return

        # Reset runtime state.
        self._finished = False
        self.code_ready = False
        self.assembling = True

        self.status_line.update("Trimming source...")

        # Lock editing while assembling so the live trimming is predictable.
        self.code_editor.read_only = True
        self.code_editor.remove_class("inactive")

        source_lines = self.code_editor.text.splitlines()
        self.assembler_stepper = AssemblerStepper(source_lines)

        # Clear existing label displays.
        self.instruction_labels_display.remove_class("inactive")
        self.variable_labels_display.remove_class("inactive")
        self.instruction_labels_display.update_labels({})
        self.variable_labels_display.update_labels({})

        # Reset RAM focus so the first emitted word is obvious in the table.
        self.cpu.ram_address.write(0)
        self.cpu.pc.write(0)
        self.cpu_display.refresh_all()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "quit":
            return True
        elif action == "tick":
            return self.assembling or self.code_ready
        elif action == "compile":
            return (not self.assembling) and (not self.code_ready)
        return None


def main() -> None:
    cpu = CPU()
    app = CPUInterfaceApp(cpu)
    app.run()


if __name__ == "__main__":
    main()