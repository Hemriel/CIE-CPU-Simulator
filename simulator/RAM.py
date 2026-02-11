"""Memory (RAM) model for the CIE CPU simulator.

Responsibility:
- Simulate Random Access Memory (RAM) as a key component of the von Neumann
  architecture, providing read/write access to stored instructions and data.
- Maintain a memory store indexed by address, supporting instruction fetch and
  data access operations required by the CPU.

Illustrates:
- CIE 9618: 4.1 Central Processing Unit (CPU) Architecture:
    - Show understanding of the basic Von Neumann model for a computer system and the stored program concept.
    - Show understanding of how data are transferred between various components using the address bus and data bus.
    - Show understanding of the purpose and roles of registers (MAR/MDR for memory access).
- CIE 9618: 1.1 Data representation:
    - Show understanding of how binary data is stored and retrieved from memory.

Design notes:
- RAM is modeled as a dictionary mapping integer addresses to word values.
- RAM is split into two components, an adress storage, and a data storage. This
  is done to mirror the MAR and MDR registers inside the CPU and to reinforce
  the separation of address and data pathways.
- This separation makes the bus transactions explicit in the UI, showing
  how the CPU accesses memory through distinct address and data buses.
- Memory is initialized as all zeros (a common practice in simulation).

Entry points:
- :class:`RAM`: Main memory component accessed by the CPU.
- :class:`RAMAddress`: Companion register that holds the current address.

Includes:
- :class:`RAMAddress`: Address register for specifying memory locations.
- :class:`RAM`: Main memory storage with read/write operations.
"""

from dataclasses import dataclass, field
from common.constants import ComponentName, WORD_SIZE
from simulator.component import CPUComponent


### Educational notes on Python operations used in this module ###
#
# Dataclasses (RAMAddress and RAM classes):
# Data classes are NOT in the curriculum.
# Here is a detailed explanation: https://docs.python.org/3/library/dataclasses.html
# In a few words, they are a concise way to define classes that mainly store
# data attributes. The __init__, __repr__, __eq__, and other methods are
# automatically generated based on the class attributes.
#
# field with default_factory (appears in RAM class):
# The field(default_factory=...) pattern creates a fresh object for each
# instance. Without default_factory, all RAM instances would share the same
# memory dictionary, causing unexpected behavior (mutable default argument problem).
# This is critical for RAM because we need each CPU simulation to have its own
# independent memory space.
# More info: https://docs.python.org/3/library/dataclasses.html#mutable-default-values
#
# Lambda functions (appear in default_factory):
# Lambda is Python's syntax for anonymous (unnamed) functions.
# Example: lambda: dict((n, 0) for n in range(2**WORD_SIZE))
# This creates a function that returns a new memory dictionary initialized to zeros.
# It's used so the dictionary is created fresh for each instance, not reused.


@dataclass
class RAMAddress(CPUComponent):
    """Address component for specifying which memory location to access.
    
    This component models only the address aspect of memory access. The actual data
    is stored in the :class:`RAM` class. This component is the direct interface
    for the MAR (Memory Address Register) in CIE 9618.
    
    Attributes:
        name: The component identifier (ComponentName.RAM_ADDRESS).
        address: The current memory address (0 to 2^WORD_SIZE - 1).
        last_active: Whether this component participated in the last RTN step.
        displayer: Optional UI component to refresh on state changes.
    """

    name: ComponentName = ComponentName.RAM_ADDRESS
    address: int = 0

    def read(self) -> int:
        """Read the current memory address stored.
        
        This is read by the data component of the RAM during memory access operations.
        
        Returns:
            The current address as a 16-bit integer (0 to 65535).
        """
        return self.address

    def write(self, address: int) -> None:
        """Update the stored address to point to a new memory address.

        In the CIE 9618 model, the CPU sets this address before reading from or writing to
        memory. The address is typically provided by the PC (for instruction fetch), the operand
        or fetched from memory for indirect addressing modes.
        
        Args:
            address: The new memory address to set. Should be in the
                range 0 to 65535 (16-bit).
        """
        self.address = address
        self._update_display()

    def __repr__(self) -> str:
        """Return a human-readable representation of the current address.
        
        Used for debugging and UI display to show the current memory address
        in hexadecimal format (4 digits, zero-padded).
        
        Returns:
            The current address as a 4-digit hexadecimal string (e.g., '0042').
        """
        return f"{self.address:04X}"


@dataclass
class RAM(CPUComponent):
    """Random Access Memory.
    
    This class models the memory subsystem in CIE 9618, handling both the storage
    of instruction and data words.
    
    The memory model follows the von Neumann architecture: a single address space
    containing both executable instructions and data. The CPU accesses memory
    through a two-step process:
    1. Place the desired address in MAR (Memory Address Register), then 
    transmit to RAMAddress component.
    2. Read (RAM to MDR) or write (MDR to RAM) data.
    
    When read() is called, the data at the address specified by the companion
    RAMAddress is retrieved. When write() is called, data is stored at
    the address in the companion RAMAddress.
    
    Attributes:
        name: The component identifier (ComponentName.RAM_DATA).
        address_comp: Reference to RAMAddress used to select the memory location.
        memory: Dictionary mapping addresses (0 to 65535) to word values (0 to 65535).
            Initialized to all zeros, following the convention that memory starts clean.
        last_active: Whether this component participated in the last RTN step.
        displayer: Optional UI component to refresh on state changes.
    """

    name: ComponentName = ComponentName.RAM_DATA
    address_comp: RAMAddress = field(
        default_factory=lambda: RAMAddress(ComponentName.RAM_ADDRESS)
    )
    memory: dict[int, int] = field(
        default_factory=lambda: dict((n, 0) for n in range(2**WORD_SIZE))
    )

    def read(self) -> int | None:
        """Read data from the memory location specified by the RAMAddress.
        
        This implements the second step of a memory read operation in CIE 9618:
        1. CPU sets RAMAddress to the desired address
        2. CPU reads MDR (this method) to get the data
        
        The address is obtained from the companion RAMAddress component.
        If the address is out of range, None is returned (indicating no data).
        
        Returns:
            The 16-bit word stored at the address specified by RAMAddress, or None if
            the address is not found in memory.
        """
        # Retrieve the current address from RAMAddress (the companion address register)
        address = self.address_comp.read()
        # Fetch the data at that address from the memory dictionary
        self.data = self.memory.get(address)
        self._update_display()
        return self.data

    def write(self, data: int) -> None:
        """Write data to the memory location specified by the RAMAddress.
        
        This implements the second step of a memory write operation in CIE 9618:
        1. CPU sets RAMAddress to the desired address
        2. CPU writes data to MDR (this method) to store the data
        
        The address is obtained from the companion RAMAddress component.
        The data is masked to 16 bits to ensure it fits in a memory word,
        following the simulated CPU's word size.
        
        Args:
            data: The value to store at the address specified by RAMAddress. Will be
                masked to 16 bits (0 to 65535).
        """
        # Retrieve the current address from RAMAddress (the companion address register)
        address = self.address_comp.read()
        self.memory[address] = data % (
            1 << WORD_SIZE
        )
        self._update_display()

    def __repr__(self) -> str:
        """Return a human-readable representation of the memory status.
        
        Used for debugging and UI display to show the total size of the
        initialized memory.
        
        Returns:
            A string showing the number of words allocated in memory.
        """
        return f"Size: {len(self.memory)} words"
