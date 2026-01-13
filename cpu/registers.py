from dataclasses import dataclass
from typing import Protocol
from constants import ComponentNames, WORD_SIZE, ControlSignals


class RegisterDisplayer(Protocol):
    def update_display(self) -> None: ...


@dataclass
class register:
    name: ComponentNames
    displayer: RegisterDisplayer | None = None
    _control: ControlSignals | None = None
    _value: int = 0

    def _update_display(self):
        if self.displayer:
            self.displayer.update_display()

    def _set_value(self, value: int):
        self._value = value % (1 << WORD_SIZE)  # Ensure value fits in register size
        self._update_display()

    def _set_control(self, control: ControlSignals | None):
        self._control = control
        self._update_display()

    def inc(self):
        self._set_value(self._value + 1)
        self._set_control(ControlSignals.WRITE)

    def dec(self):
        self._set_value(self._value - 1)
        self._set_control(ControlSignals.WRITE)

    def write(self, value: int):
        self._set_value(value)
        self._set_control(ControlSignals.WRITE)

    def read(self) -> int:
        self._set_control(ControlSignals.READ)
        return self._value

    def reset_control(self):
        self._set_control(None)
        self._update_display()
