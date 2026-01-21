# CPU-wide display built by composing individual widgets for each hardware component.

from cpu.cpu import CPU

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


class CPUDisplay(Widget):
	"""Layout the CPU interface widgets in their rough spatial arrangement."""

	def __init__(self, cpu: CPU) -> None:
		super().__init__()
		self.cpu = cpu
		self.control_display = ControlUnitDisplay(cpu.cu)
		self.input_display = IODisplay(cpu.io_in, "Input Port")
		self.output_display = IODisplay(cpu.io_out, "Output Port")
		self.alu_display = ALUDisplay(cpu.alu)
		self.inner_bus_display = InternalBusDisplay(cpu.inner_data_bus)
		self.address_bus_display = OuterBusDisplay(
			cpu.address_bus, title="Address Bus", color="gold1"
		)
		self.outer_data_bus_display = OuterBusDisplay(
			cpu.outer_data_bus, title="RAM Data Bus", color="white"
		)
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
		self._displayers = [
			self.control_display,
			self.input_display,
			self.output_display,
			self.alu_display,
			self.inner_bus_display,
			self.address_bus_display,
			self.outer_data_bus_display,
			self.ram_address_display,
			self.ram_data_display,
			*self.register_displays,
		]
		self._wire_components()

	def _wire_components(self) -> None:
		self.cpu.cu.displayer = self.control_display
		self.cpu.io_in.displayer = self.input_display
		self.cpu.io_out.displayer = self.output_display
		self.cpu.alu.displayer = self.alu_display
		self.cpu.inner_data_bus.displayer = self.inner_bus_display
		self.cpu.address_bus.displayer = self.address_bus_display
		self.cpu.outer_data_bus.displayer = self.outer_data_bus_display
		self.cpu.ram_address.displayer = self.ram_address_display
		self.cpu.ram.displayer = self.ram_data_display
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
		with Horizontal(id="cpu-layout"):
			with Vertical(id="control-column"):
				yield self.control_display
				yield self.input_display
				yield self.output_display
				yield self.alu_display
			with Vertical(id="inner-bus-column"):
				yield self.inner_bus_display
			with Vertical(id="register-column"):
				for register_widget in self.register_displays:
					yield register_widget
			with Vertical(id="outer-bus-column"):
				yield self.address_bus_display
				yield self.outer_data_bus_display
			with Vertical(id="ram-column"):
				yield self.ram_address_display
				yield self.ram_data_display

	def refresh_all(self) -> None:
		for displayer in self._displayers:
			displayer.update_display()
