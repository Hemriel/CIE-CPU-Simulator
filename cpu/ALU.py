"""Arithmetic logic unit that executes ALU control signals and tracks flags."""

from dataclasses import dataclass
from typing import Protocol
from component import CPUComponent
from constants import ControlSignal


class FlagComponent(Protocol):
    """A component that can update status flags based on an ALU result."""

    def update_flags(self, result: int, carry: bool, overflow: bool) -> None: ...


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
    operand_a: int | None = None
    operand_b: int | None = None
    result: int | None = None
    flag_component: FlagComponent | None = None
    carry: bool = False

    def set_mode(self, control: ControlSignal | None) -> None:
        """Select the ALU operation mode and refresh the UI so RTN can display it."""

        self.control = control
        self._update_display()

    def set_operands(self, operand_a: int | None, operand_b: int | None) -> None:
        """Provide operands from register transfers and redraw the panel."""

        self.operand_a = operand_a
        self.operand_b = operand_b
        self._update_display()

    def compute(self) -> None:
        """Execute the selected ControlSignal, store the result, and update flags."""

        if self.control is None or self.operand_a is None or self.operand_b is None:
            self.result = None
        else:
            # Every ControlSignal maps to a deterministic arithmetic or logic function.
            if self.control == ControlSignal.ADD:
                self.result = self.operand_a + self.operand_b
            elif self.control == ControlSignal.SUB:
                self.result = self.operand_a - self.operand_b
            elif self.control == ControlSignal.AND:
                self.result = self.operand_a & self.operand_b
            elif self.control == ControlSignal.OR:
                self.result = self.operand_a | self.operand_b
            elif self.control == ControlSignal.XOR:
                self.result = self.operand_a ^ self.operand_b
            elif self.control == ControlSignal.CMP:
                self.result = int(self.operand_a == self.operand_b)
            else:
                self.result = None

        if self.flag_component and self.result is not None:
            self.flag_component.update_flags(self.result, False, False)

        self._update_display()

    def _set_result(self, result: int | None) -> None:
        """Store the computed result and refresh the UI display."""

        self.carry = result is not None and (result < 0 or result >= (1 << 16))
        self.result = result 

