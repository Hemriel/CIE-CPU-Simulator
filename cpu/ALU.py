"""Arithmetic logic unit that executes ALU control signals and tracks flags."""

from dataclasses import dataclass
from component import CPUComponent
from constants import ComponentName, ControlSignal

@dataclass
class FlagComponent(CPUComponent):
    """A component that can update status flags based on an ALU result."""
    name: ComponentName = ComponentName.CMP_Flag
    value = False

    def read(self) -> bool:
        """Read the current flag value."""
        return self.value
    
    def write(self, value: bool) -> None:
        """Write a new flag value."""
        self.value = value
        self._update_display()

    
@dataclass
class ALU(CPUComponent):
    """Model of the ALU following the CIE RTN description of arithmetic and logic ops.

    Attributes:
        control: the ControlSignal currently armed for the pending operation.
        operand_a: first operand driven by the register transfers (usually ACC).
        operand_b: second operand (literal, memory, or bus driven).
        result: stored result to visualize the pending write back.
        flag_component: optional receiver that updates the status/register flags.
    """

    control: ControlSignal | None = None
    operand_a: int = 0
    operand_b: int = 0
    result: int = 0
    flag_component: FlagComponent = FlagComponent()

    def read(self) -> int:
        return self.result
    
    def write(self, data: int) -> None:
        raise ValueError("ALU does not support direct writes.")

    def set_mode(self, control: ControlSignal | None) -> None:
        """Select the ALU operation mode and refresh the UI so RTN can display it."""

        self.control = control
        self._update_display()

    def set_operands(self, operand_a: int, operand_b: int) -> None:
        """Provide operands from register transfers and redraw the panel."""

        self.operand_a = operand_a
        self.operand_b = operand_b
        self._update_display()

    def compute(self) -> None:
        """Execute the selected ControlSignal, store the result, and update flags."""
            # Every ControlSignal maps to a deterministic arithmetic or logic function.
        if self.control == ControlSignal.ADD:
            self._set_result(self.operand_a + self.operand_b)
        elif self.control == ControlSignal.SUB:
            self._set_result(self.operand_a - self.operand_b)
        elif self.control == ControlSignal.AND:
            self._set_result(self.operand_a & self.operand_b)
        elif self.control == ControlSignal.OR:
            self._set_result(self.operand_a | self.operand_b)
        elif self.control == ControlSignal.XOR:
            self._set_result(self.operand_a ^ self.operand_b)
        elif self.control == ControlSignal.CMP:
            compare = (self.operand_a == self.operand_b)
            self.flag_component.write(compare)
        else:
            self._set_result(0)  # Default fallback for unsupported operations.

    def _set_result(self, result: int) -> None:
        """Store the computed result and refresh the UI display."""
        self.result = result % (1 << 16)  # Assuming 16-bit ALU width.
        self._update_display()

