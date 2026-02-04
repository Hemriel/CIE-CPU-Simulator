"""Visual display component for variable label addresses from the assembler.

Responsibility:
- Display variable label mappings produced by the assembler stepper.
- Highlight the most recently updated label during pass 1 or pass 2.

Entry point:
- :class:`VariableLabelDisplay`: Table widget updated by assembler snapshots.

Design choices:
- This display is driven by assembler output, not by a direct back end component.
    The assembler stepper produces label tables, and the UI renders them.
- The display formats the mapping for visualization but performs no assembly logic.
"""

# textual specific imports. For more information, see https://textual.textualize.io/
from textual.widgets import DataTable


class VariableLabelDisplay(DataTable):
    """Visual widget that displays variable label mappings.

    Shows label names with their current decimal and hexadecimal addresses,
    and optionally highlights a label that was just updated.
    """

    def __init__(self) -> None:
        """Create a variable label display table."""
        super().__init__()
        self.border_title = "Variable Labels"
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """Initialize the table columns and empty state."""
        self.add_column("Label")
        self.add_column("Dec")
        self.add_column("Hex")
        self.update_labels({})

    def update_labels(self, labels: dict[str, int], *, highlight: str | None = None) -> None:
        """Replace the displayed label table.

        Args:
            labels: Mapping from variable label name to its current address.
            highlight: Optional label name to highlight in the table.
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
