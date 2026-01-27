"""Textual widget for displaying variable label addresses.

During pass 1 variables are allocated sequential "slots". After pass 1 is
finalised, those slots are converted into absolute RAM addresses by placing
variables after the instruction area.

This widget shows the current mapping so students can see it evolve.
"""

from __future__ import annotations

from textual.widgets import DataTable


class VariableLabelDisplay(DataTable):
    """A simple table mapping variable labels to their current addresses."""

    def __init__(self) -> None:
        super().__init__()
        self.border_title = "Variable Labels"
        self.cursor_type = "row"

    def on_mount(self) -> None:
        self.add_column("Label")
        self.add_column("Dec")
        self.add_column("Hex")
        self.update_labels({})

    def update_labels(self, labels: dict[str, int], *, highlight: str | None = None) -> None:
        """Replace the displayed label table.

        Args:
            labels: Mapping from variable label name to its current address.
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
