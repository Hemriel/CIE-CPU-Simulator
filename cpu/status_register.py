from component import CPUComponent
from dataclasses import dataclass


@dataclass
class StatusRegister(CPUComponent):
    """A status register tracking condition flags for the CPU simulator.

    Attributes:
        zero: Indicates if the last operation resulted in a zero value.
        negative: Indicates if the last operation resulted in a negative value.
        overflow: Indicates if the last operation caused an arithmetic overflow.
    """

    zero: bool = False
    negative: bool = False
    carry: bool = False
    comparison: bool = False

    def update_flags(self, result: int, carry: bool) -> None:
        """Update the status flags based on the ALU result and conditions."""
        self.zero = result == 0
        self.negative = (result < 0) or (result & (1 << 15) != 0)
        self.carry = carry
        self.comparison = bool(result)
        self._update_display()
