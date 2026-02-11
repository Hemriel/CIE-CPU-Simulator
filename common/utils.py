
"""Shared utility functions for the CPU simulator.

Responsibility:
- Provide reusable utility functions that support UI rendering and component
  display logic throughout the simulator.
- Serve as a single source of truth for formatting and display conventions,
  ensuring consistency across the application.

Entry point / public API:
- :func:`formatted_value`: Format numeric values for UI display in multiple bases
  (hexadecimal, decimal, or binary with spacing for readability).

Design note:
- This module complements common/constants.py: while constants.py holds static
  enum and configuration values, utils.py holds functions that need reuse across
  multiple UI components. The formatted_value function is particularly critical
  because it's called by register displays, memory displays, and control unit
  displays to ensure all numeric output follows the same convention.

Illustrates:
- CIE 9618: 1.1 Data Representation:
    - Show understanding of different number systems (binary, denary, hexadecimal).
    - Be able to represent data in binary, hexadecimal, and decimal form.

Educational intent:
Students can see how abstraction works: instead of each display widget handling
number formatting independently, we centralize it here. This reduces bugs and
makes the code more maintainable: if a display format changes, we change it in
one place.
"""

from common.constants import DisplayMode
from common.tester import run_tests_for_function

# Standardized method to format numeric values according to display mode.
def formatted_value(value: int, mode: DisplayMode) -> str:
    """Format a numeric value according to the current display mode.
    
    Args:
        value: The integer value to format.
        mode: The display mode to use for formatting.
    Returns:
        A string representation of the value in the selected radix.
    """
    if value < 0 or value > 0xFFFF:
        raise ValueError("Value out of range (must be 0 to 65535 inclusive)")
    if mode == DisplayMode.HEX:
        return f"{value:04X}"
    elif mode == DisplayMode.DECIMAL:
        return str(value)
    elif mode == DisplayMode.BINARY:
        bin = f"{value:016b}"
        for i in range(4, len(bin), 5):
            bin = bin[:len(bin)-i] + " " + bin[len(bin)-i:]
        return bin
    else:
        return str(value)  # Fallback to decimal
    

if __name__ == "__main__":
    """Run tests for the formatted_value function in common/utils.py."""
    normal_args = [
        (255, DisplayMode.HEX),
        (255, DisplayMode.DECIMAL),
        (255, DisplayMode.BINARY),
        (4095, DisplayMode.HEX),
        (4095, DisplayMode.DECIMAL),
        (4095, DisplayMode.BINARY),
    ]
    normal_expected = [
        "00FF",
        "255",
        "0000 0000 1111 1111",
        "0FFF",
        "4095",
        "0000 1111 1111 1111",
    ]
    run_tests_for_function(
        normal_args, 
        normal_expected, 
        formatted_value, 
        comment="normal values"
    )

    boundary_args = [
        (0, DisplayMode.HEX),
        (0, DisplayMode.DECIMAL),
        (0, DisplayMode.BINARY),
        (65535, DisplayMode.HEX),
        (65535, DisplayMode.DECIMAL),
        (65535, DisplayMode.BINARY),
    ]
    boundary_expected = [
        "0000",
        "0",
        "0000 0000 0000 0000",
        "FFFF",
        "65535",
        "1111 1111 1111 1111",
    ]
    run_tests_for_function(
        boundary_args,
        boundary_expected,
        formatted_value,
        comment="boundary values",
    )

    abnormal_args = [
        (-1, DisplayMode.HEX),
        (-1, DisplayMode.DECIMAL),
        (-1, DisplayMode.BINARY),
        (70000, DisplayMode.HEX),
        (70000, DisplayMode.DECIMAL),
        (70000, DisplayMode.BINARY),
    ]
    abnormal_expected = [
        "error",
        "error",
        "error",
        "error",
        "error",
        "error",
    ]
    run_tests_for_function(
        abnormal_args,
        abnormal_expected,
        formatted_value,
        comment="abnormal values",
    )