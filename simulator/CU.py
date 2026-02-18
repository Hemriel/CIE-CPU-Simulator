"""Control Unit (CU) module that orchestrates the fetch-decode-execute cycle.

Responsibility:
- Implement the fetch-decode-execute cycle as a sequence of Register Transfer
  Notation (RTN) steps that can be visualized in the UI one micro-operation at
  a time.
- Decode instruction opcodes and operands from binary machine words.
- Coordinate data movement between registers, buses, ALU, and memory by executing
  RTN steps that represent individual control signals.
- Manage cycle phases (FETCH, DECODE, EXECUTE) and transition between them as
  RTN sequences complete.

Illustrates:
- CIE 9618: 4.1 Central Processing Unit (CPU) Architecture:
    - Show understanding of the purpose and roles of the ALU, CU.
    - Show understanding of how data are transferred between various components using the address bus, data bus, and control bus.
    - Describe the stages of the fetch-decode-execute cycle.
- CIE 9618: 4.2 Assembly Language:
    - Show understanding of the relationship between assembly language and machine code.
- CIE 9618: 9.1 Computational Thinking Skills:
    - Show an understanding of abstraction (RTN as abstraction of control signals).
    - Describe and use decomposition (fetch-decode-execute as distinct phases).

Design choices:
- The CU models hardware control signals as RTN steps (SimpleTransferStep,
  ALUOperationStep, etc.), making each micro-operation explicit and visible.
- All components are injected via a dictionary mapping ComponentName to instances,
  ensuring the CU can reference any register or bus without safety checks.
- Phase transitions happen at the start of each tick (not at the end), keeping
  the UI synchronized with component state changes.
- The CU treats instructions as "control signal recipes" rather than encapsulating
  full behavior, mirroring how real hardware decodes opcodes into control signals.

Entry points / public API:
- :class:`CU` class: the main Control Unit that orchestrates execution.
  - `step_cycle()`: advance by one RTN step.
  - `set_instruction(instruction)`: decode a new instruction.
- :func:`create_required_components_for_CU()`: helper function to bundle all components
  into the dictionary the CU requires.

Includes:
- :func:`create_required_components_for_CU()`: component bundling helper.
- :class:`CU`: the Control Unit class.
  - Phase management: `enter_phase()`, `step_cycle()`
  - RTN execution: `step_RTNSeries()`, `execute_RTN_step()`
  - RTN handlers: `_handle_simple_transfer()`, `_handle_alu_operation()`, etc.
  - Instruction decoding: `set_instruction()`, `compute_opcode()`

Educational notes:
- This module demonstrates how the fetch-decode-execute cycle works at the
  micro-operation level. Each RTN step corresponds to a control signal that
  would be sent by the control unit in real hardware.
- CIE 9618 requires students to understand RTN and the fetch-decode-execute
  cycle. This implementation makes both concepts visible by executing RTN steps
  one at a time and grouping them into FETCH, DECODE, and EXECUTE phases.
"""

from dataclasses import dataclass, field
from simulator.component import CPUComponent
from common.constants import (
    ComponentName,
    ControlSignal,
    CYCLE_PHASES,
    CyclePhase,
    MissingComponentError,
    RegisterIndex,
)
from simulator.ALU import ALU, FlagComponent
from simulator.register import Register
from simulator.buses import Bus
from simulator.RAM import RAM, RAMAddress
from simulator.cpu_io import IO
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


### Educational notes on Python operations used in this module ###
#
# Dataclasses (used for the CU class):
# See the educational notes in assembler.py for a detailed explanation.
# In brief: dataclasses automatically generate __init__, __repr__, and other
# methods based on class attributes, reducing boilerplate code.
#
# Field with default_factory (appears in CU class):
# The `field(default_factory=dict)` pattern is used to provide mutable default
# values for dataclass attributes. Without default_factory, all instances would
# share the same mutable object, causing unexpected behavior.
# Example: components: dict[ComponentName, CPUComponent] = field(default_factory=dict)
# This ensures each CU instance gets its own empty dictionary.
#
# Lambda functions (appear in current_phase field):
# Lambda is Python's syntax for anonymous (unnamed) functions.
# Syntax: lambda arguments: expression
# Example: lambda: CYCLE_PHASES.__next__()
# This creates a function that takes no arguments and calls __next__() on
# CYCLE_PHASES. It's used as a default_factory to get the first phase.
#
# Type hints with union types (|):
# The | operator creates union types ("this OR that").
# Example: int | None means "either an integer or None".
# This is equivalent to Optional[int] from the typing module.
#
# Dictionary dispatch pattern (appears in execute_RTN_step):
# Instead of long if/elif chains, we use a dictionary to map types to handler
# functions. This is more concise and easier to extend.
# Example: dispatcher = {SimpleTransferStep: self._handle_simple_transfer, ...}
#         handler = dispatcher[type(step)]
#         handler(step)
# This looks up the handler function based on the step's type and calls it.


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
    ram_address: RAMAddress,
    ram_data: RAM,
    in_component: IO,
    out_component: IO,
) -> dict[ComponentName, CPUComponent]:
    """Bundle all CPU components into a dictionary for the Control Unit.

    This helper ensures the CU has references to every component it will control
    during instruction execution. By requiring all components as explicit
    parameters, we make the dependencies clear and prevent runtime errors from
    missing components.

    Args:
        mar: Memory Address Register.
        mdr: Memory Data Register.
        pc: Program Counter.
        cir: Current Instruction Register.
        acc: Accumulator.
        ix: Index Register.
        alu: Arithmetic Logic Unit.
        cmp_flag: Comparison flag for conditional jumps.
        address_bus: Address bus for RTN visualization.
        inner_data_bus: Internal data bus for RTN visualization.
        ram_address: RAM address component (receives MAR value).
        ram_data: RAM data component (reads/writes via MDR).
        in_component: Input device for IN instruction.
        out_component: Output device for OUT instruction.

    Returns:
        A dictionary mapping ComponentName to component instances, ready for
        the CU to use in RTN step execution.
    """
    components = {
        ComponentName.MAR: mar,
        ComponentName.MDR: mdr,
        ComponentName.PC: pc,
        ComponentName.CIR: cir,
        ComponentName.ACC: acc,
        ComponentName.IX: ix,
        ComponentName.ALU: alu,
        ComponentName.CMP_FLAG: cmp_flag,
        ComponentName.ADDRESS_BUS: address_bus,
        ComponentName.INNER_DATA_BUS: inner_data_bus,
        ComponentName.RAM_ADDRESS: ram_address,
        ComponentName.RAM_DATA: ram_data,
        ComponentName.IN: in_component,
        ComponentName.OUT: out_component,
    }
    return components


@dataclass
class CU(CPUComponent):
    """Control Unit that orchestrates the fetch-decode-execute cycle.

    The CU implements the classic von Neumann execution model as a sequence of
    micro-operations (RTN steps) grouped into three phases:
    1. FETCH: Load the next instruction from memory (PC → MAR → RAM → MDR → CIR).
    2. DECODE: Extract opcode and operand from the instruction word.
    3. EXECUTE: Perform the instruction-specific RTN sequence.

    Each RTN step represents a single control signal that coordinates component
    activity, such as "MAR ← PC" or "ACC ← ACC + MDR". The UI can step through
    these operations one at a time to visualize the CPU's internal data flow.

    Attributes:
        components: Dictionary mapping ComponentName to component instances. This
            provides the CU with access to all registers, buses, and other
            components it needs to execute RTN steps.
        name: The component's official name (always ComponentName.CU).
        binary_instruction: The raw 16-bit instruction word currently loaded.
        current_instruction: Binary string representation of the instruction
            (e.g., "00000111 00101010").
        stringified_instruction: Human-readable mnemonic form (e.g., "ADD #5").
        opcode: The 8-bit opcode extracted from the instruction (bits 15-8).
        operand: The 8-bit operand extracted from the instruction (bits 7-0).
        current_RTNStep: The RTN step being executed in this clock cycle.
        last_RTNStep: The RTN step executed in the previous clock cycle.
        RTN_sequence: List of RTN steps for the current phase.
        RTN_sequence_index: Current position in the RTN sequence.
        current_phase: Current phase of the fetch-decode-execute cycle.
    """  # See "Educational notes" at top of file for dataclass explanation

    components: dict[ComponentName, CPUComponent] = field(default_factory=dict)  # See "Educational notes" at top of file for field explanation
    name: ComponentName = ComponentName.CU

    # Instruction state
    binary_instruction: int | None = None  # See "Educational notes" at top of file for union type explanation
    current_instruction: int | None = None
    stringified_instruction: str | None = None
    opcode: int | None = None
    operand: int | None = None

    # RTN execution state
    current_RTNStep: RTNStep | None = None
    last_RTNStep: RTNStep | None = None
    RTN_sequence: list[RTNStep] = field(default_factory=list)
    RTN_sequence_index: int = 0
    current_phase: CyclePhase = field(default_factory=lambda: CYCLE_PHASES.__next__())  # See "Educational notes" at top of file for lambda explanation

    def __post_init__(self):
        """Validate that all required components are present after initialization.

        This method runs automatically after the dataclass __init__ completes.
        It checks that the components dictionary contains every ComponentName
        that RTN steps will reference, except for CU (which is self) and OPERAND
        (which is a pseudo-component representing register-index operands).

        Raises:
            MissingComponentError: If any required component is missing from the
                components dictionary.
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
        """Convert the current operand to a human-readable string.

        This handles three cases:
        1. Long operands: display the value from MDR (fetched in previous phase).
        2. Register-index operands: display the register name (e.g., "ACC").
        3. Regular operands: display the raw numeric value.

        Returns:
            A string representation of the operand suitable for UI display.
        """
        # If no instruction is loaded yet, return a placeholder.
        if self.opcode is None:
            return "None"

        # For long-operand instructions, the operand is in MDR (not in the CU).
        instruction_def = self.get_instruction_definition(self.opcode)
        if instruction_def and instruction_def.long_operand:
            return str(self.components[ComponentName.MDR].read())
            # return early, so every case below is for short operands only

        # Check if the operand is a register index (used by MOV, INC, DEC).
        for key, value in RegisterIndex.items():
            if value == self.operand:
                return key.name

        # Otherwise, just return the raw operand value.
        return str(self.operand)

    def read(self) -> int:
        """Read the CU's current operand value.

        Returns:
            The operand value, or 0 if no instruction is loaded.
        """
        if self.operand is None:
            return 0
        else:
            return self.operand

    def write(self, data: int) -> None:
        """Write a new instruction into the CU and decode it.

        This is called during the DECODE phase when the CIR is loaded.

        Args:
            data: The 16-bit instruction word to decode.
        """
        self.binary_instruction = data
        self.set_instruction(data)
        self._update_display()

    def compute_opcode(self, binary_instruction: int) -> int:
        """Extract the opcode from a binary instruction word.

        CIE 9618 curriculum doesn't say anything about word length.
        Here we chose 16 bits for simplicity, but most mordern CPUs
        use 32 or 64 bits (with more complex encoding schemes).

        Args:
            binary_instruction: The 16-bit instruction word.

        Returns:
            The 8-bit opcode (bits 15-8).
        """
        # Right-shift by 8 bits to move the opcode into the low byte.
        return binary_instruction >> 8

    def get_instruction_definition(self, opcode: int):
        """Look up the instruction definition for a given opcode.

        Args:
            opcode: The 8-bit opcode to look up.

        Returns:
            The instruction definition from the instruction set.

        Raises:
            ValueError: If the opcode is not recognized.
        """
        definition = instruction_set.get(opcode)
        if not definition:
            raise ValueError(f"Invalid opcode: {opcode}")
        return definition

    def set_instruction(self, instruction: int) -> None:
        """Decode an instruction word into opcode and operand.

        This method splits the 16-bit instruction into its opcode (high byte)
        and operand (low byte). For long-operand instructions, it sets up the
        RTN sequence to fetch the full operand from the next memory location.

        Args:
            instruction: The 16-bit instruction word to decode.
        """
        # Extract opcode (bits 15-8) and operand (bits 7-0).
        self.opcode = self.compute_opcode(instruction)
        self.operand = instruction & 0b0000000011111111  # Mask to get low 8 bits

        # Create a binary string for debugging/display.
        self.current_instruction = instruction

        # Check if this instruction needs a long operand fetch.
        instruction_def = self.get_instruction_definition(self.opcode)
        if instruction_def and instruction_def.long_operand:
            # Long instructions need an extra memory access to fetch the full
            # 16-bit operand from the next memory location.
            self.stringified_instruction = self.stringify_instruction()
            self.RTN_sequence = FETCH_LONG_OPERAND_RTNSteps
        else:
            # Short instructions have the operand embedded in the low byte.
            pass
        self._update_display()

    def print_instruction(self) -> None:
        """Print the current instruction in mnemonic form to the console.

        This is a debugging helper that outputs the human-readable instruction
        (e.g., "ADD #5") to stdout. It was used during development to verify correct
        instruction decoding.
        """
        print(self.stringify_instruction())

    def stringify_instruction(self) -> str:
        """Convert the current instruction to mnemonic form.

        This creates a human-readable representation of the instruction, such as
        "LDD #100" or "JMP LOOP". During the EXECUTE phase, long operands are
        resolved from MDR; before that, they show as "..." placeholders.

        Returns:
            A string containing the mnemonic and operand (e.g., "ADD #5").
        """
        if self.opcode is None:
            return "None"

        instruction_def = self.get_instruction_definition(self.opcode)
        mnemonic = instruction_def.mnemonic

        # Determine how to display the operand.
        if not instruction_def.long_operand:
            # Short operand: display immediately.
            operand = self.stringify_operand()
        elif self.current_phase != CyclePhase.EXECUTE:
            # Long operand not yet fetched: show placeholder.
            operand = "..."
        else:
            # Long operand fetched: display from MDR.
            operand = self.components[ComponentName.MDR].read()

        return f"{mnemonic} {operand}"  # type: ignore (some type checkers complain here)

    def enter_phase(self, phase: CyclePhase) -> None:
        """Transition to a new phase of the fetch-decode-execute cycle.

        This method resets the RTN sequence index and loads the appropriate RTN
        sequence for the new phase (FETCH, DECODE, or EXECUTE).

        Args:
            phase: The cycle phase to enter.
        """
        # Reset to the start of the new RTN sequence.
        self.RTN_sequence_index = 0

        if phase == CyclePhase.FETCH:
            # FETCH: Load the next instruction from memory. The steps are always
            # the same, and are defined in common/constants.py as FETCH_RTNSteps.
            # RTN sequence: MAR ← PC, PC ← PC + 1, RAM read, CIR → MDR.
            self.stringified_instruction = "Fetching..."
            self.RTN_sequence = FETCH_RTNSteps
        elif phase == CyclePhase.DECODE:
            # DECODE: Extract opcode and operand from the instruction word.
            # The first step is always the same (CIR → CU), and eventual long-
            # operand fetches are handled by set_instruction().
            # RTN sequence: CIR → CU (decode opcode and operand).
            self.stringified_instruction = "Decoding..."
            self.RTN_sequence = DECODE_RTNSteps
        elif phase == CyclePhase.EXECUTE:
            # EXECUTE: Perform the instruction-specific operations.
            # RTN sequence: Varies by instruction (defined in instruction_set).
            self.stringified_instruction = self.stringify_instruction()
            if self.opcode is None:
                raise ValueError("Cannot enter EXECUTE phase without a valid opcode.")
            self.print_instruction()
            instruction_def = self.get_instruction_definition(self.opcode)
            if instruction_def:
                if instruction_def.mnemonic == "END":
                    # END instruction has no RTN steps; it just halts.
                    self.RTN_sequence = []
                    return
                else:
                    # Load the instruction-specific RTN sequence.
                    self.RTN_sequence = instruction_def.rtn_sequence
            else:
                self.RTN_sequence = []
                return

        # Prepare the first step for display (but don't execute it yet).
        # Execution happens in step_cycle() to keep UI synchronized.
        if self.RTN_sequence:
            self.current_RTNStep = self.RTN_sequence[0]
        else:
            self.current_RTNStep = None

    def step_RTNSeries(self) -> bool:
        """Execute one RTN step from the current sequence.

        This method advances through the RTN sequence one step at a time,
        executing each micro-operation and updating the sequence index. It does
        NOT change the CPU phase; phase transitions are handled in step_cycle().

        Returns:
            True if the RTN sequence has been fully executed, False otherwise.
        """
        # Empty sequence means nothing to execute.
        if not self.RTN_sequence:
            self.current_RTNStep = None
            return True

        # Already finished this sequence.
        if self.RTN_sequence_index >= len(self.RTN_sequence):
            self.current_RTNStep = None
            return True

        # Execute the current step and advance the index.
        self.current_RTNStep = self.RTN_sequence[self.RTN_sequence_index]
        self.execute_RTN_step(self.current_RTNStep)
        self.last_RTNStep = self.current_RTNStep
        self.RTN_sequence_index += 1
        self._update_display()

        # Check if we've finished the sequence.
        return self.RTN_sequence_index >= len(self.RTN_sequence)

    def step_cycle(self) -> bool:
        """Advance the CPU by one visible micro-operation.

        This is the main entry point for stepping through execution. It handles:
        1. Phase transitions when RTN sequences complete.
        2. Executing one RTN step from the current phase.
        3. Keeping the UI synchronized by transitioning phases BEFORE execution.

        The key insight: phase changes happen at the START of a tick, not the end.
        This ensures the CU display shows the same phase that's actually executing.

        Returns:
            True if the program has finished (END instruction or empty sequence),
            False if execution should continue.
        """
        # Empty sequence means the program has ended.
        if not self.RTN_sequence:
            self.current_RTNStep = None
            self._update_display()
            return True

        # If we finished the previous phase's sequence, transition to the next phase.
        if self.RTN_sequence_index >= len(self.RTN_sequence):
            self.current_phase = CYCLE_PHASES.__next__()
            self.enter_phase(self.current_phase)

            # Check again after phase transition (END instruction has empty sequence).
            if not self.RTN_sequence:
                self.current_RTNStep = None
                self._update_display()
                return True

        # Execute one RTN step from the (possibly new) phase.
        self.step_RTNSeries()
        return False

    def execute_RTN_step(self, step: RTNStep, reset_active: bool = True) -> None:
        """Execute a single RTN step by dispatching to the appropriate handler.

        This method uses the dictionary dispatch pattern (see educational notes)
        to route each RTN step type to its specialized handler. Before executing,
        it resets all components' active flags so the UI can highlight only the
        components involved in this specific step.

        Args:
            step: The RTN step to execute (SimpleTransferStep, ALUOperationStep, etc.).
            reset_active: Whether to reset all components' active flags before
                executing. Set to False when chaining multiple sub-steps.
        """  
        # See "Educational notes" at top of file for dictionary dispatch explanation
        # Reset all components to inactive so the UI highlights only the
        # components involved in this specific RTN step.
        if reset_active:
            for component in self.components.values():
                component.set_last_active(False)
        # The CU is always active (it's orchestrating the step).
        self.set_last_active(True)

        # Dispatch to the appropriate handler based on the step's type.
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
        """Check if a conditional transfer should execute.

        Args:
            condition: The expected state of the comparison flag.

        Returns:
            True if the comparison flag matches the expected condition.
        """
        # The CMP flag is set by the ALU during CMP instruction execution.
        cmp_flag = self.components[ComponentName.CMP_FLAG]
        return condition == cmp_flag.read()

    def _get_dest(self, destination: ComponentName) -> CPUComponent:
        """Resolve a destination ComponentName to an actual component instance.

        Some instructions (MOV, INC, DEC) use the operand as a register index,
        which requires looking up the actual register by its index value.

        Args:
            destination: The destination component name, possibly OPERAND.

        Returns:
            The resolved component instance.

        Raises:
            ValueError: If the operand is not set or contains an invalid register index.
        """
        # Most destinations are direct component references.
        if destination != ComponentName.OPERAND:
            return self.components[destination]
        else:
            # OPERAND means "the register indexed by the operand value".
            if self.operand is None:
                raise ValueError(
                    "Operand is not set; cannot determine destination register."
                )
            reg_index = self.operand
            # Look up the register name from the index.
            for key, value in RegisterIndex.items():
                if value == reg_index:
                    destination = key
                    break
            if not destination:
                raise ValueError(f"Invalid register index in operand: {reg_index}")
            return self.components[destination]

    def _resolve_destination_name(self, destination: ComponentName) -> ComponentName:
        """Resolve OPERAND pseudo-name into the actual ComponentName.

        This is similar to _get_dest() but returns the name instead of the
        component instance. Used for UI visualization of bus connections.

        Args:
            destination: The destination component name, possibly OPERAND.

        Returns:
            The resolved ComponentName.

        Raises:
            ValueError: If the operand is not set or contains an invalid register index.
        """
        # Most destinations are already explicit component names.
        if destination != ComponentName.OPERAND:
            return destination

        # Resolve OPERAND to the actual register name.
        if self.operand is None:
            raise ValueError("Operand is not set; cannot determine destination register.")
        reg_index = self.operand
        for key, value in RegisterIndex.items():
            if value == reg_index:
                return key
        raise ValueError(f"Invalid register index in operand: {reg_index}")
        
    def _handle_simple_transfer(self, step: SimpleTransferStep) -> None:
        """Execute a simple register transfer (source → destination).

        This implements the most common RTN operation: copying data from one
        component to another via the internal data bus. Examples: "MAR ← PC",
        "ACC ← MDR", "CIR ← MDR".

        Args:
            step: The SimpleTransferStep specifying source and destination.
        """
        # Read from the source component.
        source_comp = self.components[step.source]
        source_comp.set_last_active(True)

        # Resolve the destination (handles OPERAND pseudo-name).
        dest_name = self._resolve_destination_name(step.destination)
        dest_comp = self.components[dest_name]
        dest_comp.set_last_active(True)

        # Mark the bus as active for UI visualization.
        bus = self.components[ComponentName.INNER_DATA_BUS]
        bus.set_last_active(True)

        # Record the bus connection for UI drawing.
        bus.set_last_connections([(step.source, dest_name)])  # type: ignore[attr-defined]

        # Perform the actual data transfer.
        data = source_comp.read()
        dest_comp.write(data)

    def _handle_conditional_transfer(self, step: ConditionalTransferStep) -> None:
        """Execute a conditional register transfer (if condition then source → dest).

        This implements conditional jumps (JPN, JPE) by checking the comparison
        flag before performing the transfer.

        The architecture defined in the curriculum only uses conditional transfers
        for jump instructions, but this handler could be extended for other uses.
        We chose to implement it that way because it was easier to reuse existing
        transfert logic.

        Args:
            step: The ConditionalTransferStep specifying condition, source, and dest.
        """
        condition_met = self._evaluate_condition(step.condition)
        if condition_met:
            # Condition is true; perform the transfer.
            self._handle_simple_transfer(
                SimpleTransferStep(source=step.source, destination=step.destination)
            )

    def _handle_memory_access(self, step: MemoryAccessStep) -> None:
        """Execute a memory read or write operation.

        Memory access in this architecture is a two-step process:
        1. Address phase: MAR → memory address bus.
        2. Data phase: MDR ↔ memory data (read or write).

        Args:
            step: The MemoryAccessStep specifying address vs data phase and
                read vs write control signal.
        """
        if step.is_address:
            # Step 1: Send the address from MAR to RAM's address register.
            mar = self.components[ComponentName.MAR]
            mar.set_last_active(True)
            ram_address = self.components[ComponentName.RAM_ADDRESS]
            ram_address.set_last_active(True)
            bus = self.components[ComponentName.ADDRESS_BUS]
            bus.set_last_active(True)

            # Record bus connection for UI visualization.
            bus.set_last_connections([(ComponentName.MAR, ComponentName.RAM_ADDRESS)])  # type: ignore[attr-defined]

            # Transfer the address.
            address = mar.read()
            ram_address.write(address)
        else:
            # Step 2: Transfer data between MDR and RAM.
            bus = self.components[ComponentName.ADDRESS_BUS]
            bus.set_last_active(True)

            if step.control == ControlSignal.WRITE:
                # Memory write: MDR → RAM.
                ram_data = self.components[ComponentName.RAM_DATA]
                ram_data.set_last_active(True)
                mdr = self.components[ComponentName.MDR]
                mdr.set_last_active(True)

                bus.set_last_connections([(ComponentName.MDR, ComponentName.RAM_DATA)])  # type: ignore[attr-defined]

                data = mdr.read()
                ram_data.write(data)
            else:
                # Memory read: RAM → MDR.
                mdr = self.components[ComponentName.MDR]
                mdr.set_last_active(True)
                ram_data = self.components[ComponentName.RAM_DATA]
                ram_data.set_last_active(True)

                bus.set_last_connections([(ComponentName.RAM_DATA, ComponentName.MDR)])  # type: ignore[attr-defined]

                data = ram_data.read()
                mdr.write(data)

    def _handle_alu_operation(self, step: ALUOperationStep) -> None:
        """Execute an ALU operation (arithmetic or logic).

        ALU operations combine the accumulator with another value (from a register
        or immediate operand) and store the result back in the accumulator. The
        ALU also updates the comparison flag for CMP instructions.

        Args:
            step: The ALUOperationStep specifying the operation and source operand.
        """
        # Get the ALU and accumulator.
        alu: ALU = self.components[ComponentName.ALU]  # type: ignore Generic type 'CPUComponent' has no attribute 'set_operands', but ALU does.
        alu.set_last_active(True)
        acc = self.components[ComponentName.ACC]
        acc.set_last_active(True)

        # Get the source operand (register or immediate value).
        source_comp = self.components[step.source]
        source_comp.set_last_active(True)

        # Mark the inner bus as active for UI visualization.
        inner_bus: Bus = self.components[ComponentName.INNER_DATA_BUS]  # type: ignore[assignment]
        inner_bus.set_last_active(True)
        # Show both ACC and the source feeding into the ALU.
        inner_bus.set_last_connections(
            [(ComponentName.ACC, ComponentName.ALU), (step.source, ComponentName.ALU)]
        )

        # Perform the ALU operation.
        alu.set_operands(acc.read(), source_comp.read())
        alu.set_mode(step.control)
        alu.compute()

    def _handle_reg_operation(self, step: RegOperationStep) -> None:
        """Execute a register increment or decrement operation.

        This handles INC and DEC instructions, which modify a register's value
        by adding or subtracting an offset (usually 1, but can be sourced from
        another register).

        Args:
            step: The RegOperationStep specifying INC/DEC, destination, and optional source.
        """
        # Get the target register (may be indexed via operand).
        reg_comp : Register = self._get_dest(step.destination) # type: ignore _get_dest return a generic CPUComponent, but here we know it's a Register
        reg_comp.set_last_active(True)

        # Determine the offset (default 1, or value from source register).
        offset = 1
        if step.source:
            source_comp : Register = self.components[step.source] # type: ignore _get_dest return a generic CPUComponent, but here we know it's a Register
            source_comp.set_last_active(True)
            offset = source_comp.read()

        # Perform the operation.
        if step.control == ControlSignal.INC:
            reg_comp.inc(offset)
        elif step.control == ControlSignal.DEC:
            reg_comp.dec(offset)

    def __repr__(self) -> str:
        """Return a string representation of the CU state for debugging.

        Returns:
            A formatted string showing the current instruction, opcode, operand,
            and RTN step.
        """
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
