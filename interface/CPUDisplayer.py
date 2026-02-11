"""Top-level CPU display layout and widget orchestration.

Responsibility:
- Composes all individual CPU component displays (registers, ALU, CU, buses,
  RAM, I/O) into a unified spatial layout.
- Manages the wiring between backend CPU components and frontend display widgets
  (establishes the front-end/back-end decoupling).
- Provides centralized refresh coordination for all display components.

Entry point:
- The :class:`CPUDisplay` class, which creates and arranges all display widgets
  in a Textual Horizontal layout with five vertical columns:
  1. Control column (CU, I/O, ALU)
  2. Internal bus column
  3. Register column (MAR, MDR, PC, CIR, ACC, IX)
  4. External bus column
  5. RAM column

Design note:
- This is the orchestration layer that brings together all the individual display
  components. It knows about the CPU's physical layout and arranges widgets
  spatially to reflect the conceptual CPU architecture.
- The endpoint mapping (ComponentName → widget) is key: it allows bus displays
  to dynamically find their source/destination widgets for ASCII art rendering.
- Wiring happens in two directions:
  * Backend → Frontend: CPU components hold displayer references for update hooks.
  * Frontend → Backend: Display widgets hold component references for state reading.
"""
from cpu.cpu import CPU

# Textual-specific imports. For more information, see https://textual.textualize.io/
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget

from interface.alu_display import ALUDisplay
from interface.control_unit_display import ControlUnitDisplay
from interface.internal_bus_display import InternalBusDisplay
from interface.outer_bus_display import OuterBusDisplay
from interface.register_display import RegisterDisplay
from interface.IO_display import IODisplay
from interface.ram_display import RAMAddressDisplay, RAMDataDisplay
from interface.vspacer import VSpacer

from common.constants import ComponentName, DisplayMode


class CPUDisplay(Widget):
    """Orchestrate and layout all CPU component displays.
    
    This widget is the root of the entire CPU visualization. It creates display
    widgets for every CPU component (registers, ALU, CU, buses, RAM, I/O),
    arranges them in a five-column spatial layout that mirrors the conceptual
    CPU architecture, and wires them to their backend components.
    
    The layout follows this structure:
    [Control] [Inner Bus] [Registers] [Outer Bus] [RAM]
    
    Key responsibilities:
    - Create all display widgets and pass them their backend component references.
    - Build the endpoint mapping (ComponentName → widget) for bus rendering.
    - Wire backend components to their display widgets (establishes update hooks).
    - Provide centralized refresh for all displays.
    
    Attributes:
        cpu: The CPU being visualized.
        control_display: CU instruction/step display.
        input_display: Input I/O port display.
        output_display: Output I/O port display.
        alu_display: ALU operands/result/flag display.
        register_displays: List of register displays (MAR, MDR, PC, CIR, ACC, IX).
        ram_address_display: RAM address header display.
        ram_data_display: RAM data table display.
        inner_bus_display: Internal data bus visualization.
        address_bus_display: External bus visualization.
        _endpoints: Mapping of ComponentName to widget for bus rendering.
        _displayers: List of all display widgets for refresh coordination.
    """

    def __init__(self, cpu: CPU) -> None:
        """Initialize the CPU display with all component widgets.
        
        This method:
        1. Creates display widgets for all CPU components.
        2. Builds the endpoint mapping (ComponentName → widget) for bus rendering.
        3. Creates bus displays (which depend on the endpoint mapping).
        4. Wires backend components to frontend displays.
        
        Args:
            cpu: The CPU instance to visualize.
        """
        super().__init__()
        self.cpu = cpu
        
        # Create display widgets for major components.
        self.control_display = ControlUnitDisplay(cpu.cu)
        
        # I/O displays: reversed=True for input shows data flowing right-to-left.
        self.input_display = IODisplay(cpu.io_in, "Input-Port", reversed=True)
        self.input_display.add_class("inactive")  # Start inactive until IN instruction.
        self.output_display = IODisplay(cpu.io_out, "Output-Port")
        self.output_display.add_class("inactive")  # Start inactive until OUT instruction.
        
        self.alu_display = ALUDisplay(cpu.alu)
        
        # Create display widgets for all registers in order of their typical usage.
        self.register_displays = [
            RegisterDisplay(cpu.mar, "MAR"),
            RegisterDisplay(cpu.mdr, "MDR"),
            RegisterDisplay(cpu.pc, "PC"),
            RegisterDisplay(cpu.cir, "CIR"),
            RegisterDisplay(cpu.acc, "ACC"),
            RegisterDisplay(cpu.ix, "IX"),
        ]
        
        self.ram_address_display = RAMAddressDisplay(cpu.ram)
        self.ram_data_display = RAMDataDisplay(cpu.ram)

        # Build endpoint lookup table for bus wiring.
        # This mapping allows bus displays to find source/destination widgets
        # by component name, enabling dynamic ASCII art rendering.
        self._endpoints: dict[ComponentName, object] = {
            ComponentName.CU: self.control_display,
            ComponentName.ALU: self.alu_display,
            ComponentName.IN: self.input_display,
            ComponentName.OUT: self.output_display,
            ComponentName.RAM_ADDRESS: self.ram_address_display,
            ComponentName.RAM_DATA: self.ram_data_display,
        }
        
        # Add register displays to the endpoint mapping.
        # RegisterDisplay.id is the name string (e.g. "MAR").
        for display in self.register_displays:
            if display.id:
                try:
                    self._endpoints[ComponentName(str(display.id))] = display
                except Exception:
                    pass  # Skip invalid component names.

        # Create bus displays last since they depend on the endpoint mapping.
        self.inner_bus_display = InternalBusDisplay(cpu.inner_data_bus, self._endpoints)
        self.address_bus_display = OuterBusDisplay(
            cpu.address_bus, title="Outer-Bus", endpoints=self._endpoints
        )
        
        # Collect all displayers for refresh coordination.
        self._displayers = [
            self.control_display,
            self.input_display,
            self.output_display,
            self.alu_display,
            self.inner_bus_display,
            self.address_bus_display,
            self.ram_address_display,
            self.ram_data_display,
            *self.register_displays,
        ]
        
        # Wire backend components to frontend displays.
        self._wire_components()

    def _wire_components(self) -> None:
        """Wire backend CPU components to their frontend display widgets.
        
        This establishes the front-end/back-end connection by giving each CPU
        component a reference to its display widget. When the component's state
        changes, it can call displayer.update_display() to refresh the UI.
        
        This bidirectional wiring is key to the architecture:
        - Backend holds displayer reference (for triggering updates).
        - Frontend holds component reference (for reading state).
        """
        # Wire major components.
        self.cpu.cu.displayer = self.control_display
        self.cpu.io_in.displayer = self.input_display
        self.cpu.io_out.displayer = self.output_display
        self.cpu.alu.displayer = self.alu_display
        self.cpu.inner_data_bus.displayer = self.inner_bus_display
        self.cpu.address_bus.displayer = self.address_bus_display
        self.cpu.ram_address.displayer = self.ram_address_display
        self.cpu.ram.displayer = self.ram_data_display
        
        # Wire registers in the same order they were created.
        for register, display in zip(
            [
                self.cpu.mar,
                self.cpu.mdr,
                self.cpu.pc,
                self.cpu.cir,
                self.cpu.acc,
                self.cpu.ix,
            ],
            self.register_displays,
        ):
            register.displayer = display

    def compose(self) -> ComposeResult:
        """Compose the CPU layout with all component displays.
        
        This method defines the spatial arrangement of all CPU component displays
        in a five-column layout that mirrors the conceptual CPU architecture:
        
        1. Control column (left): CU, I/O ports, ALU (control/data processing).
        2. Internal bus column: Shows data transfers within the CPU.
        3. Register column (center): All registers (MAR, MDR, PC, CIR, ACC, IX).
        4. External bus column: Shows address/data transfers to RAM.
        5. RAM column (right): RAM address and data display.
        
        VSpacer widgets provide vertical spacing for visual balance.
        
        Returns:
            A ComposeResult with the complete CPU layout structure.
        """
        with Horizontal(id="cpu-layout"):
            # Column 1: Control components (CU, I/O, ALU).
            with Vertical(id="control-column"):
                yield VSpacer()
                yield self.control_display
                yield VSpacer()
                yield self.input_display
                yield VSpacer()
                yield self.output_display
                yield VSpacer()
                yield self.alu_display
                yield VSpacer()
            
            # Column 2: Internal data bus.
            with Vertical(id="inner-bus-column"):
                yield self.inner_bus_display
            
            # Column 3: Register bank.
            with Vertical(id="register-column"):
                for register_widget in self.register_displays:
                    yield VSpacer()
                    yield register_widget
                yield VSpacer()
            
            # Column 4: External buses (address and data).
            with Vertical(id="outer-bus-column"):
                yield self.address_bus_display
            
            # Column 5: RAM.
            with Vertical(id="ram-column"):
                yield self.ram_address_display
                yield self.ram_data_display

    def refresh_all(self) -> None:
        """Refresh all display widgets to reflect current CPU state.
        
        This method provides centralized refresh coordination. It's called after
        each CPU operation to ensure all displays are in sync with the backend
        component states.
        """
        for displayer in self._displayers:
            displayer.update_display()

    def set_number_display_mode(self, mode: DisplayMode) -> None:
        """Set the number display mode for all relevant components.
        
        Args:
            mode: One of "decimal", "hexadecimal", or "binary"
        """
        for displayer in self._displayers:
            if hasattr(displayer, "set_number_display_mode"):
                displayer.set_number_display_mode(mode)