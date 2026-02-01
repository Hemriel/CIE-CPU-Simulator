"""Arithmetic Logic Unit (ALU) that executes arithmetic and logic operations.

Responsibility:
- Execute arithmetic operations (ADD, SUB) and logic operations (AND, OR, XOR, CMP)
  as specified by control signals from the Control Unit.
- Maintain the comparison flag for conditional branch instructions.
- Provide visual state for the UI to display operands, operation mode, and results.

Design note:
- The ALU is a passive component: it does not initiate operations. The Control Unit
  sets operands and mode, then calls compute() to execute the operation.
- Results are stored internally until read by register transfers (typically ACC ← ALU).

Illustrates:
- CIE 9618: 4.1 Central Processing Unit (CPU) Architecture:
    - Show understanding of the purpose and role of the ALU.
    - Show understanding of the purpose and roles of registers.
- CIE 9618: 4.3 Bit Manipulation:
    - Show understanding of and perform binary shifts (and other bitwise operations).
- CIE 9618: 13.1 User-defined data types (depper than intended by curriculum, this could serve as a complex example):
    - Show understanding of why user-defined data types are necessary.
    - Chose and define an appropriate user defined data type for a given problem.

Entry point:
- The :class:`ALU` class is instantiated by the CPU and driven by the Control Unit.
- The :class:`FlagComponent` tracks comparison results for conditional branches.

Includes:
- :class:`FlagComponent`: Comparison flag component (E flag)
- :class:`ALU`: Main ALU implementation with operation execution
"""

from dataclasses import dataclass, field
from cpu.component import CPUComponent
from common.constants import ComponentName, ControlSignal, WORD_SIZE, AbnormalComponentUseError


### Educational notes on Python features used in this module ###
#
# Dataclasses with default_factory (field(default_factory=FlagComponent)):
# This pattern creates a fresh FlagComponent instance for each ALU instance.
# Without default_factory, all ALU instances would share the same flag object
# (mutable default argument problem in Python).
# More info: https://docs.python.org/3/library/dataclasses.html#mutable-default-values
#
# Bitwise operations (& | ^):
# Python bitwise operations are NOT part of the curriculum. However, bitwise operations
# are studied in Unit 4.3 Bit manipulation, when working on assembly language.
# Python's bitwise operators work on integers as if they were binary sequences (by converting them
# to binary under the hood).
# & performs AND, | performs OR, ^ performs XOR on each bit position.


@dataclass
class FlagComponent(CPUComponent):
    """Comparison flag component that stores the result of CMP/CMI instructions.
    
    The E (Equal/comparison) flag is set to True when ACC equals the compared value,
    and False otherwise. Conditional branch instructions (JPE, JPN) read this flag
    to decide whether to jump.
    """

    name: ComponentName = ComponentName.CMP_FLAG
    value : bool = False

    def read(self) -> bool:
        """Read the current flag value."""
        return self.value

    def write(self, value: bool) -> None:
        """Write a new flag value."""
        self.value = value
        self._update_display()

    def __repr__(self) -> str:
        return f"{'SET' if self.value else 'CLEAR'}"


@dataclass
class ALU(CPUComponent):
    """Model of the ALU following CIE 9618 RTN description of arithmetic and logic operations.
    
    The ALU performs operations specified by control signals from the Control Unit.
    It operates in three phases:
    1. set_mode() selects the operation (ADD, SUB, AND, OR, XOR, CMP)
    2. set_operands() provides ACC and the second operand
    3. compute() executes the operation and updates the result/flags
    
    Phases 1 and 2 can be called in any order before compute().

    Attributes:
        control: The ControlSignal currently armed for the pending operation.
        acc: First operand (typically the accumulator value).
        operand: Second operand (from memory, immediate, or register).
        result: Computed result available for register transfer (e.g., ACC ← ALU).
        flag_component: Comparison flag component updated by CMP operations.
    """

    name: ComponentName = ComponentName.ALU
    control: ControlSignal | None = None
    acc: int = 0
    operand: int = 0
    result: int = 0
    flag_component: FlagComponent = field(default_factory=FlagComponent) # See note above

    def read(self) -> int:
        """Read the most recent ALU result.
        
        Called during register transfers like ACC ← ALU after an operation completes.
        """
        return self.result

    def write(self, data: int) -> None:
        """ALU does not support direct writes.
        
        The ALU is a computational unit, not a storage register. Operands are provided
        via set_operands() and results are retrieved via read().
        
        Raises:
            AbnormalComponentUseError: Always raised; ALU is read-only from the bus perspective.
        """
        raise AbnormalComponentUseError("ALU does not support direct writes.")

    def set_mode(self, control: ControlSignal | None) -> None:
        """Select the ALU operation mode and refresh the UI so RTN can display it."""

        self.control = control
        self._update_display()

    def set_operands(self, acc: int, operand: int) -> None:
        """Provide operands from register transfers and redraw the panel."""

        self.acc = acc
        self.operand = operand
        self._update_display()

    def compute(self) -> None:
        """Execute the selected ControlSignal, store the result, and update flags.
        
        Performs the operation selected by the current control signal:
        - ADD, SUB: Arithmetic operations, result stored for later ACC transfer
        - AND, OR, XOR: Bitwise logic operations, result stored for later ACC transfer
        - CMP: Compare ACC with operand, set comparison flag (no result stored)
        
        The comparison flag (E) is updated only for CMP operations. Other operations
        do not modify flags (CIE 9618 simplification; real CPUs update multiple flags).
        """
        # Every ControlSignal maps to a deterministic arithmetic or logic function.
        if self.control == ControlSignal.ADD:
            self._set_result(self.acc + self.operand)
        elif self.control == ControlSignal.SUB:
            self._set_result(self.acc - self.operand)
        # next three are bitwise operations, see note above
        elif self.control == ControlSignal.AND:
            self._set_result(self.acc & self.operand)
        elif self.control == ControlSignal.OR:
            self._set_result(self.acc | self.operand)
        elif self.control == ControlSignal.XOR:
            self._set_result(self.acc ^ self.operand)
        elif self.control == ControlSignal.CMP:
            compare = self.acc == self.operand
            self.flag_component.write(compare)
        else:
            raise AbnormalComponentUseError(
                f"ALU compute() called with invalid or unset control signal: {self.control}"
            )

    def _set_result(self, result: int) -> None:
        """Store the computed result and refresh the UI display."""
        self.result = result % (1 << WORD_SIZE)  # Wrap to 16-bit word (2^WORD_SIZE)
        self._update_display()

    def __repr__(self) -> str:
        """Return human-readable ALU state for debugging and logging."""
        return (
            f"Control: {self.control} | "
            f"Value from ACC: {self.acc:04X} | Operand : {self.operand:04X} | "
            f"Result: {self.result:04X}"
        )
