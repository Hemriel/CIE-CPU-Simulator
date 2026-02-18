"""Register implementation for the CIE CPU simulator with RTN control signal visualization.

Responsibility:
- Implement general-purpose and special-purpose registers that store word-sized
  integer values and track active control signals for visualization.
- Enforce word size constraints (16-bit masking) to match the simulated CPU architecture.
- Support increment/decrement operations and read/write operations while displaying
  which control signals are active.

Illustrates:
- CIE 9618: 4.1 Central Processing Unit (CPU) Architecture:
    - Show understanding of the purpose and roles of registers, including the difference
      between general and special purpose registers.
    - Show understanding of how data are transferred between various components using
      control signals and buses.
    - Describe the stages of the fetch-decode-execute cycle (registers change during execution).
- CIE 9618: 9.1 Computational Thinking Skills:
    - Show an understanding of abstraction (registers as abstractions of hardware storage).
- CIE 9618: 13.1 User-defined data types (deeper than intended by curriculum):
    - Show understanding of why user-defined data types are necessary (Register encapsulates
      value, control state, and display coordination).
    - Chose and define an appropriate user-defined data type for a given problem.
- CIE 9618: 20.1 Programming paradigms:
    - Show understanding of the characteristics of Object-Oriented Programming (Register class
      encapsulates data and behavior).

Design notes:
- Each register tracks both its stored value and the control signal that most recently
  affected it. This allows the UI to highlight which operation (READ, WRITE, INC, DEC)
  is being executed during each RTN step.
- Values are automatically masked to WORD_SIZE (16 bits) to simulate hardware word width
  enforcement. Overflow is handled via modulo arithmetic.
- The separation of _set_value, _set_control, and _update_display provides clear
  layering: data changes, control changes, and UI updates are distinct operations.
- All operations update the display immediately, keeping the UI synchronized with
  register state throughout the fetch-decode-execute cycle.

Entry points:
- :class:`Register`: The main register class, instantiated for PC, MAR, MDR, CIR, ACC, IX.

Includes:
- :class:`Register`: General and special-purpose register implementation.

Educational intent:
Students can observe how registers are active components in the CPU: not just passive
storage, but participants in the fetch-decode-execute cycle. The tracking of control
signals shows students exactly when and how registers are accessed during execution.
"""

from dataclasses import dataclass
from common.constants import WORD_SIZE, ComponentName, ControlSignal
from simulator.component import CPUComponent


### Educational notes on Python operations used in this module ###
#
# Dataclasses (Register class):
# Data classes are NOT in the curriculum.
# Here is a detailed explanation: https://docs.python.org/3/library/dataclasses.html
# In a few words, they are a concise way to define classes that mainly store
# data attributes. The __init__, __repr__, __eq__, and other methods are
# automatically generated based on the class attributes.
#
# Bitwise left shift (1 << WORD_SIZE):
# The << operator shifts bits to the left. "1 << 16" means "shift the binary 1
# sixteen positions to the left," which results in the value 65536 (2^16).
# We use this to calculate the maximum value that fits in WORD_SIZE bits.
# The modulo operator (%) then wraps values larger than this maximum back into range.
# Although bitwise operations are not in the curriculum, bit shifting is part of
# CIE 9618: 4.3 Bit Manipulation, so students should understand the concept.
#
# Type hints with union types (|):
# The | operator creates union types ("this OR that").
# Example: ControlSignal | None means "either a ControlSignal or None".
# This indicates that a control signal may be present (when the register is active)
# or absent (None, when the register is idle). It's equivalent to Optional[ControlSignal].


@dataclass
class Register(CPUComponent):
    """A CPU register with value storage and control signal tracking for RTN visualization.

    This class models both general-purpose registers (ACC, IX) and special-purpose
    registers (PC, MAR, MDR, CIR) as defined in CIE 9618. Each register stores a
    word-sized value and tracks which control signal most recently affected it,
    enabling the UI to visualize the fetch-decode-execute cycle in real time.

    The register enforces word size constraints automatically: all stored values are
    masked to 16 bits (0-65535). When an operation would overflow (e.g., incrementing
    65535), the value wraps around using modulo arithmetic, matching real hardware behavior.

    Control signal tracking makes the RTN sequence explicit: when the UI displays
    this register, it can show not just the current value but also which operation
    (READ, WRITE, INC, DEC) is active, connecting the code execution to CIE's
    Register Transfer Notation.

    Attributes:
        name: The register identifier (from ComponentName enum, e.g., ComponentName.PC).
        _control: The most recent ControlSignal asserted on this register, or None when idle.
            Updated during read/write/inc/dec operations to show which RTN step is active.
        _value: The stored word-sized value (0 to 65535). Automatically masked to 16 bits
            whenever modified to enforce word size constraints.
        last_active: Whether this component participated in the last RTN step (inherited).
        displayer: Optional UI component to refresh on state changes (inherited).
    """

    name: ComponentName
    _control: ControlSignal | None = None
    _value: int = 0

    def _set_value(self, value: int):
        """Update the register value and enforce word size constraints.

        This method is called internally whenever the register's stored value changes
        (via write, inc, dec operations). It applies the word size mask to ensure the
        value fits in 16 bits, then triggers a UI refresh.

        Args:
            value: The new value to store (may be any integer; will be masked to 16 bits).
        """
        # Mask the value to WORD_SIZE bits using modulo arithmetic.
        # This ensures the register stores only values 0-65535, matching the simulated
        # CPU's word width. See "Educational notes" for explanation of "1 << WORD_SIZE".
        self._value = value % (1 << WORD_SIZE)
        self._update_display()

    def _set_control(self, control: ControlSignal | None):
        """Update the control signal and refresh the visual display.

        This method records which control signal is currently active on the register.
        The UI uses this to highlight the active RTN step. For example, during
        ACC ← ALU, the control signal shows that ACC is being written to.

        Args:
            control: The ControlSignal to assert (e.g., ControlSignal.READ, ControlSignal.WRITE),
                or None to clear the control signal when the register is idle.
        """
        self._control = control
        self._update_display()

    def inc(self, offset: int = 1):
        """Increment the register by one and assert the INC control signal.

        This operation is used in RTN sequences like PC ← PC + 1 during instruction
        fetch. The INC control signal is displayed to show students which operation
        is active. Overflow is handled automatically (65535 + 1 wraps to 0).

        If an offset other than 1 is provided, the register is incremented by that amount.
        """
        self._set_value(self._value + offset)
        self._set_control(ControlSignal.INC)

    def dec(self, offset: int = 1):
        """Decrement the register by one and assert the DEC control signal.

        This operation is the complement of inc(). Underflow is handled automatically
        (0 - 1 wraps to 65535).

        If an offset other than 1 is provided, the register is decremented by that amount.
        """
        self._set_value(self._value - offset)
        self._set_control(ControlSignal.DEC)

    def write(self, value: int):
        """Store a value and assert the WRITE control signal.

        This operation represents an RTN transfer like ACC ← MDR. The value is masked
        to 16 bits automatically. The WRITE control signal is displayed to show that
        this register is being updated.

        Args:
            value: The value to store. Will be masked to 16 bits (0 to 65535).
        """
        self._set_value(value)
        self._set_control(ControlSignal.WRITE)

    def read(self) -> int:
        """Assert the READ control signal and return the stored value.

        This operation represents reading a register during an RTN transfer like
        MDR ← PC. The READ control signal is displayed to show that this register
        is being accessed. The returned value is the current stored value without
        any modifications.

        Returns:
            The current stored value (0 to 65535).
        """
        self._set_control(ControlSignal.READ)
        return self._value

    def reset_control(self):
        """Clear any active control signal so the register appears idle.

        This is called after an RTN step completes, to reset the display and prepare
        for the next operation. Without this, the register would show the previous
        operation's control signal indefinitely.
        """
        self._set_control(None)
        self._update_display()

    def _update_display(self):
        """Refresh the display for this register (inherited from CPUComponent).

        This method is called automatically whenever the register's value or control
        signal changes, ensuring the UI stays synchronized with the register state.
        """
        return super()._update_display()

    def __repr__(self) -> str:
        """Return a human-readable representation of the register value.

        Used for debugging and UI display to show the current register value
        in hexadecimal format (4 digits, zero-padded).

        Returns:
            The stored value as a 4-digit hexadecimal string (e.g., '042A').
        """
        return f"{self._value:04X}"


if __name__ == "__main__":
    from common.tester import run_tests_for_function, test_module
    from simulator.component import NonDisplayer

    VERBOSE = False
    # Default verbose value for all tests

    def test_value_setter(verbose=VERBOSE):
        """Test that the value setter correctly masks to 16 bits."""
        reg = Register(name=ComponentName.PC)
        if not verbose:
            reg.displayer = NonDisplayer()  # Disable display updates for cleaner test output

        test_cases = [
            (0, 0),
            (1, 1),
            (65535, 65535),
            (65536, 0),  # Wraps around
            (65537, 1),  # Wraps around
            (-1, 65535),  # Negative wraps to max
            (-2, 65534),  # Negative wraps to max - 1
        ]
        args = [(input,) for input, _ in test_cases]
        expected = [expected for _, expected in test_cases]

        def value_setter(input):
            reg._set_value(input)
            return reg._value
        
        return run_tests_for_function(
            args,
            expected,
            value_setter,
            comment="value setter with masking",
        )
    
    def test_control_signal(verbose=VERBOSE):
        """Test that control signals are set correctly on read/write/inc/dec."""
        reg = Register(name=ComponentName.ACC)
        if not verbose:
            reg.displayer = NonDisplayer()  # Disable display updates for cleaner test output

        test_cases = [
            ControlSignal.READ,
            ControlSignal.WRITE,
            ControlSignal.INC,
            ControlSignal.DEC,
            None,  # Reset control
        ]
        args = [(signal,) for signal in test_cases]
        expected = test_cases  # Expect the control signal to be set as given

        def control_setter(signal):
            if signal is None:
                reg.reset_control()
            else:
                reg._set_control(signal)
            return reg._control
        return run_tests_for_function(
            args,
            expected,
            control_setter,
            comment="control signal setter",
        )
    
    def test_inc(verbose=VERBOSE):
        """Test that inc() correctly increments and wraps values."""
        reg = Register(name=ComponentName.IX)
        if not verbose:
            reg.displayer = NonDisplayer()  # Disable display updates for cleaner test output

        test_cases = [
            ((0,), 1),
            ((65534,), 65535),
            ((65535,), 0),      # Wraps around
            ((0,7), 7),         # with second optional offset argument
            ((534,538), 1072),  # 534 + 538 = 1072, no wrap
            ((65535,100), 99), # Wraps around
        ]
        args = [input for input, _ in test_cases]
        expected = [expected for _, expected in test_cases]

        def incrementer(input, offset=None):
            reg._set_value(input)  # Set initial value
            if offset is not None:
                reg.inc(offset)  # Increment by offset
            else:
                reg.inc()  # Increment by 1
            if not reg._control == ControlSignal.INC:
                raise AssertionError(f"Expected control signal INC but got {reg._control}")
            return reg._value
        
        return run_tests_for_function(
            args,
            expected,
            incrementer,
            comment="increment operation with wrapping",
        )
    
    def test_dec(verbose=VERBOSE):
        """Test that dec() correctly decrements and wraps values."""
        reg = Register(name=ComponentName.IX)
        if not verbose:
            reg.displayer = NonDisplayer()  # Disable display updates for cleaner test output

        test_cases = [
            ((1,), 0),
            ((65535,), 65534),
            ((0,), 65535),          # Wraps around
            ((65535,100), 65435),   # with second optional offset argument
            ((534,532), 2),         # 534 - 532 = 2, no wrap
            ((0,7), 65529),         # Wraps around
        ]
        args = [input for input, _ in test_cases]
        expected = [expected for _, expected in test_cases]

        def decrementer(input, offset=None):
            reg._set_value(input)  # Set initial value
            if offset is not None:
                reg.dec(offset)  # Increment by offset
            else:
                reg.dec()  # Increment by 1
            if not reg._control == ControlSignal.DEC:
                raise AssertionError(f"Expected control signal DEC but got {reg._control}")
            return reg._value
        
        return run_tests_for_function(
            args,
            expected,
            decrementer,
            comment="decrement operation with wrapping",
        )

    test_module(
        "register",
        [
            test_value_setter,
            test_control_signal,
            test_inc,
            test_dec,
        ],
        verbose=VERBOSE
    )