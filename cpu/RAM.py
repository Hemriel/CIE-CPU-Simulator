from constants import ComponentName
from dataclasses import dataclass, field

from component import CPUComponent

@dataclass
class RAMAddress(CPUComponent):
    """Simple model of RAM address register.

    Attributes:
        address: current address in RAM being accessed.
    """
    name: ComponentName = ComponentName.RAM_ADDRESS
    address: int = 0

    def read(self) -> int:
        """Read the current RAM address."""
        return self.address

    def write(self, address: int) -> None:
        """Write a new RAM address."""
        self.address = address
        self._update_display()

@dataclass
class RAM(CPUComponent):
    """Simple model of RAM with address and data registers.

    Attributes:
        address: current address in RAM being accessed.
        data: current data at the addressed location.
        memory: internal dictionary simulating RAM storage.
    """
    name: ComponentName = ComponentName.RAM_DATA
    address_comp: RAMAddress = RAMAddress(ComponentName.RAM_ADDRESS)
    memory: dict[int, int] = field(default_factory=lambda: dict((n, 0) for n in range(2**16)))

    def read(self) -> int | None:
        """Read data from the specified RAM address."""
        address = self.address_comp.read()
        self.data = self.memory.get(address)
        self._update_display()
        return self.data

    def write(self, data: int) -> None:
        """Write data to the specified RAM address."""
        address = self.address_comp.read()
        self.memory[address] = data
        self._update_display()