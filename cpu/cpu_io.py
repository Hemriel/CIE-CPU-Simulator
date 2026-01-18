"""I/O component that feeds ASCII characters into and out of the simulated CPU."""

from dataclasses import dataclass
from cpu.component import CPUComponent
from common.constants import ComponentName


@dataclass
class IO(CPUComponent):
    """Simplified device holding queued ASCII characters for IN/OUT visualization.

    Attributes:
        contents: The pending characters represented as an ASCII string so IN/OUT match
            the CIE requirement to transfer ASCII values one character at a time.
    """

    name: ComponentName
    contents: str = ""

    def write(self, data: int) -> None:
        """Enqueue a byte by converting it to an ASCII character and refreshing the UI."""

        self.contents += chr(data)
        self._update_display()

    def read(self) -> int | None:
        """Dequeue the next ASCII character, return it as its ordinal, and update visuals."""

        if self.contents:
            data = ord(self.contents[0])
            self.contents = self.contents[1:]
            self._update_display()
            return data
        return None

    def __repr__(self) -> str:
        return f" IO | Contents: '{self.contents}'"
