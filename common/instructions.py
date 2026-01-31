"""Instruction metadata and execution contracts driven by CIE 9618 terminology.

Responsibility:
- Define instruction metadata (opcode, addressing mode, description) in a single
    registry so the Control Unit and UI can agree on instruction behavior.
- Provide Register Transfer Notation (RTN) step sequences that describe *how* each
    instruction executes during the fetch-decode-execute cycle.

Illustrates
- CIE 9618: 4.1 Central Processing Unit Architecture:
    - Show understanding of the purpose and roles of registers.
    - Show understanding of the purpose and roles of the ALU, CU.
    - Show understanding of how data are transferred between various components using buses.
    - Describe stages of the fetch-decode-execute cycle.
- CIE 9618: 4.2 Assembly Language:
    - Show understanding of and be able to use different modes of addressing.
    - Show understanding that a set of instructions are grouped.

Design notes:
1. RTN sequences for common addressing modes are defined once (direct, indirect,
   indexed) to avoid copy-and-pasting the same steps across multiple instructions.
2. Instruction definitions for the same mnemonic but different addressing modes (for
   example `ADD` has both direct and immediate versions) keep the mnemonic and
   opcode separate so the control unit knows exactly which behavior is required.
3. Every instruction exports its RTN steps so the UI can show the register transfers
   that happen at each clock cycle, and the CU can execute them.

Entry point:
- Import the registry with: from common.instructions import instruction_set
- Use :func:`get_instruction_by_mnemonic` to resolve overloaded mnemonics.

Includes:
- RTN step data classes: :class:`RTNStep`, :class:`SimpleTransferStep`,
  :class:`ConditionalTransferStep`, :class:`MemoryAccessStep`,
  :class:`ALUOperationStep`, :class:`RegOperationStep`
- Addressing-mode RTN templates: :data:`direct_addressing_RTNSteps`,
  :data:`indirect_addressing_RTNSteps`, :data:`indexed_addressing_RTNSteps`
- Instruction metadata model: :class:`InstructionDefinition`
- Instruction registry and helpers: :data:`instruction_set`,
  :func:`get_instruction_by_mnemonic`
- Fetch/decode RTN sequences: :data:`FETCH_RTNSteps`, :data:`DECODE_RTNSteps`,
  :data:`FETCH_LONG_OPERAND_RTNSteps`
"""

from dataclasses import dataclass
from common.constants import AddressingMode, ControlSignal, ComponentName


### Educational notes on Python features used in this module ###
#
# Data classes (appear throughout this file):
# Data classes are NOT in the curriculum.
# Here is a detailed explanation: https://docs.python.org/3/library/dataclasses.html
# In a few words, they are a concise way to define classes that mainly store
# data attributes. The __init__, __repr__, __eq__, and other methods are
# automatically generated based on the class attributes.
#
# __repr__ methods (appear in RTN step classes):
# These methods provide a readable string for the UI and debugging output.
# The UI uses these strings to display the RTN steps to students.


@dataclass
class RTNStep:
    """A declarative register-transfer step used by the UI and simulator.

    RTN steps describe a *single* register transfer (or micro-operation) in the
    fetch-decode-execute cycle. They are data-only objects so the Control Unit
    can interpret them and the UI can visualize them.

    This parent class is not instantiated directly; instead, use one of the
    subclasses that describe specific kinds of RTN steps. Having a common
    parent class allows the instruction definitions to store slightly
    different step types in a single list, while still ensuring type safety.
    """
    pass


@dataclass
class SimpleTransferStep(RTNStep):
    """Move a value from one component to another (e.g., `MAR <- PC`)."""

    source: ComponentName
    destination: ComponentName

    def __repr__(self) -> str:
        return f"{self.destination} <- {self.source}"


@dataclass
class ConditionalTransferStep(SimpleTransferStep):
    """Transfer that only occurs if the comparison flag matches a condition.

    Used for conditional jump instructions (e.g., JPE/JPN) that rely on the
    comparison flag set by CMP/CMI. Only the condition parameter is added to the
    SimpleTransferStep base class.
    
    Note that the source and destination attributes are inherited from
    SimpleTransferStep.
    """

    condition: bool = True

    def __repr__(self) -> str:
        cond_str = "if E" if self.condition else "if not E"
        return f"{self.destination} <- {self.source} {cond_str}"


@dataclass
class MemoryAccessStep(RTNStep):
    """Describe a memory access step over the MAR/MDR and external RAM buses."""

    is_address: bool = True                         # True = access address, False = access data
    control: ControlSignal = ControlSignal.READ     # READ or WRITE operation

    def __repr__(self) -> str:
        if self.is_address:
            return f"RAM address <- MAR"
        elif self.control == ControlSignal.READ:
            return f"MDR <- RAM data"
        else:
            return f"RAM data <- MDR"


@dataclass
class ALUOperationStep(RTNStep):
    """Describe an ALU operation using ACC and a source component."""

    source: ComponentName   # Second operand for the ALU operation
    control: ControlSignal  # ALU operation to perform (e.g., ADD, SUB, AND)

    def __repr__(self) -> str:
        return f"ACC {self.control} {self.source}"


@dataclass
class RegOperationStep(RTNStep):
    """Register operation step, such as INC or DEC, with optional source."""

    destination: ComponentName              # Register to operate on
    control: ControlSignal                  # Operation to perform (INC, DEC)
    source: ComponentName | None = None     # Optional source register (mostly intended for indexed addressing)

    def __repr__(self) -> str:
        if self.source:
            return f"{self.destination} {self.control} {self.source}"
        else:
            return f"{self.destination} {self.control}"

# Shared RTN templates for common addressing modes.
# For immediate addressing, the operand already resides in MDR.
# For direct and indirect addressing, we need to fetch the operand from memory.
#   Each adds a memory access sequence on top of the previous mode.
# For indexed addressing, we add the index register to the effective address.
# TODO: Confirm whether the indirect/indexed templates should include a MAR <- operand
#       transfer or assume MDR already holds the effective address.
direct_addressing_RTNSteps = [
    SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.MAR),
    MemoryAccessStep(),
    MemoryAccessStep(is_address=False),
]

indirect_addressing_RTNSteps = direct_addressing_RTNSteps + [
    SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.MAR),
    MemoryAccessStep(),
    MemoryAccessStep(is_address=False),
]

indexed_addressing_RTNSteps = [
    SimpleTransferStep(
        source=ComponentName.MDR, destination=ComponentName.MAR),
    # Increment MAR by IX to get effective address
    RegOperationStep(source=ComponentName.IX, destination=ComponentName.MAR, control=ControlSignal.INC),
    MemoryAccessStep(),
    MemoryAccessStep(is_address=False),
]


@dataclass
class InstructionDefinition:
    """Metadata that describes how an instruction behaves.

    Each definition combines an opcode, addressing mode, and RTN sequence so the
    Control Unit can execute the instruction and the UI can display each step.
    """

    mnemonic: str
    """Mnemonic name of the instruction in assembly, e.g., 'LDM'."""
    opcode: int
    """Numeric opcode used to identify the instruction in machine code."""
    addressing_mode: AddressingMode | None
    """Addressing mode used by the instruction, or None for I/O/END instructions."""
    description: str
    """Short human-readable description of the instruction's purpose."""
    rtn_sequence: list[RTNStep]
    """Ordered list of RTNSteps that define the register transfers for this instruction."""
    long_operand: bool = True
    """Whether the instruction uses a full-length operand (True) or is short (False).

    Short instructions assume the operand value is the second half of the instruction word.
    Long instructions assume the operand value has been fetched into MDR.
    """


instruction_set: dict[int, InstructionDefinition] = {}
"""Global registry of instruction definitions keyed by opcode."""

def get_instruction_by_mnemonic(mnemonic: str) -> list[InstructionDefinition]:
    """Retrieve all instruction definitions matching the given mnemonic.

    Some mnemonics map to multiple opcodes (e.g., immediate vs direct versions).
    This function returns all matching definitions so callers can disambiguate
    based on the operand.
    """
    return [
        instr_def
        for instr_def in instruction_set.values()
        if instr_def.mnemonic == mnemonic
    ]


### Next is the full instruction set definitions ###

## Data movement instructions ##

LDM = InstructionDefinition(
    mnemonic        = "LDM",
    opcode          = 0,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Load immediate value into accumulator",
    rtn_sequence    = [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.ACC),
    ],
)

LDD = InstructionDefinition(
    mnemonic        = "LDD",
    opcode          = 1,
    addressing_mode = AddressingMode.DIRECT,
    description     = "Load value from memory into accumulator",
    rtn_sequence    = direct_addressing_RTNSteps
    + [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.ACC),
    ],
)

LDI = InstructionDefinition(
    mnemonic        = "LDI",
    opcode          = 2,
    addressing_mode = AddressingMode.INDIRECT,
    description     = "Load value from memory address pointed to by operand into accumulator",
    rtn_sequence    = indirect_addressing_RTNSteps
    + [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.ACC),
    ],
)

LDX = InstructionDefinition(
    mnemonic        = "LDX",
    opcode          = 3,
    addressing_mode = AddressingMode.INDEXED,
    description     = "Load value from memory address computed by adding index register to operand into accumulator",
    rtn_sequence    = indexed_addressing_RTNSteps
    + [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.ACC),
    ],
)

LDR = InstructionDefinition(
    mnemonic        = "LDR",
    opcode          = 4,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Load immediate value into index register",
    rtn_sequence    = [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.IX),
    ],
)

MOV = InstructionDefinition(
    mnemonic        = "MOV",
    opcode          = 5,
    addressing_mode = AddressingMode.REGISTER,
    description     = "Move value from ACC to given register",
    long_operand    = False,
    rtn_sequence    = [
        SimpleTransferStep(source=ComponentName.ACC, destination=ComponentName.OPERAND),
    ],
)

STO = InstructionDefinition(
    mnemonic        = "STO",
    opcode          = 6,
    addressing_mode = AddressingMode.DIRECT,
    description     = "Store value from accumulator into memory",
    rtn_sequence    = [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.MAR),
        SimpleTransferStep(source=ComponentName.ACC, destination=ComponentName.MDR),
        MemoryAccessStep(),
        MemoryAccessStep(is_address=False, control=ControlSignal.WRITE),
    ],
)

STI = InstructionDefinition(
    mnemonic        = "STI",
    opcode          = 30,
    addressing_mode = AddressingMode.INDIRECT,
    description     = "Store ACC into memory address retrieved through operand pointer",
    rtn_sequence    = [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.MAR),
        MemoryAccessStep(),
        MemoryAccessStep(is_address=False),
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.MAR),
        SimpleTransferStep(source=ComponentName.ACC, destination=ComponentName.MDR),
        MemoryAccessStep(),
        MemoryAccessStep(is_address=False, control=ControlSignal.WRITE),
    ],
)

STX = InstructionDefinition(
    mnemonic        = "STX",
    opcode          = 31,
    addressing_mode = AddressingMode.INDEXED,
    description     = "Store ACC into memory at address computed by IX plus operand",
    rtn_sequence    = [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.MAR),
        RegOperationStep(
            source=ComponentName.IX, destination=ComponentName.MAR, control=ControlSignal.INC
        ),
        SimpleTransferStep(source=ComponentName.ACC, destination=ComponentName.MDR),
        MemoryAccessStep(),
        MemoryAccessStep(is_address=False, control=ControlSignal.WRITE),
    ],
)

## Arithmetic instructions ##

ADD1 = InstructionDefinition(
    mnemonic        = "ADD",
    opcode          = 7,
    addressing_mode = AddressingMode.DIRECT,
    description     = "Add value from memory to accumulator",
    rtn_sequence    = direct_addressing_RTNSteps
    + [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.ADD,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Direct addressing version of the ADD instruction."""

ADD2 = InstructionDefinition(
    mnemonic        = "ADD",
    opcode          = 8,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Add immediate value to accumulator",
    rtn_sequence    = [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.ADD,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Immediate addressing version of the ADD instruction."""

# SUB direct vs immediate: SUB1 reaches into memory and SUB2 uses operand directly.
SUB1 = InstructionDefinition(
    mnemonic        = "SUB",
    opcode          = 9,
    addressing_mode = AddressingMode.DIRECT,
    description     = "Subtract value from memory from accumulator",
    rtn_sequence    = direct_addressing_RTNSteps
    + [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.SUB,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Direct addressing version of the SUB instruction."""

SUB2 = InstructionDefinition(
    mnemonic        = "SUB",
    opcode          = 10,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Subtract immediate value from accumulator",
    rtn_sequence    = [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.SUB,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Immediate addressing version of the SUB instruction."""

INC = InstructionDefinition(
    mnemonic        = "INC",
    opcode          = 11,
    addressing_mode = AddressingMode.REGISTER,
    description     = "Increment register (ACC, IX, CU) by 1",
    long_operand    = False,
    rtn_sequence    = [
        RegOperationStep(
            destination=ComponentName.OPERAND,
            control=ControlSignal.INC,
        )
    ],
)

DEC = InstructionDefinition(
    mnemonic        = "DEC",
    opcode          = 12,
    addressing_mode = AddressingMode.REGISTER,
    description     = "Decrement register (ACC, IX, CU) by 1",
    long_operand    = False,
    rtn_sequence    = [
        RegOperationStep(
            destination=ComponentName.OPERAND,
            control=ControlSignal.DEC,
        ),
    ],
)

## Control flow instructions ##

JMP = InstructionDefinition(
    mnemonic        = "JMP",
    opcode          = 13,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Jump to address in operand",
    rtn_sequence    = [
        SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.PC),
    ],
)

# CMP direct vs immediate versions so the mnemonics stay identical while addressing differs.
CMP1 = InstructionDefinition(
    mnemonic        = "CMP",
    opcode          = 14,
    addressing_mode = AddressingMode.DIRECT,
    description     = "Compare value from memory with accumulator",
    rtn_sequence=direct_addressing_RTNSteps
    + [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.CMP,
        ),
    ],
)
"""Direct addressing version of the CMP instruction."""

CMP2 = InstructionDefinition(
    mnemonic        = "CMP",
    opcode          = 15,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Compare immediate value with accumulator",
    rtn_sequence    = [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.CMP,
        ),
    ],
)
"""Immediate addressing version of the CMP instruction."""

CMI = InstructionDefinition(
    mnemonic        = "CMI",
    opcode          = 16,
    addressing_mode = AddressingMode.INDIRECT,
    description     = "Compare ACC to the value at the memory address pointed to by operand",
    rtn_sequence    = indirect_addressing_RTNSteps
    + [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.CMP,
        ),
    ],
)

JPE = InstructionDefinition(
    mnemonic        = "JPE",
    opcode          = 17,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Jump to address in operand if E flag is set",
    rtn_sequence    = [
        ConditionalTransferStep(
            source=ComponentName.MDR,
            destination=ComponentName.PC,
            condition=True,
        ),
    ],
)

JPN = InstructionDefinition(
    mnemonic        = "JPN",
    opcode          = 18,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Jump to address in operand if E flag is cleared",
    rtn_sequence    = [
        ConditionalTransferStep(
            source=ComponentName.MDR,
            destination=ComponentName.PC,
            condition=False,
        ),
    ],
)

## I/O instructions ##

IN = InstructionDefinition(
    mnemonic        = "IN",
    opcode          = 19,
    description     = "Input value from input queue into accumulator",
    addressing_mode = AddressingMode.NONE,
    long_operand    = False,
    rtn_sequence    = [
        SimpleTransferStep(source=ComponentName.IN, destination=ComponentName.ACC),
    ],
)

OUT = InstructionDefinition(
    mnemonic        = "OUT",
    opcode          = 20,
    description     = "Output value from accumulator to output queue",
    addressing_mode = AddressingMode.NONE,
    long_operand    = False,
    rtn_sequence=[
        SimpleTransferStep(source=ComponentName.ACC, destination=ComponentName.OUT),
    ],
)

## System instructions ##

END = InstructionDefinition(
    mnemonic        = "END",
    opcode          = 21,
    description     = "Halt program execution",
    addressing_mode = AddressingMode.NONE,
    long_operand    = False,
    rtn_sequence    = [],
)

## Logical instructions ##

# AND has immediate and direct versions differentiated by opcode.
AND1 = InstructionDefinition(
    mnemonic        = "AND",
    opcode          = 22,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Bitwise AND immediate value with accumulator",
    rtn_sequence    = [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.AND,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Immediate addressing version of the AND instruction."""

AND2 = InstructionDefinition(
    mnemonic        = "AND",
    opcode          = 23,
    addressing_mode = AddressingMode.DIRECT,
    description     = "Bitwise AND value from memory with accumulator",
    rtn_sequence    = direct_addressing_RTNSteps
    + [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.AND,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Direct addressing version of the AND instruction."""

# Same mnemonic XOR has an immediate and a direct variant.
XOR1 = InstructionDefinition(
    mnemonic        = "XOR",
    opcode          = 24,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Bitwise XOR immediate value with accumulator",
    rtn_sequence    = [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.XOR,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Immediate addressing version of the XOR instruction."""

XOR2 = InstructionDefinition(
    mnemonic        = "XOR",
    opcode          = 25,
    addressing_mode = AddressingMode.DIRECT,
    description     = "Bitwise XOR value from memory with accumulator",
    rtn_sequence    = direct_addressing_RTNSteps
    + [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.XOR,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Direct addressing version of the XOR instruction."""

# OR also has both immediate and direct forms to keep the mnemonic shared.
OR1 = InstructionDefinition(
    mnemonic        = "OR",
    opcode          = 26,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Bitwise OR immediate value with accumulator",
    rtn_sequence    = [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.OR,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Immediate addressing version of the OR instruction."""

OR2 = InstructionDefinition(
    mnemonic        = "OR",
    opcode          = 27,
    addressing_mode = AddressingMode.DIRECT,
    description     = "Bitwise OR value from memory with accumulator",
    rtn_sequence    = direct_addressing_RTNSteps
    + [
        ALUOperationStep(
            source=ComponentName.MDR,
            control=ControlSignal.OR,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)
"""Direct addressing version of the OR instruction."""

LSL = InstructionDefinition(
    mnemonic        = "LSL",
    opcode          = 28,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Logical shift left accumulator by immediate value",
    long_operand    = False,
    rtn_sequence    = [
        ALUOperationStep(
            source=ComponentName.CU,
            control=ControlSignal.LSL,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)

LSR = InstructionDefinition(
    mnemonic        = "LSR",
    opcode          = 29,
    addressing_mode = AddressingMode.IMMEDIATE,
    description     = "Logical shift right accumulator by immediate value",
    long_operand    = False,
    rtn_sequence    = [
        ALUOperationStep(
            source=ComponentName.CU,
            control=ControlSignal.LSR,
        ),
        SimpleTransferStep(source=ComponentName.ALU, destination=ComponentName.ACC),
    ],
)

instruction_set = {
    LDM.opcode  : LDM,
    LDD.opcode  : LDD,
    LDI.opcode  : LDI,
    LDX.opcode  : LDX,
    LDR.opcode  : LDR,
    MOV.opcode  : MOV,
    STO.opcode  : STO,
    ADD1.opcode : ADD1,
    ADD2.opcode : ADD2,
    SUB1.opcode : SUB1,
    SUB2.opcode : SUB2,
    INC.opcode  : INC,
    DEC.opcode  : DEC,
    JMP.opcode  : JMP,
    CMP1.opcode : CMP1,
    CMP2.opcode : CMP2,
    CMI.opcode  : CMI,
    JPE.opcode  : JPE,
    JPN.opcode  : JPN,
    IN.opcode   : IN,
    OUT.opcode  : OUT,
    END.opcode  : END,
    AND1.opcode : AND1,
    AND2.opcode : AND2,
    XOR1.opcode : XOR1,
    XOR2.opcode : XOR2,
    OR1.opcode  : OR1,
    OR2.opcode  : OR2,
    LSL.opcode  : LSL,
    LSR.opcode  : LSR,
    STI.opcode  : STI,
    STX.opcode  : STX,
}

### Fetch and decode RTN sequences ###
# All CPU operations are expressed in RTN steps, including fetch and decode phases.
# These sequences are used by the Control Unit to perform instruction fetch
# and decode before executing the instruction-specific RTN steps.
# By the end of the decode phase, the CU has loaded the instruction into CIR
# and the operand into MDR (if the instruction uses a long operand).

FETCH_RTNSteps: list[RTNStep] = [
    SimpleTransferStep(source=ComponentName.PC, destination=ComponentName.MAR),
    MemoryAccessStep(),
    MemoryAccessStep(is_address=False),
    SimpleTransferStep(source=ComponentName.MDR, destination=ComponentName.CIR),
    RegOperationStep(destination=ComponentName.PC, control=ControlSignal.INC),
]

DECODE_RTNSteps: list[RTNStep] = [
    SimpleTransferStep(source=ComponentName.CIR, destination=ComponentName.CU),
]

FETCH_LONG_OPERAND_RTNSteps: list[RTNStep] = [
    SimpleTransferStep(source=ComponentName.CIR, destination=ComponentName.CU),
    SimpleTransferStep(source=ComponentName.PC, destination=ComponentName.MAR),
    MemoryAccessStep(),
    MemoryAccessStep(is_address=False),
    RegOperationStep(destination=ComponentName.PC, control=ControlSignal.INC),
]