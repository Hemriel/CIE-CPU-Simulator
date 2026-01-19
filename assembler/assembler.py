"""Two-pass assembler for the CIE CPU simulator.

This module tokenizes the teaching assembly language, resolves labels and
variables, and emits machine words that the CPU simulator can load.
"""

from common.instructions import get_instruction_by_mnemonic
from common.constants import (
    AddressingMode,
    AssemblingError,
    ComponentName,
    RegisterIndex,
)
from dataclasses import dataclass


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


def assemble(source_lines: list[str]) -> list[int]:
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
    instruction_address = 0
    variable_address = 0
    parsing_results: list[ParsingResult] = []
    instructions = []
    instruction_labels = {}
    variable_labels = {}

    # First pass: Process each line to identify labels and count instruction size
    for line in trim_source(source_lines):

        # Convert line into user definied data structure, easier to manipulate
        parsing_results.append(parse_line(line, instruction_address, variable_address))

        # Record any instruction label
        if parsing_results[-1].new_instruction_label:
            instruction_labels[parsing_results[-1].new_instruction_label] = (
                instruction_address
            )
        # Record any variable label
        if parsing_results[-1].new_variable_label:
            variable_labels[parsing_results[-1].new_variable_label] = variable_address
        
        # Update instruction and variable addresses for next iteration
        instruction_address, variable_address = (
            parsing_results[-1].next_address,
            parsing_results[-1].next_variable_address,
        )
    # End of first pass

    # Check that program includes END instruction
    end = False
    for parsing_result in reversed(parsing_results):
        if parsing_result.mnemonic is not None:
            if parsing_result.mnemonic == "END":
                end = True
            break
    if not end:
        raise AssemblingError("Program must include END instruction.")

    # Computes variable addresses to place them after instructions in RAM-
    for var_label, addr in variable_labels.items():
        variable_labels[var_label] = instruction_address + addr

    # Second pass: create instructions with resolved labels
    # Variables are emitted after the end instructions in order to avoid
    # being read as instruction code.
    for parsing_result in [
        parsing_result
        for parsing_result in parsing_results
        if parsing_result.new_variable_label is None # only instructions
    ]:
        instructions += create_instruction_from_parsing_result(
            parsing_result, instruction_labels, variable_labels
        )
    for parsing_result in [
        parsing_result
        for parsing_result in parsing_results
        if parsing_result.new_variable_label is not None # only variables
    ]:
        instructions += create_instruction_from_parsing_result(
            parsing_result, instruction_labels, variable_labels
        )

    return instructions


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
