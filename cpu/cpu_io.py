"""I/O component for character-based input and output in the CPU simulator.

Responsibility:
- Provide a simple queue of ASCII characters that the CPU can read from (IN
  instruction) or write to (OUT instruction), following CIE 9618 I/O conventions.

Illustrates:
- CIE 9618: 1.1 Data representation:
    - Show understanding of different number systems (binary, denary, hexadecimal).
    - Show understanding and be able to represent character data in its internal binary form (ASCII).

Design choices:
- Uses a string-based queue for simplicity and student-readability.
- Each `read()` dequeues one character and returns its ASCII ordinal (0-255).
- Each `write()` accepts an integer byte value and converts it to a character,
  appending it to the output queue.
- The queue is visible in the UI so students can watch characters flow through
  the system during program execution.

Entry points:
- :class:`IO` class: implements the CPUComponent protocol for I/O operations.

Includes:
- :class:`IO`
"""

from dataclasses import dataclass
from cpu.component import CPUComponent
from common.constants import ComponentName

### Educational notes on Python operations used in this module ###
#
# Data classes:
# Data classes are NOT in the curriculum.
# Here is a detailed explanation: https://docs.python.org/3/library/dataclasses.html
# In a few words, they are a concise way to define classes that mainly store
# data attributes. The __init__, __repr__, __eq__, and other methods are
# automatically generated based on the class attributes.

@dataclass
class IO(CPUComponent):
    """I/O device holding queued ASCII characters for IN/OUT instructions.

    This component models the CIE 9618 requirement that IN/OUT instructions
    transfer single ASCII characters. The internal queue is represented as a
    string for simplicity and visual clarity in the UI.

    Attributes:
        name: The component's official name (from ComponentName enum).
        contents: The pending characters represented as an ASCII string. Each
            `read()` dequeues the leftmost character, and each `write()` appends
            a new character to the right.
    """

    name: ComponentName
    contents: str = "example"  # Default queue content for demonstration

    def write(self, data: int) -> None:
        """Enqueue a byte by converting it to an ASCII character.

        This models the OUT instruction, which writes a single ASCII character
        from the accumulator to the output device.

        Args:
            data: An integer byte value (0-255) representing the ASCII code of
                the character to output.
        """
        # Convert the integer to its ASCII character and append to the queue.
        self.contents += chr(data)
        self._update_display()

    def read(self) -> int | None:
        """Dequeue the next ASCII character and return it as its ordinal.

        This models the IN instruction, which reads a single ASCII character
        from the input device into the accumulator.

        Returns:
            The ASCII code (0-255) of the dequeued character, or None if the
            queue is empty (no input available).
        """
        if self.contents:
            # Convert the leftmost character to its ASCII ordinal (0-255).
            data = ord(self.contents[0])
            # Remove the character from the queue (FIFO behavior).
            self.contents = self.contents[1:]
            self._update_display()
            return data
        # No input available; return None to signal an empty queue.
        return None

    def __repr__(self) -> str:
        return f" IO | Contents: '{self.contents}'"
