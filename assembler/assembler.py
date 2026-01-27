"""Two-pass assembler for the CIE CPU simulator.

This module tokenizes the teaching assembly language, resolves labels and
variables, and emits machine words that the CPU simulator can load.

It also provides :class:`AssemblerStepper`, a small state machine that can be
advanced one "tick" at a time.

Educational intent
------------------
The stepper exists so students can *watch* the classic two-pass assembler:

1. A quick "trim" stage removes comments and blank lines.
2. Pass 1 scans each remaining line to build label tables.
3. Pass 2 emits machine code and (optionally) streams it into RAM.

The existing :func:`compile` helper remains available for non-interactive use.
"""

from common.instructions import get_instruction_by_mnemonic
from common.constants import (
    AddressingMode,
    AssemblingError,
    ComponentName,
    RegisterIndex,
)
from dataclasses import dataclass


@dataclass(frozen=True)
class RamWrite:
    """One RAM write emitted during pass 2.

    The UI can apply these writes immediately to visualise machine code being
    placed into memory in real time.
    """

    address: int
    value: int


@dataclass
class ParsingResult:
    """Intermediate state produced while scanning a single source line."""

    instruction_address: int = -1
    variable_address: int = -1
    mnemonic: str | None = None
    operand_token: str | None = None
    new_instruction_label: str | None = None
    new_variable_label: str | None = None
    next_address: int = 0
    next_variable_address: int = 0


@dataclass
class AssemblerSnapshot:
    """A view of the assembler's current state suitable for a UI refresh."""

    phase: str
    pass_number: int
    current_line_index: int
    current_line_text: str | None
    cursor_row: int | None
    instruction_address: int
    variable_address: int
    instruction_labels: dict[str, int]
    variable_labels: dict[str, int]
    highlight_instruction_label: str | None
    highlight_variable_label: str | None
    emitted_words: list[int]
    ram_writes: list[RamWrite]
    editor_text: str | None = None
    message: str | None = None


class AssemblerStepper:
    """Advance the assembler a single micro-step at a time.

    The stepper is deliberately simple: each call to :meth:`step` advances one
    small piece of work that is easy to explain on a whiteboard.

    The phases are:
    - TRIM: remove comments/blank lines *progressively*.
    - PASS1_SCAN: build label tables line-by-line.
    - PASS1_FINALISE: validate END and compute final variable addresses.
    - PASS2_EMIT_INSTRUCTIONS: emit machine code for instruction lines.
    - PASS2_EMIT_VARIABLES: emit variable values after instructions.
    - DONE / ERROR
    """

    PHASE_TRIM = "TRIM"
    PHASE_PASS1_SCAN = "PASS1_SCAN"
    PHASE_PASS1_FINALISE = "PASS1_FINALISE"
    PHASE_PASS2_EMIT_INSTRUCTIONS = "PASS2_EMIT_INSTRUCTIONS"
    PHASE_PASS2_EMIT_VARIABLES = "PASS2_EMIT_VARIABLES"
    PHASE_DONE = "DONE"
    PHASE_ERROR = "ERROR"

    def __init__(self, source_lines: list[str]) -> None:
        """Create a new stepper for the given source program.

        Args:
            source_lines: Raw source lines. These may include comments and blank
                lines; the TRIM phase will remove them progressively.
        """

        self._raw_lines = list(source_lines)
        self._trimmed_lines: list[str] = []
        self._trim_index = 0

        self._phase = self.PHASE_TRIM

        self._instruction_address = 0
        self._variable_address = 0

        self._parsing_results: list[ParsingResult] = []
        self._instruction_labels: dict[str, int] = {}
        self._variable_labels_relative: dict[str, int] = {}
        self._variable_labels_final: dict[str, int] = {}

        self._pass1_index = 0
        self._instructions_end_address = 0

        self._pass2_instruction_results: list[ParsingResult] = []
        self._pass2_variable_results: list[ParsingResult] = []
        self._pass2_index = 0

        self._emitted_words: list[int] = []
        self._error_message: str | None = None

    @property
    def phase(self) -> str:
        """Return the current assembler phase."""

        return self._phase

    @property
    def emitted_words(self) -> list[int]:
        """Return all machine words emitted so far."""

        return list(self._emitted_words)

    def step(self) -> AssemblerSnapshot:
        """Advance the assembler by one tick.

        Returns:
            A snapshot describing the updated state after this tick.
        """

        if self._phase in (self.PHASE_DONE, self.PHASE_ERROR):
            return self._snapshot(current_line_text=None, ram_writes=[])

        try:
            if self._phase == self.PHASE_TRIM:
                return self._step_trim()
            elif self._phase == self.PHASE_PASS1_SCAN:
                return self._step_pass1_scan()
            elif self._phase == self.PHASE_PASS1_FINALISE:
                return self._step_pass1_finalise()
            elif self._phase == self.PHASE_PASS2_EMIT_INSTRUCTIONS:
                return self._step_pass2_emit_instructions()
            elif self._phase == self.PHASE_PASS2_EMIT_VARIABLES:
                return self._step_pass2_emit_variables()
        except AssemblingError as exc:
            self._phase = self.PHASE_ERROR
            self._error_message = str(exc)
            return self._snapshot(
                current_line_text=None, ram_writes=[], message=str(exc)
            )

        self._phase = self.PHASE_ERROR
        self._error_message = "Internal assembler state error."
        return self._snapshot(
            current_line_text=None, ram_writes=[], message=self._error_message
        )

    def run_to_completion(self, *, max_steps: int = 1_000_000) -> list[int]:
        """Run the stepper until it finishes (non-interactive use).

        Args:
            max_steps: Safety limit to avoid infinite loops if a bug is introduced.

        Returns:
            The final list of emitted machine words.
        """

        for _ in range(max_steps):
            snapshot = self.step()
            if snapshot.phase == self.PHASE_ERROR:
                raise AssemblingError(snapshot.message or "Assembling failed.")
            if snapshot.phase == self.PHASE_DONE:
                return snapshot.emitted_words
        raise AssemblingError("Assembler did not finish within the step limit.")

    def _step_trim(self) -> AssemblerSnapshot:
        if self._trim_index >= len(self._raw_lines):
            # Finished trimming; move into pass 1.
            self._phase = self.PHASE_PASS1_SCAN
            # One last editor update to show the final trimmed listing.
            editor_text = "\n".join(self._trimmed_lines)
            return self._snapshot(
                current_line_text=None,
                ram_writes=[],
                editor_text=editor_text,
                message="Trim complete.",
            )

        raw_line = self._raw_lines[self._trim_index]
        trimmed = raw_line.split(";", 1)[0].strip()
        cursor_row: int
        if trimmed:
            self._trimmed_lines.append(trimmed)
            # This line was kept (possibly modified by comment trimming).
            cursor_row = max(0, len(self._trimmed_lines) - 1)
        else:
            # This line is being deleted; point at the next still-unprocessed line.
            cursor_row = len(self._trimmed_lines)

        self._trim_index += 1

        # Educational UI trick: show the trimmed prefix and the original suffix.
        # Students can watch comments/blank lines disappear as we scan downward.
        editor_text = "\n".join(
            self._trimmed_lines + self._raw_lines[self._trim_index :]
        )
        return self._snapshot(
            current_line_text=raw_line,
            ram_writes=[],
            cursor_row=cursor_row,
            editor_text=editor_text,
            message="Trimming source...",
        )

    def _step_pass1_scan(self) -> AssemblerSnapshot:
        if self._pass1_index >= len(self._trimmed_lines):
            self._phase = self.PHASE_PASS1_FINALISE
            return self._snapshot(
                current_line_text=None, ram_writes=[], message="Pass 1 complete."
            )

        line = self._trimmed_lines[self._pass1_index]
        parsing_result = parse_line(
            line, self._instruction_address, self._variable_address
        )
        self._parsing_results.append(parsing_result)

        highlight_instruction_label = None
        highlight_variable_label = None

        if parsing_result.new_instruction_label:
            self._instruction_labels[parsing_result.new_instruction_label] = (
                self._instruction_address
            )
            highlight_instruction_label = parsing_result.new_instruction_label
        if parsing_result.new_variable_label:
            self._variable_labels_relative[parsing_result.new_variable_label] = (
                self._variable_address
            )
            highlight_variable_label = parsing_result.new_variable_label

        self._instruction_address = parsing_result.next_address
        self._variable_address = parsing_result.next_variable_address
        self._pass1_index += 1

        return self._snapshot(
            current_line_text=line,
            ram_writes=[],
            cursor_row=max(0, self._pass1_index - 1),
            highlight_instruction_label=highlight_instruction_label,
            highlight_variable_label=highlight_variable_label,
            message="Pass 1: scanning...",
        )

    def _step_pass1_finalise(self) -> AssemblerSnapshot:
        # Check that program includes END instruction.
        end_found = False
        for parsing_result in reversed(self._parsing_results):
            if parsing_result.mnemonic is not None:
                if parsing_result.mnemonic == "END":
                    end_found = True
                break
        if not end_found:
            raise AssemblingError("Program must include END instruction.")

        # Compute final variable addresses to place them after instructions in RAM.
        self._instructions_end_address = self._instruction_address
        self._variable_labels_final = {
            label: self._instructions_end_address + relative
            for label, relative in self._variable_labels_relative.items()
        }

        # Split parsing results so pass 2 can emit in the desired order.
        self._pass2_instruction_results = [
            result
            for result in self._parsing_results
            if result.new_variable_label is None
        ]
        self._pass2_variable_results = [
            result
            for result in self._parsing_results
            if result.new_variable_label is not None
        ]
        self._pass2_index = 0
        self._emitted_words = []

        self._phase = self.PHASE_PASS2_EMIT_INSTRUCTIONS
        return self._snapshot(
            current_line_text=None,
            ram_writes=[],
            cursor_row=None,
            message="Pass 1 finalised. Starting pass 2...",
        )

    def _step_pass2_emit_instructions(self) -> AssemblerSnapshot:
        if self._pass2_index >= len(self._pass2_instruction_results):
            self._phase = self.PHASE_PASS2_EMIT_VARIABLES
            self._pass2_index = 0
            return self._snapshot(
                current_line_text=None,
                ram_writes=[],
                message="Instructions emitted. Emitting variables...",
            )

        parsing_result = self._pass2_instruction_results[self._pass2_index]
        words = create_instruction_from_parsing_result(
            parsing_result,
            instruction_labels=self._instruction_labels,
            variable_labels=self._variable_labels_final,
        )

        base_address = parsing_result.instruction_address
        ram_writes = []
        for offset, word in enumerate(words):
            address = base_address + offset
            ram_writes.append(RamWrite(address=address, value=word & 0xFFFF))
            self._emitted_words.append(word & 0xFFFF)

        self._pass2_index += 1
        return self._snapshot(
            current_line_text=parsing_result.mnemonic,
            ram_writes=ram_writes,
            cursor_row=None,
            message="Pass 2: emitting instructions...",
        )

    def _step_pass2_emit_variables(self) -> AssemblerSnapshot:
        if self._pass2_index >= len(self._pass2_variable_results):
            self._phase = self.PHASE_DONE
            return self._snapshot(
                current_line_text=None, ram_writes=[], message="Assembling complete."
            )

        parsing_result = self._pass2_variable_results[self._pass2_index]
        words = create_instruction_from_parsing_result(
            parsing_result,
            instruction_labels=self._instruction_labels,
            variable_labels=self._variable_labels_final,
        )
        # Variable definitions always emit exactly one word.
        address = self._instructions_end_address + parsing_result.variable_address
        value = words[0] & 0xFFFF
        ram_writes = [RamWrite(address=address, value=value)]
        self._emitted_words.append(value)

        self._pass2_index += 1
        return self._snapshot(
            current_line_text=parsing_result.new_variable_label,
            ram_writes=ram_writes,
            cursor_row=None,
            highlight_variable_label=parsing_result.new_variable_label,
            message="Pass 2: emitting variables...",
        )

    def _snapshot(
        self,
        *,
        current_line_text: str | None,
        ram_writes: list[RamWrite],
        cursor_row: int | None = None,
        editor_text: str | None = None,
        highlight_instruction_label: str | None = None,
        highlight_variable_label: str | None = None,
        message: str | None = None,
    ) -> AssemblerSnapshot:
        if self._phase == self.PHASE_TRIM:
            current_index = self._trim_index
            pass_number = 0
        elif self._phase in (self.PHASE_PASS1_SCAN, self.PHASE_PASS1_FINALISE):
            current_index = self._pass1_index
            pass_number = 1
        else:
            current_index = self._pass2_index
            pass_number = 2

        return AssemblerSnapshot(
            phase=self._phase,
            pass_number=pass_number,
            current_line_index=current_index,
            current_line_text=current_line_text,
            cursor_row=cursor_row,
            instruction_address=self._instruction_address,
            variable_address=self._variable_address,
            instruction_labels=dict(self._instruction_labels),
            variable_labels=dict(
                self._variable_labels_final or self._variable_labels_relative
            ),
            highlight_instruction_label=highlight_instruction_label,
            highlight_variable_label=highlight_variable_label,
            emitted_words=list(self._emitted_words),
            ram_writes=ram_writes,
            editor_text=editor_text,
            message=message or self._error_message,
        )


def trim_source(source_lines: list[str]) -> list[str]:
    """Drop comments and blank lines so line numbering stays compact.

    Allow to focus on the instructions and labels that remain in the
    trimmed listing without being distracted by trailing comments or empty
    space. The order is preserved so label resolution stays predictable.
    """
    trimmed_lines = []
    for line in source_lines:
        line = line.split(";", 1)[0].strip()
        if line:
            trimmed_lines.append(line)
    return trimmed_lines


def compile(source_lines: list[str]) -> list[int]:
    """Convert raw assembly text into a contiguous list of machine words.

    This implements the canonical two-pass assembler:
    1. Scan the program, record label positions, and allocate variable slots
       without emitting any machine code.
    2. Revisit the recorded lines to produce the final opcode and operand
       words once every reference can be resolved.

    Args:
        source_lines: Assembly text lines including comments and labels.

    Returns:
        A list of 16-bit integers representing opcodes and operands.
    """
    # Keep the old API, but implement it in terms of the stepper.
    stepper = AssemblerStepper(source_lines)
    return stepper.run_to_completion()


def parse_line(
    line: str, instruction_address: int, variable_address: int
) -> ParsingResult:
    """Translate a source line into the parsing record used in both passes.

    Args:
        line: One trimmed source line that may contain a label, instruction, or
            immediate variable definition.
        instruction_address: Current program counter used for label resolution.
        variable_address: Slot counter used for consecutive variable storage.

    Returns:
        A ParsingResult that records how far instructions/variables advanced and
        what mnemonic/operand (if any) was found.
    """
    result = ParsingResult(
        instruction_address=instruction_address, variable_address=variable_address
    )

    # label are followed by ":" so split on that first
    if ":" in line:
        label, rest_of_line = line.split(":", 1)
        label = label.strip().upper()
        rest_of_line = rest_of_line.strip()
        if not rest_of_line or not len(rest_of_line.split()) in [1, 2]:
            raise AssemblingError(
                f"""In {line}: Label '{label}' must be followed by an instruction or immediate value.
correct formats:
- <LABEL>: <MNEMONIC> <OPERAND>
- <LABEL>: <IMMEDIATE VALUE>"""
            )
        elif len(rest_of_line.split()) == 2:
            # label followed by instruction
            result.new_instruction_label = label
            result.mnemonic, result.operand_token = rest_of_line.split()
            result.instruction_address = instruction_address
            instruction_def = get_instruction_by_mnemonic(result.mnemonic)
            if not instruction_def:
                raise AssemblingError(
                    f"Unknown instruction mnemonic '{result.mnemonic}'."
                )
            elif instruction_def[0].long_operand:
                result.next_address = instruction_address + 2
            else:
                result.next_address = instruction_address + 1
            return result
        elif rest_of_line in ["IN", "OUT", "END"]:
            # label followed by instruction without operand
            result.new_instruction_label = label
            result.mnemonic = rest_of_line
            result.instruction_address = instruction_address
            result.next_address = instruction_address + 1
            return result
        else:
            # label followed by immediate value
            result.new_variable_label = label
            result.operand_token = rest_of_line
            if not rest_of_line.startswith(("#", "B", "&")):
                raise AssemblingError(
                    f"Invalid immediate value '{rest_of_line}'. Immediate values must start with '#', 'B', or '&'."
                )
            result.variable_address = variable_address
            result.next_variable_address = variable_address + 1
            return result

    # No label present
    parts = line.split()
    if len(parts) == 1:
        # instruction without operand
        result.mnemonic = parts[0]
        instruction_def = get_instruction_by_mnemonic(result.mnemonic)
        if not instruction_def:
            raise AssemblingError(f"Unknown instruction mnemonic '{result.mnemonic}'.")
        result.next_address = instruction_address + 1
        return result
    elif len(parts) == 2:
        # instruction with operand
        result.mnemonic, result.operand_token = parts
        instruction_def = get_instruction_by_mnemonic(result.mnemonic)
        if not instruction_def:
            raise AssemblingError(f"Unknown instruction mnemonic '{result.mnemonic}'.")
        elif instruction_def[0].long_operand:
            result.next_address = instruction_address + 2
        else:
            result.next_address = instruction_address + 1
        return result
    else:
        raise AssemblingError(f"Invalid line format: '{line}'.")


def create_instruction_from_parsing_result(
    parsing_result: ParsingResult,
    instruction_labels: dict[str, int],
    variable_labels: dict[str, int],
) -> list[int]:
    """Emit the machine word(s) for a single parsing result.

    Variables are converted to their immediate values while instructions are
    resolved once all label addresses are known. This function therefore
    straddles both assembler passes: it runs during the second pass but uses the
    metadata collected earlier.

    Args:
        parsing_result: Recorded scan state for the line being emitted.
        instruction_labels: Mapping from instruction labels to absolute
            addresses.
        variable_labels: Mapping from variable labels to absolute addresses.

    Returns:
        One or two words representing the instruction plus optional operand.
    """
    result = []

    # Handle variable definitions
    if parsing_result.new_variable_label is not None:
        operand_token = parsing_result.operand_token
        if operand_token is None:
            raise AssemblingError("Variable definition missing value.")
        if operand_token.startswith("#"):
            value = int(operand_token[1:], 10)
        elif operand_token.startswith("B"):
            value = int(operand_token[1:], 2)
        elif operand_token.startswith("&"):
            value = int(operand_token[1:], 16)
        else:
            raise AssemblingError(
                f"Invalid immediate value '{operand_token}'. Immediate values must start with '#', 'B', or '&'."
            )
        if not (0 <= value <= 0xFFFF):
            raise AssemblingError(
                f"Immediate value '{value}' out of range (0 to 65535)."
            )
        result.append(value & 0xFFFF)
        return result

    # Handle instructions
    mnemonic = parsing_result.mnemonic
    if mnemonic is None:
        raise AssemblingError("Instruction mnemonic is missing.")
    instruction_defs = get_instruction_by_mnemonic(mnemonic)
    if not instruction_defs:
        raise AssemblingError(f"Unknown instruction mnemonic '{mnemonic}'.")

    if len(instruction_defs) > 1:
        # Check for operand to determine correct instruction
        operand_token = parsing_result.operand_token
        if operand_token is None:
            raise AssemblingError(
                f"Ambiguous instruction '{mnemonic}' requires an operand."
            )
        if operand_token.startswith(("#", "B", "&")):
            addressing_mode = AddressingMode.IMMEDIATE
            for instr_def in instruction_defs:
                if instr_def.addressing_mode == addressing_mode:
                    instruction_def = instr_def
                    break
        else:
            # Non-literals choose the register/label variant so the assembler
            # consistently picks the correct opcode.
            for instr_def in instruction_defs:
                if instr_def.addressing_mode != AddressingMode.IMMEDIATE:
                    instruction_def = instr_def
                    break
    else:
        instruction_def = instruction_defs[0]

    # convert mnemonic to opcode
    opcode = instruction_def.opcode
    instruction_word = opcode << 8

    # instruction with no operand
    if instruction_def.addressing_mode == AddressingMode.NONE:
        result.append(instruction_word & 0xFFFF)
        return result

    if not instruction_def.long_operand:
        instruction_word += operand_to_int(
            parsing_result.operand_token, instruction_labels, variable_labels
        )
        result.append(instruction_word & 0xFFFF)
    else:
        result.append(instruction_word & 0xFFFF)
        result.append(
            operand_to_int(
                parsing_result.operand_token, instruction_labels, variable_labels
            )
            & 0xFFFF
        )

    return result


def operand_to_int(
    operand_token: str | None,
    instruction_labels: dict[str, int],
    variable_labels: dict[str, int],
) -> int:
    """Resolve an operand token into a 16-bit value.

    The operand could be an immediate literal, a label that points to code/data,
    or a register alias such as ACC or PC. RegisterIndex ensures register names
    map back to the numeric bus identifier defined in the constants.
    Args:
        operand_token: Raw token parsed after the mnemonic.
        instruction_labels: Label -> address map for instructions.
        variable_labels: Label -> address map for variables.

    Returns:
        The resolved 16-bit integer value to embed in the instruction.
    """
    if operand_token is None:
        raise AssemblingError("Operand is missing.")
    if operand_token.startswith("#"):
        value = int(operand_token[1:], 10)
    elif operand_token.startswith("B"):
        value = int(operand_token[1:], 2)
    elif operand_token.startswith("&"):
        value = int(operand_token[1:], 16)
    elif operand_token in instruction_labels:
        value = instruction_labels[operand_token]
    elif operand_token in variable_labels:
        value = variable_labels[operand_token]
    elif operand_token in [
        ComponentName.ACC,
        ComponentName.IX,
        ComponentName.PC,
        ComponentName.MAR,
        ComponentName.MDR,
        ComponentName.CIR,
    ]:
        value = RegisterIndex[ComponentName(operand_token)]
    else:
        raise AssemblingError(f"Unknown operand or label '{operand_token}'.")
    if not (0 <= value <= 0xFFFF):
        raise AssemblingError(f"Operand value '{value}' out of range (0 to 65535).")
    return value
