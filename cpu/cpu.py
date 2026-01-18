"""Wire up every CPU component and expose an entry point for stepping the CU."""

from common.constants import ComponentName
from cpu.CU import CU, create_required_components_for_CU
from cpu.ALU import ALU, FlagComponent
from cpu.buses import Bus
from cpu.RAM import RAM, RAMAddress
from cpu.register import Register
from cpu.cpu_io import IO


class CPU:
    """High-level CPU assembly that owns registers, buses, RAM, and the CU."""

    def __init__(self) -> None:
        # Create registers that the CU's RTN sequences will move data between.
        self.mar = Register(name=ComponentName.MAR)
        self.mdr = Register(name=ComponentName.MDR)
        self.pc = Register(name=ComponentName.PC)
        self.cir = Register(name=ComponentName.CIR)
        self.acc = Register(name=ComponentName.ACC)
        self.ix = Register(name=ComponentName.IX)

        # Buses are purely for RTN visualization and so just exist as placeholders.
        self.address_bus = Bus(name=ComponentName.ADDRESS_BUS)
        self.inner_data_bus = Bus(name=ComponentName.INNER_DATA_BUS)
        self.outer_data_bus = Bus(name=ComponentName.OUTER_DATA_BUS)

        # The ALU talks to a devoted flag latch so CMP updates the comparison flag.
        self.cmp_flag = FlagComponent()
        self.alu = ALU(flag_component=self.cmp_flag)

        # RAM hooks share an address register so the CU can drive the address bus once per cycle.
        self.ram_address = RAMAddress()
        self.ram = RAM(address_comp=self.ram_address)

        # Simple I/O queues for keyboard/screen wiring.
        self.io_in = IO(name=ComponentName.IN)
        self.io_out = IO(name=ComponentName.OUT)

        # The CU must see every register, bus, and flag it will ever read or write.
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
            outer_data_bus=self.outer_data_bus,
            ram_address=self.ram_address,
            ram_data=self.ram,
            in_component=self.io_in,
            out_component=self.io_out,
        )

        self.cu = CU(components=components)

        self.cycles = 0
        self.pc.write(0)

        components[ComponentName.CU] = self.cu
        self.components = components

    def load_program(self, program: list[int]) -> None:
        """Load a list of instruction words into RAM starting at address 0."""

        self.ram_address.write(0)
        for address, word in enumerate(program):
            self.ram_address.write(address)
            # Align every value to WORD_SIZE bits since the datapath is word-sized.
            self.ram.write(word & 0xFFFF)
        self.pc.write(0)

    def step(self) -> bool:
        """Advance the Control Unit by one RTN step and execute it."""

        finished = self.cu.step_cycle()
        self.cycles += 1
        return finished

    def __repr__(self) -> str:
        """String representation of the CPU state for debugging purposes.

        Returns the values of the main registers and the current instruction.
        """
        step = (
            self.cu.current_RTNStep if self.cu.current_RTNStep is not None else "None"
        )
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
    cpu = CPU()
    print("CPU initialized with components:")
    for name, component in cpu.components.items():
        print(f"{name}: {component}")
    with open("fibo.bin", "r") as f:
        program = [int(line.strip(), 16) for line in f.readlines()]
    cpu.load_program(program)
    print("Program loaded into RAM.")
    ram_contents = [cpu.ram.memory[addr] for addr in range(len(program))]
    print("RAM Contents:")
    for addr, word in enumerate(ram_contents):
        print(f"Address {addr:04X}: {word:04X}")
    print(cpu)
    while not cpu.step():
        print(cpu)
    print("Program execution finished.")
    print("fibonacci results:")
    for i in range(20):
        print(f"fib({i}) = {cpu.ram.memory.get(i+200)}")
