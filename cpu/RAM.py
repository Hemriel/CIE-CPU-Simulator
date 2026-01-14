from constants import ComponentName
from dataclasses import dataclass, field

from component import CPUComponent

@dataclass
class RAM(CPUComponent):
    """Simple model of RAM with address and data registers.

    Attributes:
        address: current address in RAM being accessed.
        data: current data at the addressed location.
        memory: internal dictionary simulating RAM storage.
    """
    name: ComponentName = ComponentName.RAM_DATA
    address: int | None = None
    data: int | None = None
    memory: dict[int, int] = field(default_factory=lambda: dict((n, 0) for n in range(2**16)))

    def read(self, address: int) -> int | None:
        """Read data from the specified RAM address."""
        self.address = address
        self.data = self.memory.get(address)
        self._update_display()
        return self.data

    def write(self, address: int, data: int) -> None:
        """Write data to the specified RAM address."""
        self.address = address
        self.data = data
        self.memory[address] = data
        self._update_display()