"""Two-pass assembler for the CIE CPU simulator.

Responsibility: 
- This module tokenizes the teaching assembly language, resolves labels and
variables, and emits machine words that the CPU simulator can load.

Illustrates:
- CIE 9618: 4.2 Assembly Language:
    - Show understanding of the relationship between assembly language and machine code.
    - Describe the different stages of the assembly process for a two pass assembler.
    - Trace a given simple assembly language program.
    - Show understanding that a set of instructions are grouped.
    - Show understanding of and be able to use different modes of addressing.
- CIE 9618: 5.2 Language Translators:
    - Show understanding of the need for the translation of an assembly language program.
- CIE 9618: 13.1 User-defined data types (depper than intended by curriculum, this could serve as a complex example):
    - Show understanding of why user-defined data types are necessary.
    - Chose and define an appropriate user defined data type for a given problem.

Entry point:
- The :class:`AssemblerStepper` class, which implements
the two-pass assembler as a simple state machine that can be advanced one "tick"
at a time. Each tick performs a small, easily explainable piece of work.
Except very specific exceptions, other modules should only import and use this class.
Their import should then just contain:
    from assembler.assembler import AssemblerStepper

Includes:
- data classes to represent intermediate and final assembler state: 
:class:`RamWrite`, 
:class:`ParsingResult`,
:class:`AssemblerSnapshot`.
- main stepper class: 
:class:`AssemblerStepper`.
- helper functions for parsing and emitting instructions: 
:func:`parse_line`,
:func:`create_instruction_from_parsing_result`,
:func:`operand_to_int`

Educational intent
------------------
The stepper exists so students can *watch* the classic two-pass assembler:

1. A quick "trim" stage removes comments and blank lines.
2. Pass 1 scans each remaining line to build label tables.
3. Pass 2 emits machine code and (optionally) streams it into RAM.
"""

from common.instructions import get_instruction_by_mnemonic
from common.constants import (
    AddressingMode,
    AssemblingError,
    ComponentName,
    RegisterIndex,
)
from dataclasses import dataclass


### Educational notes on Python operations used in this module ###
#
# Bitwise AND with "& 0xFFFF" (appears throughout this file):
# This operation masks a value to 16 bits (the word size of our simulated CPU).
# - 0xFFFF in binary is 16 ones: 0b1111111111111111
# - Bitwise AND keeps only the lowest 16 bits, discarding any higher bits
# - Example: 0x1ABCD & 0xFFFF = 0xABCD (removed the high bits)
# - This ensures all emitted words fit in the range 0-65535 (16-bit unsigned)
#
# Although bitwise operations in Python are not in the A-level curriculum,
# bitwise AND, OR, XOR, and bit shifting ARE part of the assembly language
# curriculum (CIE 9618: 4.2), so students should be familiar with the concept.
#
# Data classes (appear in the section below):
# Data classes are NOT in the curriculum.
# Here is a detailed explanation: https://docs.python.org/3/library/dataclasses.html
# In a few words, they are a concise way to define classes that mainly store
# data attributes. The __init__, __repr__, __eq__, and other methods are
# automatically generated based on the class attributes.
#
# @property decorator (appears in AssemblerStepper class):
# The @property decorator is not in the curriculum (nor what decorators are).
# It allows to define a method that can be accessed like an attribute.
# For example, instead of calling stepper.phase(), you can just use stepper.phase
# Benefits:
# 1. It makes the code cleaner and easier to read.
# 2. It allows to compute the value on-the-fly while keeping the syntax of an attribute access.
# 3. It can be used to create read-only attributes.


### Data classes for intermediate and final assembler state ###
# These are simple containers for data used by the main stepper class.
# They keep the stepper class smaller, easier to read, and focused on state management.

@dataclass(frozen=True)  # See "Educational notes" at top of file
class RamWrite:
    """One RAM write emitted during pass 2.

    The UI can apply these writes immediately to visualise machine code being
    placed into memory in real time.
    """

    address: int
    value: int


@dataclass  # See "Educational notes" at top of file
class ParsingResult:
    """Intermediate state produced while scanning a single source line."""

    instruction_address: int = -1  # address of this instruction (if any)
    variable_address: int = -1  # relative address of this variable (if any)
    mnemonic: str | None = None  # instruction mnemonic (if any)
    operand_token: str | None = None  # raw operand token (if any)
    new_instruction_label: str | None = None  # new instruction label (if any)
    new_variable_label: str | None = None  # new variable label (if any)
    next_address: int = 0  # next instruction address after this line
    next_variable_address: int = 0  # next variable address after this line


@dataclass  # See "Educational notes" at top of file
class AssemblerSnapshot:
    """A view of the assembler's current state suitable for a UI refresh."""

    phase: str  # current phase name
    pass_number: int  # 0=trim, 1=pass1, 2=pass2
    current_line_index: int  # index of the line being processed
    current_line_text: str | None  # text of the line being processed
    cursor_row: int | None  # editor cursor row to highlight
    instruction_address: int  # next instruction address
    variable_address: int  # next variable address
    instruction_labels: dict[str, int]  # mapping of instruction labels to addresses
    variable_labels: dict[str, int]  # mapping of variable labels to addresses
    highlight_instruction_label: str | None  # instruction label to highlight
    highlight_variable_label: str | None  # variable label to highlight
    emitted_words: list[int]  # all emitted machine words so far
    ram_writes: list[RamWrite]  # all RAM writes emitted so far
    editor_text: str | None = None  # full text for the source editor
    message: str | None = None  # status or error message


### Main assembler stepper class ###
# This class implements the two-pass assembler as a simple state machine
# that can be advanced one "tick" at a time. Each tick performs a small,
# This is the main entry point for the assembler functionality.
# It will be imported and used by other modules, so they don't need to know
# about anything else in this file.

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


    @property  # See "Educational notes" at top of file
    def phase(self) -> str:
        """Return the current assembler phase."""

        return self._phase

    @property  # See "Educational notes" at top of file
    def emitted_words(self) -> list[int]:
        """Return all machine words emitted so far."""

        return list(self._emitted_words)

    def step(self) -> AssemblerSnapshot:
        """Advance the assembler by one tick.

        Catches any internal assembling errors.
        When an error occurs, transitions to the ERROR phase and returns a snapshot
        describing the error state, so the UI can display it.

        Returns:
            A snapshot describing the updated state after this tick.
        """

        if self._phase in (self.PHASE_DONE, self.PHASE_ERROR):
            return self._snapshot(current_line_text=None, ram_writes=[])

        # This assembler raises custom errors, so we need to catch them here.
        # Custom errors allows us to differentiate between expected errors
        # and unexpected ones (like programming bugs).
        try:
            # Dispatch to the appropriate phase handler.
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

        # Should never reach here. But if we do, transition to error state.
        self._phase = self.PHASE_ERROR
        self._error_message = "Internal assembler state error."
        return self._snapshot(
            current_line_text=None, ram_writes=[], message=self._error_message
        )

    def run_to_completion(self, *, max_steps: int = 1_000_000) -> list[int]:
        """Run the stepper until it finishes (non-interactive use).

        Catches any internal assembling errors and raises them to the caller.

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
        """
        Perform one trimming step by processing the next raw line.
        Trimming removes comments and blank lines.
        Returns:
            An AssemblerSnapshot reflecting the updated state after trimming.
        """
        # Guard against running past the end of the raw lines.
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
        # That way, we can watch comments/blank lines disappear as we scan downward.
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
        """
        Perform one pass 1 scanning step by processing the next trimmed line.
        Pass 1 builds label tables without emitting machine code.

        Code emission is impossible if there are forward references to labels
        that have not yet been defined. Therefore, the first pass must scan
        the entire program to build the label tables before any code can be emitted.

        Returns:
            An AssemblerSnapshot reflecting the updated state after scanning.
        """
        # Guard against running past the end of the trimmed lines.
        if self._pass1_index >= len(self._trimmed_lines):
            self._phase = self.PHASE_PASS1_FINALISE
            return self._snapshot(
                current_line_text=None, ram_writes=[], message="Pass 1 complete."
            )

        # Fetch the next line and parse it (turns it into a ParsingResult).
        line = self._trimmed_lines[self._pass1_index]
        parsing_result = _parse_line(
            line, self._instruction_address, self._variable_address
        )
        self._parsing_results.append(parsing_result)

        highlight_instruction_label = None
        highlight_variable_label = None

        # Depending on the optionals set in the ParsingResult,
        # update the label tables.
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

        # Advance the instruction and variable addresses as indicated.
        # To prepare for the next line.
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
        """
        Finalise pass 1 by verifying the program includes END instruction
        and preparing for pass 2.
        Returns:
            An AssemblerSnapshot reflecting the updated state after finalising.
        """

        # Check that program includes END instruction.
        end_found = False
        for parsing_result in reversed(self._parsing_results):  # Start from the end
            if parsing_result.mnemonic is not None:
                if parsing_result.mnemonic == "END":
                    end_found = True
                break
        if not end_found:
            raise AssemblingError("Program must include END instruction.")

        # Compute final variable addresses to place them after instructions in RAM.
        # In most real assemblers, variables are placed before instructions,
        # but placing them after instructions allows us to always start the
        # program at instruction address 0.
        self._instructions_end_address = self._instruction_address
        self._variable_labels_final = {}
        for label, relative in self._variable_labels_relative.items():
            self._variable_labels_final[label] = (
                self._instructions_end_address + relative
            )

        # Split parsing results so pass 2 can emit in the desired order.
        self._pass2_instruction_results = []
        for result in self._parsing_results:
            if result.new_variable_label is None:  # No variable label means instruction
                self._pass2_instruction_results.append(result)

        self._pass2_variable_results = []
        for result in self._parsing_results:
            if result.new_variable_label is not None:
                self._pass2_variable_results.append(result)

        self._pass2_index = 0
        self._emitted_words = []

        self._phase = self.PHASE_PASS2_EMIT_INSTRUCTIONS
        return self._snapshot(
            current_line_text=None,
            ram_writes=[],
            cursor_row=max(0, self._pass1_index - 1),
            message="Pass 1 finalised. Starting pass 2...",
        )

    def _step_pass2_emit_instructions(self) -> AssemblerSnapshot:
        """
        Perform one pass 2 instruction emission step by processing the next instruction.

        Now that all labels have been resolved, we can emit machine code.
        We start by emitting all instructions in a row. Variables will be emitted
        afterwards.

        We choose to start emitting instructions first so that the program
        always starts at address 0. In real situations, the start address is 
        handled by the operating system, not the assembler.

        Returns:
            An AssemblerSnapshot reflecting the updated state after emission.
        """
        instruction_offset: int = len(self._pass2_variable_results)

        # Guard against running past the end of the instruction results.
        if self._pass2_index >= len(self._pass2_instruction_results):
            self._phase = self.PHASE_PASS2_EMIT_VARIABLES
            self._pass2_index = 0
            return self._snapshot(
                current_line_text=None,
                cursor_row=max(0, self._pass2_index - 1 + instruction_offset),
                ram_writes=[],
                message="Instructions emitted. Emitting variables...",
            )

        # Turn the next ParsingResult into machine words.
        # Some instructions emit one word; others emit two.
        parsing_result = self._pass2_instruction_results[self._pass2_index]
        words, looked_at_instruction, looked_at_variable = _create_instruction_from_parsing_result(
            parsing_result,
            instruction_labels=self._instruction_labels,
            variable_labels=self._variable_labels_final,
        )

        # Emit the words into RAM at the correct addresses.
        # The first word goes at the instruction address recorded during pass 1.
        # Subsequent words (if any) go at consecutive addresses.
        base_address = parsing_result.instruction_address
        ram_writes = []
        for offset, word in enumerate(words):
            address = base_address + offset
            ram_writes.append(RamWrite(address=address, value=word & 0xFFFF))  # See "Educational notes" at top of file
            self._emitted_words.append(word & 0xFFFF)  # See "Educational notes" at top of file

        # Advance to the next instruction for the next step.
        self._pass2_index += 1
        return self._snapshot(
            current_line_text=parsing_result.mnemonic,
            ram_writes=ram_writes,
            cursor_row=max(0, self._pass2_index - 1 + instruction_offset),
            highlight_instruction_label=looked_at_instruction,
            highlight_variable_label=looked_at_variable,
            message="Pass 2: emitting instructions...",
        )

    def _step_pass2_emit_variables(self) -> AssemblerSnapshot:
        """
        Perform one pass 2 variable emission step by processing the next variable.

        After all instructions have been emitted, we emit the variables.

        Returns:
            An AssemblerSnapshot reflecting the updated state after emission.
        """

        # Guard against running past the end of the variable results.
        if self._pass2_index >= len(self._pass2_variable_results):
            self._phase = self.PHASE_DONE
            return self._snapshot(
                current_line_text=None, 
                ram_writes=[], 
                cursor_row=max(0, self._pass2_index - 1), 
                message="Assembling complete."
            )

        # Turn the next ParsingResult into machine words.
        parsing_result = self._pass2_variable_results[self._pass2_index]
        words, _, _ = _create_instruction_from_parsing_result(
            parsing_result,
            instruction_labels=self._instruction_labels,
            variable_labels=self._variable_labels_final,
        )

        # Variable definitions always emit exactly one word.
        address = self._instructions_end_address + parsing_result.variable_address
        value = words[0] & 0xFFFF  # Ensure 16-bit word (see "Educational notes" at top of file)
        ram_writes = [RamWrite(address=address, value=value)]
        self._emitted_words.append(value)

        # Advance to the next variable for the next step.
        self._pass2_index += 1
        return self._snapshot(
            current_line_text=parsing_result.new_variable_label,
            ram_writes=ram_writes,
            cursor_row=max(0, self._pass2_index - 1),
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
        """Create a snapshot of the current assembler state."""
        if self._phase == self.PHASE_TRIM:
            current_index = self._trim_index
            pass_number = 0
        elif self._phase in (self.PHASE_PASS1_SCAN, self.PHASE_PASS1_FINALISE):
            current_index = self._pass1_index
            pass_number = 1
        else:
            current_index = self._pass2_index
            pass_number = 2

        # Spaces added around '=' for better readability.
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


### Helper functions for parsing and emitting instructions ###
# These are outside the stepper class for multiple reasons:
# 1. They keep the stepper class smaller, easier to read, and focused on state management.
# 2. They can be tested independently of the stepper state machine.
# 3. They could be reused in other contexts if needed (although they shouldn't out of this module).


def _parse_line(
    line: str, instruction_address: int, variable_address: int
) -> ParsingResult:
    """Translate a source line into the parsing record used in both passes.
    
    This function handles three main cases:
    1. Labels followed by instructions (e.g., "LOOP: ADD #5")
    2. Labels followed by immediate values (e.g., "COUNT: #10")
    3. Instructions without labels (e.g., "END")
    
    Why both addresses? Pass 1 maintains separate counters for instructions
    (which execute) and variables (which store data). This lets the assembler
    place variables after instructions in memory, so programs always start at
    address 0.

    Args:
        line: One trimmed source line that may contain a label, instruction, or
            immediate variable definition.
        instruction_address: Current instruction counter (increments by 1 or 2
            depending on whether instruction has long operand).
        variable_address: Current variable slot counter (increments by 1 per
            variable definition).

    Returns:
        A ParsingResult that records:
        - How far instruction/variable addresses advanced (next_address fields)
        - What mnemonic/operand was found (if any)
        - Any new label discovered (instruction or variable)
        
    Raises:
        AssemblingError: If line format is invalid or mnemonic is unknown.
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


def _create_instruction_from_parsing_result(
    parsing_result: ParsingResult,
    instruction_labels: dict[str, int],
    variable_labels: dict[str, int],
) -> tuple[list[int], str | None, str | None]:
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
        One or two words representing the instruction plus optional operand,
        plus optionally the instruction label and variable label looked at.
    """
    result = []
    looked_at_instruction = None
    looked_at_variable = None

    # Handle variable definitions, and returns early.
    if parsing_result.new_variable_label is not None:
        looked_at_variable = parsing_result.new_variable_label
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
        result.append(value & 0xFFFF)  # See "Educational notes" at top of file
        return result, None, looked_at_variable

    # If we didn't return early, it's an instruction
    mnemonic = parsing_result.mnemonic
    if mnemonic is None:
        raise AssemblingError("Instruction mnemonic is missing.")
    instruction_defs = get_instruction_by_mnemonic(mnemonic)
    if not instruction_defs:
        raise AssemblingError(f"Unknown instruction mnemonic '{mnemonic}'.")

    # Start by assuming the first definition is correct
    instruction_def = instruction_defs[0]
    
    # If there are multiple definitions for the same mnemonic, we need to
    # disambiguate based on the operand.
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

    # convert mnemonic to opcode
    opcode = instruction_def.opcode
    instruction_word = opcode << 8

    # instruction with no operand
    if instruction_def.addressing_mode == AddressingMode.NONE:
        result.append(instruction_word & 0xFFFF)  # See "Educational notes" at top of file
        return result, None, None

    operand, looked_at_instruction, looked_at_variable = _operand_to_int(
        parsing_result.operand_token, instruction_labels, variable_labels
    ) 
    if not instruction_def.long_operand:
        instruction_word += operand
        result.append(instruction_word & 0xFFFF)  # See "Educational notes" at top of file
    else:
        result.append(instruction_word & 0xFFFF)  # See "Educational notes" at top of file
        result.append(
            operand
            & 0xFFFF  # See "Educational notes" at top of file
        )

    return result, looked_at_instruction, looked_at_variable


def _operand_to_int(
    operand_token: str | None,
    instruction_labels: dict[str, int],
    variable_labels: dict[str, int],
) -> tuple[int, str | None, str | None]:
    """Resolve an operand token into a 16-bit value.

    The operand could be an immediate literal, a label that points to code/data,
    or a register alias such as ACC or PC. RegisterIndex ensures register names
    map back to the numeric bus identifier defined in the constants.
    Args:
        operand_token: Raw token parsed after the mnemonic.
        instruction_labels: Label -> address map for instructions.
        variable_labels: Label -> address map for variables.

    Returns:
        The resolved 16-bit integer value to embed in the instruction,
        plus optionally the instruction label and variable label looked at.
    """
    looked_at_instruction = None
    looked_at_variable = None
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
        looked_at_instruction = operand_token
    elif operand_token in variable_labels:
        value = variable_labels[operand_token]
        looked_at_variable = operand_token
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
    return value, looked_at_instruction, looked_at_variable
