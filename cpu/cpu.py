"""Top-level CPU module that wires all components together.

Responsibility:
- Instantiate and connect all CPU components (registers, buses, RAM, ALU, CU, I/O)
  into a single cohesive CPU object.
- Provide a simple, student-friendly API for loading programs and stepping through
  execution one RTN operation at a time.
- Serve as the main entry point for CPU simulation, hiding the complexity of
  component interactions behind a clean interface.

Illustrates:
- CIE 9618: 4.1 Central Processing Unit Architecture:
    - Show understanding of the purpose and roles of registers.
    - Show understanding of the purpose and roles of the ALU, CU.
    - Show understanding of how data are transferred between various components using buses.

Design choices:
- The CPU class owns all components and passes references to the Control Unit,
  which orchestrates data movement via RTN sequences. This mirrors real hardware
  where the CU sends control signals to coordinate component activity.
- Registers (PC, MAR, MDR, CIR, ACC, IX) are created first because they form
  the core data path described in CIE 9618.
- Buses exist primarily for RTN visualization; they don't implement data transfer
  logic since Python references handle that directly.
- The ALU receives a dedicated flag component for comparison operations, following
  the CIE model where the status register tracks condition codes.
- RAM is separated into address and data components to make the MAR/MDR interaction
  explicit in the UI.
- I/O components model the IN/OUT instructions as simple character queues.

Entry points / public API:
- `CPU` class: main simulator interface.
  - `load_program(program)`: load machine code into RAM.
  - `step()`: advance the CU by one RTN step.

Contained classes:
- `CPU`

Educational notes:
- This module demonstrates the von Neumann architecture: a single shared memory
  space for instructions and data, with a control unit that fetches, decodes, and
  executes instructions in sequence.
- The component wiring makes the fetch-decode-execute cycle visible: PC points to
  the next instruction, MAR/MDR handle memory access, CIR holds the current
  instruction, and ACC performs computations.
"""

from common.constants import ComponentName
from cpu.CU import CU, create_required_components_for_CU
from cpu.ALU import ALU, FlagComponent
from cpu.buses import Bus
from cpu.RAM import RAM, RAMAddress
from cpu.register import Register
from cpu.cpu_io import IO


class CPU:
    """Complete CPU simulation that connects all components and exposes a step API.

    This class models the CIE 9618 CPU architecture, including:
    - Registers: PC, MAR, MDR, CIR, ACC, IX (as defined in the specification)
    - Buses: address bus and internal data bus (for RTN visualization)
    - ALU: performs arithmetic and logic operations
    - RAM: stores both instructions and data (von Neumann architecture)
    - I/O: models IN/OUT instructions for character-based input/output
    - Control Unit: orchestrates the fetch-decode-execute cycle

    The CPU can be loaded with a program (list of machine words) and stepped
    through execution one RTN operation at a time, making the internal data
    flow visible for educational purposes.
    """

    def __init__(self) -> None:
        """Initialize all CPU components and wire them to the Control Unit.

        This creates the complete data path and control path as specified in
        CIE 9618. The order of initialization follows the logical structure:
        registers → buses → ALU → RAM → I/O → Control Unit.
        """
        # Create the six main registers defined in CIE 9618.
        # These form the core data path for instruction execution.
        self.mar = Register(name=ComponentName.MAR)  # Memory Address Register
        self.mdr = Register(name=ComponentName.MDR)  # Memory Data Register
        self.pc = Register(name=ComponentName.PC)    # Program Counter
        self.cir = Register(name=ComponentName.CIR)  # Current Instruction Register
        self.acc = Register(name=ComponentName.ACC)  # Accumulator
        self.ix = Register(name=ComponentName.IX)    # Index Register    # Index Register

        # Create buses for RTN visualization.
        # In this simulator, buses are display-only; actual data transfer happens
        # via Python references. This keeps the code simple while still showing
        # students the conceptual flow of data between components.
        self.address_bus = Bus(name=ComponentName.ADDRESS_BUS)
        self.inner_data_bus = Bus(name=ComponentName.INNER_DATA_BUS)

        # Create the ALU with a dedicated flag component.
        # The flag tracks comparison results (CMP instruction) so conditional
        # jumps can be executed
        self.cmp_flag = FlagComponent()
        self.alu = ALU(flag_component=self.cmp_flag)

        # Create RAM with a separate address component.
        # This separation makes the MAR → RAM address flow explicit in the UI,
        # matching the CIE model where MAR always holds the address for memory
        # operations.
        self.ram_address = RAMAddress()
        self.ram = RAM(address_comp=self.ram_address)

        # Create I/O components for IN/OUT instructions.
        # These model simple character-based input (keyboard) and output (screen)
        # as specified in CIE 9618.
        self.io_in = IO(name=ComponentName.IN)
        self.io_out = IO(name=ComponentName.OUT)

        # Creates the list of all components to prepare for Control Unit creation.
        # The CU needs references to every component it will control during
        # instruction execution. This implements the "control path" from CIE 9618:
        # the CU sends control signals to coordinate data movement.
        # In a real CPU, this would be done via a control bus; here, we pass
        # references directly for simplicity.
        components = create_required_components_for_CU(
            mar=self.mar,
            mdr=self.mdr,
            pc=self.pc,
            cir=self.cir,
            acc=self.acc,
            ix=self.ix,
            alu=self.alu,
            cmp_flag=self.cmp_flag,
            address_bus=self.address_bus,
            inner_data_bus=self.inner_data_bus,
            ram_address=self.ram_address,
            ram_data=self.ram,
            in_component=self.io_in,
            out_component=self.io_out,
        )

        # Create the Control Unit, which orchestrates the fetch-decode-execute cycle.
        self.cu = CU(components=components)

        # Initialize CPU state.
        self.cycles = 0  # Count of RTN steps executed
        self.pc.write(0)  # Start execution at address 0

        # Add the CU itself to the components dictionary for UI access.
        components[ComponentName.CU] = self.cu
        self.components = components

    def load_program(self, program: list[int]) -> None:
        """Load a list of instruction words into RAM starting at address 0.

        This models the initial program loading that happens before execution
        starts. In real systems, this would be done by an operating system or
        bootloader; here, we do it directly for simplicity.

        Args:
            program: A list of 16-bit machine words representing the assembled
                program. Each word is an instruction opcode or operand.
        """
        self.ram_address.write(0)
        for address, word in enumerate(program):
            self.ram_address.write(address)
            # Mask to 16 bits (0xFFFF) to ensure all words fit in WORD_SIZE.
            # This is critical because Python integers are unbounded, but our
            # simulated CPU has a fixed word size.
            self.ram.write(word & 0xFFFF)
        # Reset PC to 0 so execution starts at the first instruction.
        self.pc.write(0)

    def step(self) -> bool:
        """Advance the Control Unit by one RTN step.

        This is the main execution method. Each call performs one micro-operation
        in the fetch-decode-execute cycle, such as "MAR ← PC" or "ACC ← ACC + MDR".
        The UI can call this repeatedly to animate the CPU's operation.

        Returns:
            True if the CPU has reached a halt state (END instruction or error),
            False if execution should continue.
        """
        # Delegate to the Control Unit's step logic, which implements the
        # fetch-decode-execute cycle as a sequence of RTN steps.
        finished = self.cu.step_cycle()
        self.cycles += 1  # Track total RTN steps for debugging/statistics
        return finished

    def __repr__(self) -> str:
        """Return a string representation of the CPU state for debugging.

        This provides a snapshot of all major registers, the current RTN step,
        and the current RAM location being accessed. Useful for non-UI debugging
        or logging execution traces.

        Returns:
            A formatted string showing register values in hexadecimal, the current
            RTN step, and the cycle count.
        """
        # Display the current RTN step name, or "None" if not yet started.
        step = (
            self.cu.current_RTNStep if self.cu.current_RTNStep is not None else "None"
        )
        # Format all values as 4-digit hexadecimal for consistency with
        # typical assembly language notation.
        return (
            f"{step} with : "
            f"PC: {self.pc._value:04X} | "
            f"CIR: {self.cir._value:04X} | "
            f"MAR: {self.mar._value:04X} | "
            f"MDR: {self.mdr._value:04X} | "
            f"ACC: {self.acc._value:04X} | "
            f"IX: {self.ix._value:04X} | "
            f"ALU: {self.alu.result:04X} | "
            f"RAM[{self.ram_address.address:04X}] = {self.ram.memory.get(self.ram_address.address, 0):04X} | "
            f"Cycles: {self.cycles}"
        )


if __name__ == "__main__":
    # Simple test harness for non-UI debugging.
    # This demonstrates how to use the CPU API: initialize, load a program,
    # step through execution, and inspect results.

    # Create and inspect the CPU.
    cpu = CPU()
    print("CPU initialized with components:")
    for name, component in cpu.components.items():
        print(f"{name}: {component}")

    # Load a program from a binary file (Fibonacci sequence generator).
    with open("fibo.bin", "r") as f:
        program = [int(line.strip(), 16) for line in f.readlines()]
    cpu.load_program(program)
    print("Program loaded into RAM.")

    # Display the loaded program in RAM.
    ram_contents = [cpu.ram.memory[addr] for addr in range(len(program))]
    print("RAM Contents:")
    for addr, word in enumerate(ram_contents):
        print(f"Address {addr:04X}: {word:04X}")

    # Step through the program until completion.
    print(cpu)
    while not cpu.step():
        print(cpu)  # Print CPU state after each RTN step
    print("Program execution finished.")

    # Display the Fibonacci results stored in RAM.
    print("fibonacci results:")
    for i in range(20):
        print(f"fib({i}) = {cpu.ram.memory.get(i+200)}")
