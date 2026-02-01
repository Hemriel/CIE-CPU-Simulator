"""Shared text and numeric constants used throughout the CPU simulator.

Responsibility:
- Define component names, control signals, addressing modes, and other constants
  to ensure consistency across all modules and prevent typos.
- Act as the single source of truth for enum values and magic numbers used in
  CPU simulation, control logic, memory model, and UI display.

Illustrates:
- CIE 9618: 4.1 Central Processing Unit Architecture:
    - Show understanding of the purpose and roles of registers.
    - Show understanding of the purpose and roles of the ALU, CU.
    - Show understanding of how data are transferred between various components using buses.
    - Describe stages of the fetch-decode-execute cycle.
- CIE 9618: 4.2 Assembly Language:
    - Show understanding of and be able to use different modes of addressing.
    - Show understanding that a set of instructions are grouped.
- CIE 9618: 4.3 Bit Manipulation:
    - Show understanding of binary shifts (represented in ControlSignal enum).

Design note:
- Keeping all constant strings in one place makes it much less likely a typo
  sneaks into two modules that are supposed to agree on the same text.
- When every reference imports from here, the code stays consistent and easier
  to follow.

Entry point:
- This is a constants module; all classes and enums are public API.
- Import as needed: from common.constants import ComponentName, AddressingMode, etc.

Includes:
- Exception classes: :class:`MissingComponentError`, :class:`AssemblingError`, class:`AbnormalComponentUseError`
- Addressing mode enum: :class:`AddressingMode` (defines all CIE addressing modes)
- Component labels: :class:`ComponentName` (registers, buses, and control units)
- Register index mapping: :data:`RegisterIndex` (register name -> operand index)
- Control signal codes: :class:`ControlSignal` (ALU and register operations)
- RTN step types: :class:`RTNTypes` (fetch-decode-execute classification)
- Display modes: :class:`DisplayMode` (hex, decimal, binary)
- CPU timing: :class:`CyclePhase` and :data:`CYCLE_PHASES`
- Global constants: :data:`WORD_SIZE`
"""

from enum import StrEnum
from itertools import cycle

### Educational notes on Python operations used in this module ###
#
# The exeption classes below inherit from Exception directly.
# They don't need any special behavior, just a unique type. That way,
# other modules can raise and catch them specifically, without interfering
# with exceptions raised by Python itself.
#
# The enums inherit from StrEnum so that their values are strings. This allows
# easy comparison to string literals (e.g., if mode == AddressingMode.IMMEDIATE: ...).
# Using enums prevents typos and makes code more self-documenting.
# Enums, or non-composite datatypes (as for CIE Pseudocode guidelines), are
# used to define sets of related constant values.
#
# "cycle", imported from itertools, allows to infinitely loop over the fetch-decode-execute
# phases. This is a memory-efficient way to represent repeating sequences.

class MissingComponentError(Exception):
    """Raised when a CPU component is missing required sub-components."""
    pass


class AssemblingError(Exception):
    """Raised when an error occurs during assembly of source code."""
    pass

class AbnormalComponentUseError(Exception):
    """Raised when a CPU component is used in an unexpected or incorrect way."""
    pass

class AddressingMode(StrEnum):
    """Defines every addressing mode that the CIE spec calls out.
    
    Each mode determines how the operand is interpreted during instruction execution:
    
    - IMMEDIATE: Operand is a literal value (e.g., #5 in "ADD #5").
      No memory access required; value is directly available.
    - DIRECT: Operand is a memory address (e.g., "LDD 100" loads from address 100).
      Requires one memory access to fetch/store data.
    - INDIRECT: Operand is an address containing another address (e.g., "LDI 200").
      Requires two memory accesses: first to fetch the pointer, second to fetch data.
    - INDEXED: Operand plus the Index Register (IX) = effective address.
      Used for array indexing and iteration (e.g., "LDX 50" accesses memory[50 + IX]).
    - REGISTER: Operand specifies a CPU register (e.g., "MOV IX" for register transfer).
      No memory access; operates on registers directly.
    - NONE: Instruction has no operand (e.g., "END", "IN", "OUT").
      Operand field is unused.
    """

    IMMEDIATE = "immediate"
    DIRECT = "direct"
    INDIRECT = "indirect"
    REGISTER = "register"
    INDEXED = "indexed"
    NONE = "none"


class ComponentName(StrEnum):
    """Labels that every component registers itself under for display queries.
    
    These names form the canonical component identifiers used throughout the CPU
    simulator. Registers are defined in CIE 9618 §4.1; buses and other components
    are implementation-specific architectural choices to support the curriculum.
    """

    # CIE 9618 special-purpose registers
    MAR = "MAR"  # Memory Address Register
    MDR = "MDR"  # Memory Data Register
    PC  = "PC"   # Program Counter
    CIR = "CIR"  # Current Instruction Register
    ACC = "ACC"  # Accumulator
    IX  = "IX"   # Index Register
    
    # Control and execution units
    CU       = "CU"   # Control Unit
    ALU      = "ALU"  # Arithmetic Logic Unit
    CMP_FLAG = "CMP_FLAG"  # Comparison Flag (set by CMP/CMI instructions)
    
    # I/O and operand handling
    OPERAND = "OPERAND"  # Register pointed to by the CU operand of the instruction
    IN      = "IN"       # Stdin
    OUT     = "OUT"      # Stdout
    
    # Memory and bus connections
    RAM_ADDRESS     = "RAM_ADDRESS"
    RAM_DATA        = "RAM_DATA"
    INNER_DATA_BUS  = "INNER_DATA_BUS"
    ADDRESS_BUS     = "ADDRESS_BUS"

# Maps CIE register names to numeric bus indices for instruction operands.
# Used by the assembler and CPU to encode/decode register references in MOV, INC, DEC.
# Example: ComponentName.ACC maps to operand index 0.
RegisterIndex: dict[ComponentName, int] = {
    ComponentName.ACC: 0,
    ComponentName.IX : 1,
    ComponentName.PC : 2,
    ComponentName.MAR: 3,
    ComponentName.MDR: 4,
    ComponentName.CIR: 5,
}


class DisplayMode(StrEnum):
    """Choices for how registers and memory are rendered on screen.
    
    Students can toggle between radixes to understand how binary and hex
    representations relate to decimal values (CIE 9168 §1.1 Show 
    understanding of different numbering systems).
    """

    HEX = "hex"
    DECIMAL = "decimal"
    BINARY = "binary"


class ControlSignal(StrEnum):
    """Short strings used to describe control signals inside the ALU and registers.
    
    The control bus is not displayed directly in the UI, but we can
    observe its effects by looking at control signals displayed on each
    components panel during RTN steps. These codes correspond to each
    signal the CU can send to the ALU or registers to perform operations.
    """

    # Memory and register access
    READ  = "r"
    WRITE = "w"
    
    # CIE 9618 ALU operations
    ADD = "add"
    SUB = "sub"
    AND = "and"
    OR  = "or"
    XOR = "xor"
    CMP = "cmp"
    
    # Register increment/decrement
    INC = "inc"
    DEC = "dec"
    
    # Shift operations
    LSL = "lsl"  # Logical Shift Left
    LSR = "lsr"  # Logical Shift Right


class RTNTypes(StrEnum):
    """Labels for different kinds of RTN (Register Transfer Notation) steps.
    Here, we extend the meaning of register transfer notation to classify
    every micro-operation that occurs during the fetch-decode-execute cycle,
    including ALU operations and memory accesses.
    
    RTN explicitly models the fetch-decode-execute cycle as a sequence of
    register transfers. Each step type is executed by the Control Unit.
    """

    SIMPLE_TRANSFER = "simple_transfer" # Basic register-to-register or bus transfer
    ALU_OPERATION   = "alu_operation"   # ALU computation step (ADD, SUB, etc.)
    REG_OPERATION   = "reg_operation"   # Register operation (INC, DEC)
    MEMORY_ACCESS   = "memory_access"   # Memory read or write operation
    
class CyclePhase(StrEnum):
    """Labels for the three phases of the CPU fetch-decode-execute cycle.
    """

    FETCH = "fetch"
    DECODE = "decode"
    EXECUTE = "execute"

# Infinite cycle of fetch-decode-execute phases. Used to sequence CPU execution.
CYCLE_PHASES = cycle([CyclePhase.FETCH, CyclePhase.DECODE, CyclePhase.EXECUTE])

# This constant is used for word wrapping and range validation throughout the simulator.
# All CPU have a fixed word size defined by the architecture. 
WORD_SIZE = 16


if __name__ == "__main__":
    # Quick test to verify that all enums can be iterated and printed.
    print(CYCLE_PHASES.__next__())