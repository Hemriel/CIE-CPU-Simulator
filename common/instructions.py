"""Instruction metadata and execution contracts driven by CIE 9618 terminology."""

from dataclasses import dataclass
from constants import AddressingMode

""" Helper type definitions for instruction execution context and metadata. """

@dataclass
class RTNStep:
    """A declarative register-transfer step used by the UI to explain instruction timing."""
    source: str
    destination: str
    alu_op: str | None = None
    note: str | None = None

direct_addressing_RTNSteps = [
    RTNStep(source="operand", destination="MAR"),
    RTNStep(source="MAR", destination="RAM_address"),
    RTNStep(source="RAM_data", destination="MDR"),
]

indirect_addressing_RTNSteps = direct_addressing_RTNSteps + [
    RTNStep(source="MDR", destination="MAR"),
    RTNStep(source="MAR", destination="RAM_address"),
    RTNStep(source="RAM_data", destination="MDR"),
]

indexed_addressing_RTNSteps = [
    RTNStep(source="operand,X", destination="ALU", alu_op="ADD"),
    RTNStep(source="ALU", destination="MAR"),
    RTNStep(source="MAR", destination="RAM_address"),
    RTNStep(source="RAM_data", destination="MDR"),
]

@dataclass
class InstructionDefinition:
    """Metadata that describes how an instruction behaves in terms of opcode, addressing, and RTN."""

    mnemonic: str
    opcode: int
    addressing_mode: AddressingMode | None
    description: str
    rtn_sequence: list[RTNStep]

instruction_set: dict[int, InstructionDefinition] = {}
"""A global registry of instruction definitions keyed by opcode."""

LDM = InstructionDefinition(
    mnemonic="LDM",
    opcode=0,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Load immediate value into accumulator",
    rtn_sequence=[
        RTNStep(source="operand", destination="ACC"),
    ]
)

LDD = InstructionDefinition(
    mnemonic="LDD",
    opcode=1,
    addressing_mode=AddressingMode.DIRECT,
    description="Load value from memory into accumulator",
    rtn_sequence= direct_addressing_RTNSteps + [
        RTNStep(source="MDR", destination="ACC"),
    ]
)

LDI = InstructionDefinition(
    mnemonic="LDI",
    opcode=2,
    addressing_mode=AddressingMode.INDIRECT,
    description="Load value from memory address pointed to by operand into accumulator",
    rtn_sequence=indirect_addressing_RTNSteps + [
        RTNStep(source="MDR", destination="ACC"),
    ]
)

LDX = InstructionDefinition(
    mnemonic="LDX",
    opcode=3,
    addressing_mode=AddressingMode.INDEXED,
    description="Load value from memory address computed by adding index register to operand into accumulator",
    rtn_sequence= indexed_addressing_RTNSteps + [
        RTNStep(source="MDR", destination="ACC"),
    ]
)

LDR = InstructionDefinition(
    mnemonic="LDR",
    opcode=4,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Load immediate value into index register",
    rtn_sequence=[
        RTNStep(source="operand", destination="X"),
    ]
)

MOV = InstructionDefinition(
    mnemonic="MOV",
    opcode=5,
    addressing_mode=AddressingMode.REGISTER,
    description="Move value from ACC to given register",
    rtn_sequence=[
        RTNStep(source="ACC", destination="operand"),
    ]
)

STO = InstructionDefinition(
    mnemonic="STO",
    opcode=6,
    addressing_mode=AddressingMode.DIRECT,
    description="Store value from accumulator into memory",
    rtn_sequence=[
        RTNStep(source="operand", destination="MAR"),
        RTNStep(source="ACC", destination="MDR"),
        RTNStep(source="MDR", destination="RAM_data"),
    ]
)

ADD1 = InstructionDefinition(
    mnemonic="ADD",
    opcode=7,
    addressing_mode=AddressingMode.DIRECT,
    description="Add value from memory to accumulator",
    rtn_sequence= direct_addressing_RTNSteps + [
        RTNStep(source="ACC,MDR", destination="ALU", alu_op="ADD"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

ADD2 = InstructionDefinition(
    mnemonic="ADD",
    opcode=8,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Add immediate value to accumulator",
    rtn_sequence=[
        RTNStep(source="ACC,operand", destination="ALU", alu_op="ADD"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

SUB1 = InstructionDefinition(
    mnemonic="SUB",
    opcode=9,
    addressing_mode=AddressingMode.DIRECT,
    description="Subtract value from memory from accumulator",
    rtn_sequence= direct_addressing_RTNSteps + [
        RTNStep(source="ACC - MDR", destination="ALU", alu_op="SUB"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

SUB2 = InstructionDefinition(
    mnemonic="SUB",
    opcode=10,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Subtract immediate value from accumulator",
    rtn_sequence=[
        RTNStep(source="ACC,operand", destination="ALU", alu_op="SUB"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

INC = InstructionDefinition(
    mnemonic="INC",
    opcode=11,
    addressing_mode=AddressingMode.REGISTER,
    description="Increment accumulator by 1",
    rtn_sequence=[
        RTNStep(source="CU", destination="operand", note="Control Unit provides constant 1"),
    ]
)

DEC = InstructionDefinition(
    mnemonic="DEC",
    opcode=12,
    addressing_mode=AddressingMode.REGISTER,
    description="Decrement accumulator by 1",
    rtn_sequence=[
        RTNStep(source="CU", destination="operand", note="Control Unit provides constant 1"),
    ]
)

JMP = InstructionDefinition(
    mnemonic="JMP",
    opcode=13,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Jump to address in operand",
    rtn_sequence=[
        RTNStep(source="operand", destination="PC"),
    ]
)

CMP1 = InstructionDefinition(
    mnemonic="CMP",
    opcode=14,
    addressing_mode=AddressingMode.DIRECT,
    description="Compare value from memory with accumulator",
    rtn_sequence= direct_addressing_RTNSteps + [
        RTNStep(source="ACC,MDR", destination="ALU", alu_op="CMP"),
    ]
)

CMP2 = InstructionDefinition(
    mnemonic="CMP",
    opcode=15,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Compare immediate value with accumulator",
    rtn_sequence=[
        RTNStep(source="ACC,operand", destination="ALU", alu_op="CMP"),
    ]
)

CMI = InstructionDefinition(
    mnemonic="CMI",
    opcode=16,
    addressing_mode=AddressingMode.INDIRECT,
    description="Compare ACC to the value at the memory address pointed to by operand",
    rtn_sequence= indirect_addressing_RTNSteps + [
        RTNStep(source="ACC,MDR", destination="ALU", alu_op="CMP"),
    ]
)

JPE = InstructionDefinition(
    mnemonic="JPE",
    opcode=17,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Jump to address in operand if E flag is set",
    rtn_sequence=[
        RTNStep(source="operand", destination="PC", note="if E flag is set"),
    ]
)

JPN = InstructionDefinition(
    mnemonic="JPN",
    opcode=18,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Jump to address in operand if E flag is cleared",
    rtn_sequence=[
        RTNStep(source="operand", destination="PC", note="if E flag is cleared"),
    ]
)

IN = InstructionDefinition(
    mnemonic="IN",
    opcode=19,
    description="Input value from input queue into accumulator",
    addressing_mode=None,
    rtn_sequence=[
        RTNStep(source="IN", destination="ACC"),
    ]
)

OUT = InstructionDefinition(
    mnemonic="OUT",
    opcode=20,
    description="Output value from accumulator to output queue",
    addressing_mode=None,
    rtn_sequence=[
        RTNStep(source="ACC", destination="OUT"),
    ]
)

END = InstructionDefinition(
    mnemonic="END",
    opcode=21,
    description="Halt program execution",
    addressing_mode=None,
    rtn_sequence=[]
)

AND1 = InstructionDefinition(
    mnemonic="AND",
    opcode=22,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Bitwise AND immediate value with accumulator",
    rtn_sequence=[
        RTNStep(source="ACC,operand", destination="ALU", alu_op="AND"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

AND2 = InstructionDefinition(
    mnemonic="AND",
    opcode=23,
    addressing_mode=AddressingMode.DIRECT,
    description="Bitwise AND value from memory with accumulator",
    rtn_sequence= direct_addressing_RTNSteps + [
        RTNStep(source="ACC,MDR", destination="ALU", alu_op="AND"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

XOR1 = InstructionDefinition(
    mnemonic="XOR",
    opcode=24,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Bitwise XOR immediate value with accumulator",
    rtn_sequence=[
        RTNStep(source="ACC,operand", destination="ALU", alu_op="XOR"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

XOR2 = InstructionDefinition(
    mnemonic="XOR",
    opcode=25,
    addressing_mode=AddressingMode.DIRECT,
    description="Bitwise XOR value from memory with accumulator",
    rtn_sequence= direct_addressing_RTNSteps + [
        RTNStep(source="ACC,MDR", destination="ALU", alu_op="XOR"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

OR1 = InstructionDefinition(
    mnemonic="OR",
    opcode=26,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Bitwise OR immediate value with accumulator",
    rtn_sequence=[
        RTNStep(source="ACC,operand", destination="ALU", alu_op="OR"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

OR2 = InstructionDefinition(
    mnemonic="OR",
    opcode=27,
    addressing_mode=AddressingMode.DIRECT,
    description="Bitwise OR value from memory with accumulator",
    rtn_sequence= direct_addressing_RTNSteps + [
        RTNStep(source="ACC,MDR", destination="ALU", alu_op="OR"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

LSL = InstructionDefinition(
    mnemonic="LSL",
    opcode=28,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Logical shift left accumulator by immediate value",
    rtn_sequence=[
        RTNStep(source="ACC,operand", destination="ALU", alu_op="LSL"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

LSR = InstructionDefinition(
    mnemonic="LSR",
    opcode=29,
    addressing_mode=AddressingMode.IMMEDIATE,
    description="Logical shift right accumulator by immediate value",
    rtn_sequence=[
        RTNStep(source="ACC,operand", destination="ALU", alu_op="LSR"),
        RTNStep(source="ALU", destination="ACC"),
    ]
)

instruction_set = {
    LDM.opcode: LDM,
    LDD.opcode: LDD,
    LDI.opcode: LDI,
    LDX.opcode: LDX,
    LDR.opcode: LDR,
    MOV.opcode: MOV,
    STO.opcode: STO,
    ADD1.opcode: ADD1,
    ADD2.opcode: ADD2,
    SUB1.opcode: SUB1,
    SUB2.opcode: SUB2,
    INC.opcode: INC,
    DEC.opcode: DEC,
    JMP.opcode: JMP,
    CMP1.opcode: CMP1,
    CMP2.opcode: CMP2,
    CMI.opcode: CMI,
    JPE.opcode: JPE,
    JPN.opcode: JPN,
    IN.opcode: IN,
    OUT.opcode: OUT,
    END.opcode: END,
    AND1.opcode: AND1,
    AND2.opcode: AND2,
    XOR1.opcode: XOR1,
    XOR2.opcode: XOR2,
    OR1.opcode: OR1,
    OR2.opcode: OR2,
    LSL.opcode: LSL,
    LSR.opcode: LSR,
}