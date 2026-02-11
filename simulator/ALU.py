"""Arithmetic Logic Unit (ALU) that executes arithmetic and logic operations.

Responsibility:
- Execute arithmetic operations (ADD, SUB) and logic operations (AND, OR, XOR, CMP)
  as specified by control signals from the Control Unit.
- Maintain the comparison flag for conditional branch instructions.
- Provide visual state for the UI to display operands, operation mode, and results.

Design note:
- The ALU is a passive component: it does not initiate operations. The Control Unit
  sets operands and mode, then calls compute() to execute the operation.
- Results are stored internally until read by register transfers (typically ACC ← ALU).

Illustrates:
- CIE 9618: 4.1 Central Processing Unit (CPU) Architecture:
    - Show understanding of the purpose and role of the ALU.
    - Show understanding of the purpose and roles of registers.
- CIE 9618: 4.3 Bit Manipulation:
    - Show understanding of and perform binary shifts (and other bitwise operations).
- CIE 9618: 13.1 User-defined data types (depper than intended by curriculum, this could serve as a complex example):
    - Show understanding of why user-defined data types are necessary.
    - Chose and define an appropriate user defined data type for a given problem.

Entry point:
- The :class:`ALU` class is instantiated by the CPU and driven by the Control Unit.
- The :class:`FlagComponent` tracks comparison results for conditional branches.

Includes:
- :class:`FlagComponent`: Comparison flag component (E flag)
- :class:`ALU`: Main ALU implementation with operation execution
"""

from dataclasses import dataclass, field
from simulator.component import CPUComponent
from common.constants import ComponentName, ControlSignal, WORD_SIZE, AbnormalComponentUseError


### Educational notes on Python features used in this module ###
#
# Dataclasses with default_factory (field(default_factory=FlagComponent)):
# This pattern creates a fresh FlagComponent instance for each ALU instance.
# Without default_factory, all ALU instances would share the same flag object
# (mutable default argument problem in Python).
# More info: https://docs.python.org/3/library/dataclasses.html#mutable-default-values
#
# Bitwise operations (& | ^):
# Python bitwise operations are NOT part of the curriculum. However, bitwise operations
# are studied in Unit 4.3 Bit manipulation, when working on assembly language.
# Python's bitwise operators work on integers as if they were binary sequences (by converting them
# to binary under the hood).
# & performs AND, | performs OR, ^ performs XOR on each bit position.


@dataclass
class FlagComponent(CPUComponent):
    """Comparison flag component that stores the result of CMP/CMI instructions.
    
    The E (Equal/comparison) flag is set to True when ACC equals the compared value,
    and False otherwise. Conditional branch instructions (JPE, JPN) read this flag
    to decide whether to jump.
    """

    name: ComponentName = ComponentName.CMP_FLAG
    value : bool = False

    def read(self) -> bool:
        """Read the current flag value."""
        return self.value

    def write(self, value: bool) -> None:
        """Write a new flag value."""
        self.value = value
        self._update_display()

    def __repr__(self) -> str:
        return f"{'SET' if self.value else 'CLEAR'}"


@dataclass
class ALU(CPUComponent):
    """Model of the ALU following CIE 9618 RTN description of arithmetic and logic operations.
    
    The ALU performs operations specified by control signals from the Control Unit.
    It operates in three phases:
    1. set_mode() selects the operation (ADD, SUB, AND, OR, XOR, CMP)
    2. set_operands() provides ACC and the second operand
    3. compute() executes the operation and updates the result/flags
    
    Phases 1 and 2 can be called in any order before compute().

    Attributes:
        control: The ControlSignal currently armed for the pending operation.
        acc: First operand (typically the accumulator value).
        operand: Second operand (from memory, immediate, or register).
        result: Computed result available for register transfer (e.g., ACC ← ALU).
        flag_component: Comparison flag component updated by CMP operations.
    """

    name: ComponentName = ComponentName.ALU
    control: ControlSignal | None = None
    acc: int = 0
    operand: int = 0
    result: int = 0
    flag_component: FlagComponent = field(default_factory=FlagComponent) # See note above

    def read(self) -> int:
        """Read the most recent ALU result.
        
        Called during register transfers like ACC ← ALU after an operation completes.
        """
        return self.result

    def write(self, data: int) -> None:
        """ALU does not support direct writes.
        
        The ALU is a computational unit, not a storage register. Operands are provided
        via set_operands() and results are retrieved via read().
        
        Raises:
            AbnormalComponentUseError: Always raised; ALU is read-only from the bus perspective.
        """
        raise AbnormalComponentUseError("ALU does not support direct writes.")

    def set_mode(self, control: ControlSignal | None) -> None:
        """Select the ALU operation mode and refresh the UI so RTN can display it."""

        self.control = control
        self._update_display()

    def set_operands(self, acc: int, operand: int) -> None:
        """Provide operands from register transfers and redraw the panel."""

        self.acc = acc
        self.operand = operand
        self._update_display()

    def compute(self) -> None:
        """Execute the selected ControlSignal, store the result, and update flags.
        
        Performs the operation selected by the current control signal:
        - ADD, SUB: Arithmetic operations, result stored for later ACC transfer
        - AND, OR, XOR: Bitwise logic operations, result stored for later ACC transfer
        - CMP: Compare ACC with operand, set comparison flag (no result stored)
        
        The comparison flag (E) is updated only for CMP operations. Other operations
        do not modify flags (CIE 9618 simplification; real CPUs update multiple flags).
        """
        # Every ControlSignal maps to a deterministic arithmetic or logic function.
        if self.control == ControlSignal.ADD:
            self._set_result(self.acc + self.operand)
        elif self.control == ControlSignal.SUB:
            self._set_result(self.acc - self.operand)
        # next three are bitwise operations, see note above
        elif self.control == ControlSignal.AND:
            self._set_result(self.acc & self.operand)
        elif self.control == ControlSignal.OR:
            self._set_result(self.acc | self.operand)
        elif self.control == ControlSignal.XOR:
            self._set_result(self.acc ^ self.operand)
        elif self.control == ControlSignal.CMP:
            compare = self.acc == self.operand
            self.flag_component.write(compare)
        else:
            raise AbnormalComponentUseError(
                f"ALU compute() called with invalid or unset control signal: {self.control}"
            )

    def _set_result(self, result: int) -> None:
        """Store the computed result and refresh the UI display."""
        self.result = result % (1 << WORD_SIZE)  # Wrap to 16-bit word (2^WORD_SIZE)
        self._update_display()

    def __repr__(self) -> str:
        """Return human-readable ALU state for debugging and logging."""
        return (
            f"Control: {self.control} | "
            f"Value from ACC: {self.acc:04X} | Operand : {self.operand:04X} | "
            f"Result: {self.result:04X}"
        )

# Run tests when this module is executed directly
if __name__ == "__main__":
    from common.tester import run_tests_for_function
    
    # Test ADD operation: normal values, boundary (overflow), and wraparound
    def test_add():
        """Test ADD operation with various operand combinations."""
        alu = ALU()
        
        test_cases = [
            (10, 20, 30),               # Normal: 10 + 20 = 30
            (0, 0, 0),                  # Boundary: 0 + 0 = 0
            (65535, 1, 0),              # Overflow: wraps to 0
            (32767, 32768, 65535),      # Large values: wraps
        ]
        
        failed = False
        for acc, operand, expected in test_cases:
            alu.set_mode(ControlSignal.ADD)
            alu.set_operands(acc, operand)
            alu.compute()
            result = alu.read()
            if result != expected:
                print(f"  ADD {acc} + {operand}: expected {expected}, got {result} [FAIL]")
                failed = True
        
        if not failed:
            print("  ADD: PASS")
    
    # Test SUB operation: normal values, boundary (negative/wrap), zero result
    def test_sub():
        """Test SUB operation with various operand combinations."""
        alu = ALU()
        
        test_cases = [
            (20, 10, 10),               # Normal: 20 - 10 = 10
            (10, 10, 0),                # Boundary: 10 - 10 = 0
            (5, 10, (1 << 16) - 5),     # Negative wraps
            (0, 1, 65535),              # Boundary: 0 - 1 wraps to 65535
        ]
        
        failed = False
        for acc, operand, expected in test_cases:
            alu.set_mode(ControlSignal.SUB)
            alu.set_operands(acc, operand)
            alu.compute()
            result = alu.read()
            if result != expected:
                print(f"  SUB {acc} - {operand}: expected {expected}, got {result} [FAIL]")
                failed = True
        
        if not failed:
            print("  SUB: PASS")
    
    # Test AND operation: various bit patterns
    def test_and():
        """Test AND operation with various bitwise patterns."""
        alu = ALU()
        
        test_cases = [
            (0xFF, 0xF0, 0xF0),         # Partial overlap
            (0xFFFF, 0xFFFF, 0xFFFF),   # All bits set
            (0xFFFF, 0x0000, 0x0000),   # No overlap
            (0xAA, 0x55, 0x00),         # Alternating bits
        ]
        
        failed = False
        for acc, operand, expected in test_cases:
            alu.set_mode(ControlSignal.AND)
            alu.set_operands(acc, operand)
            alu.compute()
            result = alu.read()
            if result != expected:
                print(f"  AND 0x{acc:04X} & 0x{operand:04X}: expected 0x{expected:04X}, got 0x{result:04X} [FAIL]")
                failed = True
        
        if not failed:
            print("  AND: PASS")
    
    # Test OR operation: set bits from either operand
    def test_or():
        """Test OR operation with various bitwise patterns."""
        alu = ALU()
        
        test_cases = [
            (0x0F, 0xF0, 0xFF),         # Complementary patterns
            (0x0000, 0x0000, 0x0000),   # Both zero
            (0xFFFF, 0x0000, 0xFFFF),   # All bits set
            (0xAA, 0x55, 0xFF),         # Alternating
        ]
        
        failed = False
        for acc, operand, expected in test_cases:
            alu.set_mode(ControlSignal.OR)
            alu.set_operands(acc, operand)
            alu.compute()
            result = alu.read()
            if result != expected:
                print(f"  OR 0x{acc:04X} | 0x{operand:04X}: expected 0x{expected:04X}, got 0x{result:04X} [FAIL]")
                failed = True
        
        if not failed:
            print("  OR: PASS")
    
    # Test XOR operation: bits differ between operands
    def test_xor():
        """Test XOR operation with various bitwise patterns."""
        alu = ALU()
        
        test_cases = [
            (0xFFFF, 0x0000, 0xFFFF),   # Different
            (0x5555, 0x5555, 0x0000),   # Same values
            (0xF0, 0x0F, 0xFF),         # Complementary
            (0xAA, 0x55, 0xFF),         # Alternating inverted
        ]
        
        failed = False
        for acc, operand, expected in test_cases:
            alu.set_mode(ControlSignal.XOR)
            alu.set_operands(acc, operand)
            alu.compute()
            result = alu.read()
            if result != expected:
                print(f"  XOR 0x{acc:04X} ^ 0x{operand:04X}: expected 0x{expected:04X}, got 0x{result:04X} [FAIL]")
                failed = True
        
        if not failed:
            print("  XOR: PASS")
    
    # Test CMP operation: comparison flag set/clear based on equality
    def test_cmp():
        """Test CMP operation and flag component behavior."""
        alu = ALU()
        
        test_cases = [
            (100, 100, True),           # Equal
            (100, 50, False),           # Not equal
            (0, 0, True),               # Boundary: zero equals zero
            (65535, 65535, True),       # Boundary: max value equals itself
        ]
        
        failed = False
        for acc, operand, expected_flag in test_cases:
            alu.set_mode(ControlSignal.CMP)
            alu.set_operands(acc, operand)
            alu.compute()
            flag_result = alu.flag_component.read()
            if flag_result != expected_flag:
                print(f"  CMP {acc} == {operand}: flag expected {expected_flag}, got {flag_result} [FAIL]")
                failed = True
        
        if not failed:
            print("  CMP: PASS")
    
    # Test read() method: returns most recent result
    def test_read():
        """Test read() method returns correct result after compute()."""
        alu = ALU()
        
        test_cases = [
            (ControlSignal.ADD, 10, 5, 15),
            (ControlSignal.SUB, 20, 7, 13),
            (ControlSignal.AND, 0xFF, 0x0F, 0x0F),
        ]
        
        failed = False
        for control, acc, operand, expected in test_cases:
            alu.set_mode(control)
            alu.set_operands(acc, operand)
            alu.compute()
            result = alu.read()
            if result != expected:
                print(f"  read() after {control}: expected {expected}, got {result} [FAIL]")
                failed = True
        
        if not failed:
            print("  read(): PASS")
    
    # Test write() method: should raise AbnormalComponentUseError
    def test_write():
        """Test write() method raises appropriate error."""
        alu = ALU()
        
        try:
            alu.write(42)
            print(f"  write(): FAIL - expected exception but none raised")
        except AbnormalComponentUseError:
            print(f"  write(): PASS")
        except Exception as e:
            print(f"  write(): FAIL - raised {type(e).__name__} instead of AbnormalComponentUseError")
    
    # Run all tests
    print("Testing ALU class:")
    test_add()
    test_sub()
    test_and()
    test_or()
    test_xor()
    test_cmp()
    test_read()
    test_write()
