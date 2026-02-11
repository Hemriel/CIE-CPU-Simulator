"""ASCII visualization of RAM state and access.

Responsibility:
- Displays the currently accessed memory address (MAR).
- Shows a scrollable window of RAM words around the currently active address,
  with the active row highlighted via cursor positioning.
- Updates dynamically as memory is accessed and modified.

Entry points:
- :class:`RAMAddressDisplay`: Shows the current address being accessed.
- :class:`RAMDataDisplay`: DataTable showing neighboring RAM words with smart
  scrolling to keep the active address visible.

Design note:
- Like all display components, these decouple front-end (ASCII/DataTable rendering)
  from back-end (RAM model). The RAM object holds the actual data; these widgets
  just visualize it.
- Smart scrolling: when the cursor moves, the view adjusts to keep the active
  address visible while minimizing unnecessary scrolling (only scrolls if the
  address moves toward the edge of the display window).
"""
from cpu.RAM import RAM
from common.constants import DisplayMode, formatted_value

# Textual-specific imports. For more information, see https://textual.textualize.io/
from rich.text import Text
from textual.widgets import Static, DataTable


class RAMAddressDisplay(Static):
    """Inteded to display the current RAM address is the first place, this
    later became obsolete. The component was kept as a title display for RAM.
    
    Attributes:
        ram: The RAM object whose address should be displayed.
    """

    DEFAULT_CSS = """
    RAMAddressDisplay {
        width: 26;
        background: grey;
        content-align: center middle;
    }
    """

    def __init__(self, ram: RAM) -> None:
        """Initialize the RAM address display widget.
        
        Args:
            ram: The RAM object whose address should be displayed.
        """
        super().__init__()
        self.ram = ram

    def on_mount(self) -> None:
        self.update_display()

    def update_display(self) -> None:
        """Update the display with the current address state."""
        self.content = Text(f"RAM")


class RAMDataDisplay(DataTable):
    """Display a window of RAM words with smart scrolling.
    
    This widget shows a scrollable DataTable of neighboring memory addresses and
    their values. The active memory word (currently being accessed) is highlighted
    by moving the table cursor to that row.
    
    Smart scrolling keeps the active address visible:
    - If the address is visible and not near the top/bottom edge, the view stays
      put (smooth scrolling).
    - If the address moves toward an edge or becomes invisible, the view
      recenters on the active address.
    
    This provides a good balance between visual stability (view doesn't jump
    around constantly) and usability (active address stays visible).
    
    Attributes:
        ram: The RAM object whose data should be displayed.
        display_start: The first RAM address currently shown in the table.
        LIMIT_ROWS: Threshold (5 rows) for deciding when to scroll.
    """

    LIMIT_ROWS = 5

    def __init__(self, ram: RAM) -> None:
        """Initialize the RAM data display widget.
        
        Args:
            ram: The RAM object whose data should be displayed.
        """
        super().__init__()
        self.id = "ram-data-display"
        self.ram = ram
        self.display_start = 0  # First address shown in the table.
        self.cursor_type = "row"  # Use row-based cursor to highlight active address.

        self.number_display_mode = DisplayMode.HEX

    def on_mount(self) -> None:
        self.add_column("#")
        self.add_column("Value")
        self.update_display()

    def set_number_display_mode(self, mode: DisplayMode) -> None:
        """Set the number display mode for the ALU values.
        
        Args:
            mode: One of "decimal", "hexadecimal", or "binary"
        """
        # Currently, this display only supports hexadecimal.
        # This method is a placeholder for future extensions.
        self.number_display_mode = mode

    def update_display(self) -> None:
        """Refresh the table with current RAM state and active address.
        
        This method:
        1. Updates the 'inactive' CSS class based on RAM activity.
        2. Computes which RAM addresses to display based on the active address
           and smart scrolling logic.
        3. Rebuilds the table with current RAM values in the selected number display mode.
        4. Positions the cursor at the active address row.
        """
        # Toggle the 'inactive' CSS class for visual feedback when RAM is idle.
        if self.ram.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        
        # Compute how many rows are available for display (excluding header/footer).
        height = self.size.height - 2  # Account for header/footer
        
        # Get the currently active address (currently being accessed).
        focus = self.ram.address_comp.address
        
        # Update the display window to keep the active address visible with
        # smart scrolling (doesn't jump unless necessary).
        self.update_start(focus, height)
        
        # Build the table rows: address and value, both in hexadecimal.
        lines = []
        for offset in range(height):
            addr = self.display_start + offset
            value = self.ram.memory.get(addr, 0)  # Default to 0 if not in memory.
            lines.append([f"{addr:04X}", formatted_value(value, self.number_display_mode)])  # Format according to display mode.
        
        # Clear and repopulate the table.
        self.clear()
        for line in lines:
            self.add_row(*line)
        
        # Move the cursor to highlight the active address in the table.
        # Calculate which row in the table corresponds to the active address.
        self.move_cursor(row=focus - self.display_start)

    def update_start(self, focus: int, height: int) -> None:
        """Determine the first address to display based on the active address.
        
        Smart scrolling algorithm:
        - If the active address is currently visible AND not near an edge
          (within LIMIT_ROWS of top/bottom), keep the same start position.
        - Otherwise, recenter the display on the active address.
        
        This balances visual stability (view doesn't jump constantly) with
        usability (active address stays visible and reasonably centered).
        
        Args:
            focus: The currently active RAM address (to highlight).
            height: The number of rows available for display.
        """
        # Check if the focus address is outside the currently visible range.
        not_visible = focus < self.display_start or focus >= self.display_start + height
        
        # Check if the focus address is near the top or bottom edge of the display.
        # If it's within LIMIT_ROWS of either edge, we should scroll to recenter.
        in_limit_rows = (focus < self.display_start + self.LIMIT_ROWS) or (focus >= self.display_start + height - self.LIMIT_ROWS)
        
        # Scroll only if the focus is not visible or is near an edge.
        if not_visible or in_limit_rows:
            # Recenter the display around the focus address.
            # Clamped to ensure we don't scroll to negative addresses.
            self.display_start = max(0, focus - height // 2)