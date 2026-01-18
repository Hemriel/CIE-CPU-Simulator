"""Control Unit (CU) module for the CPU simulator."""

from dataclasses import dataclass, field
from cpu.component import CPUComponent
from common.constants import (
    ComponentName,
    ControlSignal,
    CYCLE_PHASES,
    CyclePhase,
    MissingComponentError,
    RegisterIndex,
)
from cpu.ALU import ALU, FlagComponent
from cpu.register import Register
from cpu.buses import Bus
from cpu.RAM import RAM, RAMAddress
from cpu.cpu_io import IO
from common.instructions import (
    RTNStep,
    instruction_set,
    SimpleTransferStep,
    ALUOperationStep,
    MemoryAccessStep,
    RegOperationStep,
    ConditionalTransferStep,
    FETCH_RTNSteps,
    DECODE_RTNSteps,
    FETCH_LONG_OPERAND_RTNSteps,
)


def create_required_components_for_CU(
    mar: Register,
    mdr: Register,
    pc: Register,
    cir: Register,
    acc: Register,
    ix: Register,
    alu: ALU,
    cmp_flag: FlagComponent,
    address_bus: Bus,
    inner_data_bus: Bus,
    outer_data_bus: Bus,
    ram_address: RAMAddress,
    ram_data: RAM,
    in_component: IO,
    out_component: IO,
) -> dict[ComponentName, CPUComponent]:
    """Bundle every register, bus, and flag into the map that the CU will use.

    This helper is the single place where the machine builder proves that every
    register and bus required by the RTN sequences exists, so the CU can trust
    direct lookups rather than peppering the code with guards.
    """
    components = {
        ComponentName.MAR: mar,
        ComponentName.MDR: mdr,
        ComponentName.PC: pc,
        ComponentName.CIR: cir,
        ComponentName.ACC: acc,
        ComponentName.IX: ix,
        ComponentName.ALU: alu,
        ComponentName.CMP_Flag: cmp_flag,
        ComponentName.ADDRESS_BUS: address_bus,
        ComponentName.INNER_DATA_BUS: inner_data_bus,
        ComponentName.OUTER_DATA_BUS: outer_data_bus,
        ComponentName.RAM_ADDRESS: ram_address,
        ComponentName.RAM_DATA: ram_data,
        ComponentName.IN: in_component,
        ComponentName.OUT: out_component,
    }
    return components


@dataclass
class CU(CPUComponent):
    """Model of the Control Unit (CU) that orchestrates fetch/decode/execute timing.

    The CU always runs with a complete mapping from every ComponentName to its
    instance so that register-transfer notation (RTN) steps can refer to concrete
    hardware pieces without extra safety checks. Whoever builds the machine uses
    ``create_required_components_for_CU`` to supply this mapping.
    """

    components: dict[ComponentName, CPUComponent] = field(default_factory=dict)
    name: ComponentName = ComponentName.CU

    binary_instruction: int | None = None
    current_instruction: str | None = None
    opcode: int | None = None
    operand: int | None = None

    current_RTNStep: RTNStep | None = None
    RTN_sequence: list[RTNStep] = field(default_factory=list)
    RTN_sequence_index: int = 0
    current_phase: CyclePhase = field(default_factory=lambda: CYCLE_PHASES.__next__())

    def __post_init__(self):
        """Guard the CU against being created without any of the names the RTN
        scripts will reference.

        The helper at the top of this module bundles every register, bus, and flag
        into ``components`` before the CU is constructed. This validation mirrors
        that discipline by raising ``MissingComponentError`` immediately if the
        mapping is incomplete, which lets the rest of the CU trust that lookups
        never fail.
        """
        missing = [
            name
            for name in ComponentName
            if name not in self.components
            and name not in [ComponentName.CU, ComponentName.OPERAND]
        ]
        if missing:
            raise MissingComponentError(
                f"CU initialization failed: missing {', '.join(map(str, missing))}"
            )

        self.enter_phase(self.current_phase)

    def read(self) -> int:
        return self.operand if self.operand is not None else 0

    def write(self, data: int) -> None:
        self.binary_instruction = data
        self.set_instruction(data)
        self._update_display()

    def compute_opcode(self, binary_instruction: int) -> int:
        """Extract the opcode from a binary instruction."""
        return binary_instruction >> 8

    def get_instruction_definition(self, opcode: int):
        """Retrieve the instruction definition for a given opcode."""
        definition = instruction_set.get(opcode)
        if not definition:
            raise ValueError(f"Invalid opcode: {opcode}")
        return definition

    def set_instruction(self, instruction: int) -> None:
        """Decode the current instruction into opcode and operand parts."""
        self.opcode = self.compute_opcode(instruction)
        self.operand = instruction & 0b0000000011111111
        self.current_instruction = f"{self.opcode:08b} {self.operand:08b}"
        instruction_def = self.get_instruction_definition(self.opcode)
        if instruction_def and instruction_def.long_operand:
            # Short instructions keep the operand in the CU, but long instructions need the MDR dance first.
            self.RTN_sequence = FETCH_LONG_OPERAND_RTNSteps
        else:
            # No extra RTN steps needed for short instructions, but we still refresh the UI.
            pass
        self._update_display()

    def print_instruction(self) -> None:
        """Print the current instruction in mnemonic form for debugging."""
        if self.opcode is None:
            raise ValueError("Cannot print instruction without a valid opcode.")
        instruction_def = self.get_instruction_definition(self.opcode)
        mnemonic = instruction_def.mnemonic
        if instruction_def.long_operand:
            operand = self.components[ComponentName.MDR].read()
        else:
            operand = self.operand
        print(f"{mnemonic} {operand}")  # type: ignore

    def enter_phase(self, phase: CyclePhase) -> None:
        """Set the CU to a new cycle phase and reset the RTN sequence."""
        self.RTN_sequence_index = 0
        print(f"=== {phase} ===")
        if phase == CyclePhase.FETCH:
            self.RTN_sequence = FETCH_RTNSteps
        elif phase == CyclePhase.DECODE:
            self.RTN_sequence = DECODE_RTNSteps
        elif phase == CyclePhase.EXECUTE:
            if self.opcode is None:
                raise ValueError("Cannot enter EXECUTE phase without a valid opcode.")
            self.print_instruction()
            instruction_def = self.get_instruction_definition(self.opcode)
            if instruction_def:
                if instruction_def.mnemonic == "END":
                    self.RTN_sequence = []
                    return
                else:
                    self.RTN_sequence = instruction_def.rtn_sequence
            else:
                self.RTN_sequence = []
                return
        self.current_RTNStep = self.RTN_sequence[0]
        self._update_display()

    def step_RTNSeries(self) -> bool:
        """Advance to the next RTN step in the current instruction's sequence.

        If the end of the sequence is reached, returns True.
        """
        if self.current_RTNStep is None:
            raise ValueError("No current RTN step to execute.")

        self.execute_RTN_step(self.current_RTNStep)
        self.RTN_sequence_index += 1
        self._update_display()

        if self.RTN_sequence_index < len(self.RTN_sequence):
            self.current_RTNStep = self.RTN_sequence[self.RTN_sequence_index]
            return False
        else:
            self.current_RTNStep = None
            return True

    def step_cycle(self) -> bool:
        if not self.RTN_sequence:
            # Empty RTN sequence means the program has ended or no instruction is loaded.
            return True
        if (
            self.step_RTNSeries()
        ):  # step_RTNSeries executes an RTN and returns True if the sequence is complete
            self.current_phase = CYCLE_PHASES.__next__()
            self.enter_phase(self.current_phase)
        return False

    def execute_RTN_step(self, step: RTNStep) -> None:
        """Execute a single RTN step by coordinating component actions."""
        # The RTN step classes act like tiny microinstructions; this table routes each kind to the right helper.
        dispatcher = {
            SimpleTransferStep: self._handle_simple_transfer,
            ConditionalTransferStep: self._handle_conditional_transfer,
            MemoryAccessStep: self._handle_memory_access,
            ALUOperationStep: self._handle_alu_operation,
            RegOperationStep: self._handle_reg_operation,
        }
        handler = dispatcher[type(step)]
        handler(step)

    def _evaluate_condition(self, condition: bool) -> bool:
        # The CMP flag is a single-bit comparison result that RTN steps query.
        cmp_flag = self.components[ComponentName.CMP_Flag]
        return condition == cmp_flag.read()

    def _get_dest(self, destination: ComponentName) -> CPUComponent:
        """Helper to fetch the destination component for a transfer or register operation.
        Accomodates for the fact that MOV, INC, and DEC can target registers by index.
        """
        if destination != ComponentName.OPERAND:
            return self.components[destination]
        else:
            # Operand-targeting instructions use the operand as a register index.
            if self.operand is None:
                raise ValueError(
                    "Operand is not set; cannot determine destination register."
                )
            reg_index = self.operand
            for key, value in RegisterIndex.items():
                if value == reg_index:
                    destination = key
                    break
            if not destination:
                raise ValueError(f"Invalid register index in operand: {reg_index}")
            return self.components[destination]
        
    def _handle_simple_transfer(self, step: SimpleTransferStep) -> None:
        """Move data along the inner data bus exactly as RTN lists."""
        source_comp = self.components[step.source]
        dest_comp = self._get_dest(step.destination)
        bus = self.components[ComponentName.INNER_DATA_BUS]
        data = source_comp.read()
        bus.write(data)
        dest_comp.write(data)

    def _handle_conditional_transfer(self, step: ConditionalTransferStep) -> None:
        condition_met = self._evaluate_condition(step.condition)
        if condition_met:
            self._handle_simple_transfer(
                SimpleTransferStep(source=step.source, destination=step.destination)
            )

    def _handle_memory_access(self, step: MemoryAccessStep) -> None:
        if step.is_address:
            # Address fetch step (MAR -> memory address bus).
            mar = self.components[ComponentName.MAR]
            ram_address = self.components[ComponentName.RAM_ADDRESS]
            bus = self.components[ComponentName.ADDRESS_BUS]
            address = mar.read()
            bus.write(address)
            ram_address.write(address)
        else:
            # Data transfer step uses the MDR/RAM data registers depending on the control signal.
            bus = self.components[ComponentName.OUTER_DATA_BUS]
            if step.control == ControlSignal.WRITE:
                ram_data = self.components[ComponentName.RAM_DATA]
                mdr = self.components[ComponentName.MDR]
                data = mdr.read()
                bus.write(data)
                ram_data.write(data)
            else:
                mdr = self.components[ComponentName.MDR]
                ram_data = self.components[ComponentName.RAM_DATA]
                data = ram_data.read()
                bus.write(data)
                mdr.write(data)

    def _handle_alu_operation(self, step: ALUOperationStep) -> None:
        # ALU operations always read the ACC first and combine it with the RTN operand.
        alu: ALU = self.components[ComponentName.ALU]  # type: ignore Generic type 'CPUComponent' has no attribute 'set_operands', but ALU does.
        acc = self.components[ComponentName.ACC]
        source_comp = self.components[step.source]
        alu.set_operands(acc.read(), source_comp.read())
        alu.set_mode(step.control)
        alu.compute()

    def _handle_reg_operation(self, step: RegOperationStep) -> None:
        # Register INC/DEC steps can use another register to define how far to move.
        reg_comp = self._get_dest(step.destination)
        offset = 1
        if step.source:
            source_comp = self.components[step.source]
            offset = source_comp.read()
        if step.control == ControlSignal.INC:
            value = reg_comp.read()
            reg_comp.write(value + offset)
        elif step.control == ControlSignal.DEC:
            value = reg_comp.read()
            reg_comp.write(value - offset)

    def __repr__(self) -> str:
        """Render a summary of the CU's current state for debugging."""
        bin_str = (
            f"{self.binary_instruction:04X}"
            if self.binary_instruction is not None
            else "None"
        )
        return (
            f"CU | Instruction: {self.current_instruction if self.current_instruction is not None else 'None'} | "
            f"Opcode: {self.opcode} | Operand: {self.operand} | "
            f"Binary Instruction: {bin_str} | "
            f"Current RTN Step: {self.current_RTNStep if self.current_RTNStep is not None else 'None'}"
        )


if __name__ == "__main__":
    cu = CU(name=ComponentName.CU)
    cu.set_instruction(0b000111000010100)
