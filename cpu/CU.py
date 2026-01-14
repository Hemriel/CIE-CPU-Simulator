"""Control Unit (CU) module for the CPU simulator."""

from dataclasses import dataclass
from component import CPUComponent
from constants import ComponentName
from instructions import RTNStep

@dataclass
class CU(CPUComponent):
    """Model of the Control Unit (CU) responsible for sequencing operations.

    Attributes:
        control_signal: the ControlSignal currently being issued by the CU.
    """
    name: ComponentName = ComponentName.CU
    current_instruction: str | None = None
    opcode: int | None = None
    operand: int | None = None
    current_RTNStep: RTNStep | None = None

    def set_instruction(self, instruction: int) -> None:
        """Decode the current instruction into opcode and operand parts."""
        self.opcode = (instruction >> 8)
        self.operand = instruction & 0b0000011111111111
        self.current_instruction = f"{self.opcode:08b} {self.operand:08b}"
        self._update_display()


if __name__ == "__main__":
    cu = CU(name=ComponentName.CU)
    cu.set_instruction(0b011100000010100)