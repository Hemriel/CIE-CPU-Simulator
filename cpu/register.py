"""Register implementation for the CIE CPU simulator, tracking value and control state."""

from dataclasses import dataclass
from constants import WORD_SIZE, ControlSignal
from component import CPUComponent


@dataclass
class Register(CPUComponent):
    """A general-purpose register with control signal tracking for RTN visualization.

    Attributes:
        _control: The current ControlSignal asserted for this register or None when idle.
        _value: The stored word-sized integer value that wraps around when it overflows.
    """

    _control: ControlSignal | None = None
    _value: int = 0

    def _set_value(self, value: int):
        """Clamp the provided integer to WORD_SIZE bits and refresh the UI feedback."""
        self._value = value % (1 << WORD_SIZE)  # Register width enforcement.
        self._update_display()

    def _set_control(self, control: ControlSignal | None):
        """Update the held control signal and refresh the visual display."""
        self._control = control
        self._update_display()

    def inc(self):
        """Increment the register by one and show the INC control signal."""
        self._set_value(self._value + 1)
        self._set_control(ControlSignal.INC)

    def dec(self):
        """Decrement the register by one and show the DEC control signal."""
        self._set_value(self._value - 1)
        self._set_control(ControlSignal.DEC)

    def write(self, value: int):
        """Store a provided integer and assert the WRITE control signal."""
        self._set_value(value)
        self._set_control(ControlSignal.WRITE)

    def read(self) -> int:
        """Assert the READ control signal and return the stored value."""
        self._set_control(ControlSignal.READ)
        return self._value

    def reset_control(self):
        """Clear any active control signal so the register appears idle."""
        self._set_control(None)
        self._update_display()
