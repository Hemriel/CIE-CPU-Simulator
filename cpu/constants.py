"""Shared text and numeric constants used throughout the CPU simulator.

Keeping the stringy names for components, control signals, and display modes in
one place makes it much less likely a typo sneaks into two modules that are
supposed to agree on the same text. When every reference imports from here,
the code stays consistent and easier to follow.
"""

from enum import StrEnum, IntEnum
from itertools import cycle

class MissingComponentError(Exception):
    """Raised when a CPU component is missing required sub-components."""
    ...


class AddressingMode(StrEnum):
    """Defines every addressing mode that the CIE spec calls out."""

    IMMEDIATE = "immediate"
    DIRECT = "direct"
    INDIRECT = "indirect"
    REGISTER = "register"
    INDEXED = "indexed"


class ComponentName(StrEnum):
    """Labels that every component registers itself under for display queries."""

    MAR = "MAR"  # Memory Address Register
    MDR = "MDR"  # Memory Data Register
    PC = "PC"  # Program Counter
    CIR = "CIR"  # Current Instruction Register
    ACC = "ACC"  # Accumulator
    IX = "IX"  # Index Register
    CU = "CU"  # Control Unit
    OPERAND = "OPERAND"  # Register pointed to by the CU operand of the instruction
    IN = "IN"  # Stdin
    OUT = "OUT"  # Stdout
    ALU = "ALU"  # Arithmetic Logic Unit
    CMP_Flag = "CMP_Flag"  # Comparison Flag
    RAM_ADDRESS = "RAM_ADDRESS"
    RAM_DATA = "RAM_DATA"
    INNER_DATA_BUS = "INNER_DATA_BUS"
    OUTER_DATA_BUS = "OUTER_DATA_BUS"
    ADDRESS_BUS = "ADDRESS_BUS"

class RegisterIndex(IntEnum):
    """Numeric indices for general-purpose registers. Used to encode/decode register operands in MOV, INC, DEC."""

    ACC = 0
    IX = 1
    PC = 2
    MAR = 3
    MDR = 4
    CIR = 5


class DisplayMode(StrEnum):
    """Choices for how registers and memory are rendered on screen."""

    HEX = "hex"
    DECIMAL = "decimal"
    BINARY = "binary"


class ControlSignal(StrEnum):
    """Short strings used to describe control signals inside the ALU and registers."""

    READ = "r"
    WRITE = "w"
    ADD = "add"
    SUB = "sub"
    CMP = "cmp"
    INC = "inc"
    DEC = "dec"
    AND = "and"
    OR = "or"
    XOR = "xor"
    LSL = "lsl"  # Logical Shift Left
    LSR = "lsr"  # Logical Shift Right


class RTNTypes(StrEnum):
    """Labels for different kinds of RTN steps."""

    SIMPLE_TRANSFER = "simple_transfer"
    ALU_OPERATION = "alu_operation"
    REG_OPERATION = "reg_operation"
    MEMORY_ACCESS = "memory_access"
    
class CyclePhases(StrEnum):
    """Labels for different phases within a CPU cycle."""

    FETCH = "fetch"
    DECODE = "decode"
    EXECUTE = "execute"

CYCLE_PHASES = cycle([CyclePhases.FETCH, CyclePhases.DECODE, CyclePhases.EXECUTE])
WORD_SIZE = 16  # in bits
"""bit width for general-purpose registers and the ALU operations."""
