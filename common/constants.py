from enum import StrEnum

class AddressingMode(StrEnum):
    IMMEDIATE = "immediate"
    DIRECT = "direct"
    INDIRECT = "indirect"
    REGISTER = "register"
    INDEXED = "indexed"

class ComponentNames(StrEnum):
    MAR = "MAR"  # Memory Address Register
    MDR = "MDR"  # Memory Data Register
    PC = "PC"    # Program Counter
    CIR = "CIR"  # Current Instruction Register
    ACC = "ACC"  # Accumulator
    IX = "IX"    # Index Register
    CU_CONTROL = "CU_CONTROL"    # Control Unit for control purposes
    CU_OPERAND = "CU_OPERAND"  # Control Unit Operand
    IN = "IN"    # Stdin
    OUT = "OUT"  # Stdout
    ALU = "ALU"  # Arithmetic Logic Unit
    RAM_ADDRESS = "RAM_ADDRESS"
    RAM_DATA = "RAM_DATA"

class DisplayModes(StrEnum):
    HEX = "hex"
    DECIMAL = "decimal"
    BINARY = "binary"

class ControlSignals(StrEnum):
    READ = "r"
    WRITE = "w"
    
WORD_SIZE = 16  # in bits