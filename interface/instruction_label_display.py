"""Textual widget for displaying instruction label addresses.

This is used by the interactive assembler view so students can watch pass 1 fill
out the instruction label table in real time.
"""

from __future__ import annotations

from textual.widgets import DataTable


class InstructionLabelDisplay(DataTable):
    """A simple table mapping instruction labels to their resolved addresses."""

    def __init__(self) -> None:
        super().__init__()
        self.border_title = "Instruction Labels"
        self.cursor_type = "row"

    def on_mount(self) -> None:
        self.add_column("Label")
        self.add_column("Dec")
        self.add_column("Hex")
        self.update_labels({})

    def update_labels(self, labels: dict[str, int], *, highlight: str | None = None) -> None:
        """Replace the displayed label table.

        Args:
            labels: Mapping from label name to absolute instruction address.
        """

        if labels:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")

        self.clear()
        sorted_items = sorted(labels.items())
        highlight_row: int | None = None
        for row_index, (label, address) in enumerate(sorted_items):
            self.add_row(label, str(address), f"{address:04X}")
            if highlight is not None and label == highlight:
                highlight_row = row_index

        if highlight_row is not None:
            self.move_cursor(row=highlight_row)
