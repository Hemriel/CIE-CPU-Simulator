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
    last_RTNStep: RTNStep | None = None
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
        self._update_display()

    def stringify_operand(self) -> str:
        # logic changes depending on whether opcode is set
        if self.opcode is None:
            return "None"
        # If the current instruction uses a long operand, displays "long" instead of the raw value.
        instruction_def = self.get_instruction_definition(self.opcode)
        if instruction_def and instruction_def.long_operand:
            return "long"
        # if the current instruction uses a RegisterIndex as operand, display the register name
        for key, value in RegisterIndex.items():
            if value == self.operand:
                return key.name
        # Otherwise, just return the raw operand value.
        return str(self.operand)

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
        # Note: We intentionally do not advance or display the *next* step at the
        # end of the previous tick. Instead, we select the step to execute at the
        # start of the next tick (see step_cycle), so the UI stays in sync with
        # whichever components were active for the tick just executed.
        self.current_RTNStep = self.RTN_sequence[0] if self.RTN_sequence else None

    def step_RTNSeries(self) -> bool:
        """Execute exactly one RTN step from the current RTN sequence.

        This helper advances the RTN sequence index but does **not** change the
        CPU phase. Phase transitions are handled in :meth:`step_cycle` at the
        start of the next tick so the CU display does not get ahead of the rest
        of the CPU visualisation.

        Returns:
            True if the RTN sequence has been fully executed after this step.
        """

        if not self.RTN_sequence:
            self.current_RTNStep = None
            return True

        if self.RTN_sequence_index >= len(self.RTN_sequence):
            self.current_RTNStep = None
            return True

        # Select the step to execute *now* (based on the current index).
        self.current_RTNStep = self.RTN_sequence[self.RTN_sequence_index]
        self.execute_RTN_step(self.current_RTNStep)
        self.last_RTNStep = self.current_RTNStep
        self.RTN_sequence_index += 1
        self._update_display()

        return self.RTN_sequence_index >= len(self.RTN_sequence)

    def step_cycle(self) -> bool:
        """Advance the CPU by one *visible* micro-step.

        The CU prepares (phase changes + choosing the RTN step) **before** it
        executes the step. That way, the CU widget shows the same phase/RTN step
        that the rest of the CPU components are highlighting for this tick.

        Returns:
            True if the program has finished and there are no more RTN steps.
        """

        # Empty RTN sequence means the program has ended or no instruction is loaded.
        if not self.RTN_sequence:
            self.current_RTNStep = None
            self._update_display()
            return True

        # If we finished the previous phase's RTN sequence on the last tick,
        # advance the phase *now* (at the start of this tick), before executing
        # anything. This prevents the CU display from jumping ahead.
        if self.RTN_sequence_index >= len(self.RTN_sequence):
            self.current_phase = CYCLE_PHASES.__next__()
            self.enter_phase(self.current_phase)

            if not self.RTN_sequence:
                self.current_RTNStep = None
                self._update_display()
                return True

        # Execute one step from the (possibly new) phase. We intentionally do
        # not transition phases at the end of this call.
        self.step_RTNSeries()
        return False

    def execute_RTN_step(self, step: RTNStep, reset_active: bool = True) -> None:
        """Execute a single RTN step by coordinating component actions."""
        # The RTN step classes act like tiny microinstructions; this table routes each kind to the right helper.
        if reset_active:
            for component in self.components.values():
                component.set_last_active(False)
        self.set_last_active(True)
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

    def _resolve_destination_name(self, destination: ComponentName) -> ComponentName:
        """Resolve operand-based destinations into an explicit ComponentName.

        Some instructions (MOV/INC/DEC) encode a register index inside the operand.
        When RTN steps target OPERAND, we resolve it into the specific register name
        so the UI can draw accurate bus connections.
        """

        if destination != ComponentName.OPERAND:
            return destination
        if self.operand is None:
            raise ValueError("Operand is not set; cannot determine destination register.")
        reg_index = self.operand
        for key, value in RegisterIndex.items():
            if value == reg_index:
                return key
        raise ValueError(f"Invalid register index in operand: {reg_index}")
        
    def _handle_simple_transfer(self, step: SimpleTransferStep) -> None:
        """Move data along the inner data bus exactly as RTN lists."""
        source_comp = self.components[step.source]
        source_comp.set_last_active(True)
        dest_name = self._resolve_destination_name(step.destination)
        dest_comp = self.components[dest_name]
        dest_comp.set_last_active(True)
        bus = self.components[ComponentName.INNER_DATA_BUS]
        bus.set_last_active(True)
        # Record the endpoints for UI wiring.
        try:
            bus.set_last_connection(step.source, dest_name)  # type: ignore[attr-defined]
        except Exception:
            # Keep the CPU simulation robust even if UI metadata isn't available.
            pass
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
            mar.set_last_active(True)
            ram_address = self.components[ComponentName.RAM_ADDRESS]
            ram_address.set_last_active(True)
            bus = self.components[ComponentName.ADDRESS_BUS]
            bus.set_last_active(True)
            try:
                bus.set_last_connection(ComponentName.MAR, ComponentName.RAM_ADDRESS)  # type: ignore[attr-defined]
            except Exception:
                pass
            address = mar.read()
            bus.write(address)
            ram_address.write(address)
        else:
            # Data transfer step uses the MDR/RAM data registers depending on the control signal.
            bus = self.components[ComponentName.OUTER_DATA_BUS]
            bus.set_last_active(True)
            if step.control == ControlSignal.WRITE:
                ram_data = self.components[ComponentName.RAM_DATA]
                ram_data.set_last_active(True)
                mdr = self.components[ComponentName.MDR]
                mdr.set_last_active(True)
                try:
                    bus.set_last_connection(ComponentName.MDR, ComponentName.RAM_DATA)  # type: ignore[attr-defined]
                except Exception:
                    pass
                data = mdr.read()
                bus.write(data)
                ram_data.write(data)
            else:
                mdr = self.components[ComponentName.MDR]
                mdr.set_last_active(True)
                ram_data = self.components[ComponentName.RAM_DATA]
                ram_data.set_last_active(True)
                try:
                    bus.set_last_connection(ComponentName.RAM_DATA, ComponentName.MDR)  # type: ignore[attr-defined]
                except Exception:
                    pass
                data = ram_data.read()
                bus.write(data)
                mdr.write(data)

    def _handle_alu_operation(self, step: ALUOperationStep) -> None:
        # ALU operations always read the ACC first and combine it with the RTN operand.
        alu: ALU = self.components[ComponentName.ALU]  # type: ignore Generic type 'CPUComponent' has no attribute 'set_operands', but ALU does.
        alu.set_last_active(True)
        acc = self.components[ComponentName.ACC]
        acc.set_last_active(True)
        source_comp = self.components[step.source]
        source_comp.set_last_active(True)
        alu.set_operands(acc.read(), source_comp.read())
        alu.set_mode(step.control)
        alu.compute()

    def _handle_reg_operation(self, step: RegOperationStep) -> None:
        # Register INC/DEC steps can use another register to define how far to move.
        reg_comp = self._get_dest(step.destination)
        reg_comp.set_last_active(True)
        offset = 1
        if step.source:
            source_comp = self.components[step.source]
            source_comp.set_last_active(True)
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
