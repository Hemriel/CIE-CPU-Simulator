"""ASCII bus visualization helpers for the CPU simulator.

Responsibility:
- Turns high-level connections (source → destination) into ASCII "wires" drawn
  inside bus column widgets.
- Computes attachment points from live layout geometry (responsive to terminal
  resize).
- Implements simple trunk-and-stub drawing strategy for educational clarity.

Entry point:
- :func:`draw_connection_ascii` generates the ASCII art for a single connection.
- :func:`widget_anchor_y` computes vertical attachment points for widgets.
- :func:`which_side` determines left/right positioning relative to bus widget.

Design note:
- The UI is responsive: widget positions change as the terminal is resized, so
  attachment points are computed from Textual's live layout geometry on every
  render.
- Each bus draws *inside its own widget*, not as a full-screen overlay.
- RAM-specific anchoring: address bus connects MAR to the top of RAM column,
  data bus connects MDR to the currently active RAM word (DataTable cursor row).

Drawing strategy:
- A single vertical "trunk" runs through the middle of the bus widget.
- Each endpoint connects to the trunk via a horizontal stub.
- Junction points are marked with "+" where stubs meet the trunk.
- An arrowhead ("<" or ">") indicates the destination side.

This visual approach makes data flow explicit: students can trace the path from
source register through the trunk to the destination component.
"""
from dataclasses import dataclass
from typing import Any

# Textual-specific imports. For more information, see https://textual.textualize.io/
from textual.geometry import Region


@dataclass(frozen=True)
class ScreenPoint:
    """A point in absolute screen coordinates (terminal rows/columns).
    
    This data class represents a position in the terminal's coordinate system.
    It's used when computing where to attach bus endpoints to widgets, since
    Textual widgets report their positions in screen space.

    Attributes:
        x: Column (0-based) in the terminal.
        y: Row (0-based) in the terminal.
    """

    x: int
    y: int


def safe_screen_region(widget: Any) -> Region | None:
    """Best-effort fetch of a widget's screen-space region.
    
    Textual widgets have a `region` attribute giving their position relative to
    their parent. To get absolute screen coordinates, we must walk up the parent
    chain and accumulate offsets. This is necessary because bus endpoints may be
    in different parent containers, so their positions must be in a common
    coordinate system (screen space) for drawing to work correctly.

    Args:
        widget: Any Textual widget.

    Returns:
        A Region in screen coordinates if available, otherwise None if the widget
        has no region (not yet laid out or no parent chain).
    """

    # Fetch the widget's own region (position relative to its parent).
    region = getattr(widget, "region", None)
    if region is not None:
        # Start with the widget's position relative to its parent.
        x, y = int(region.x), int(region.y)
        
        # Walk up the parent chain to accumulate offsets.
        # Each parent's region gives its position relative to *its* parent,
        # so we add all parent offsets to get absolute screen coordinates.
        parent = getattr(widget, "parent", None)
        while parent is not None:
            parent_region = getattr(parent, "region", None)
            if parent_region is not None:
                x += int(parent_region.x)
                y += int(parent_region.y)
            parent = getattr(parent, "parent", None)
        
        # Return a new Region with absolute screen coordinates.
        return Region(x, y, int(region.width), int(region.height))

    # Widget not yet laid out or has no region.
    return None


def widget_anchor_y(widget: Any, *, mode: str = "center") -> int | None:
    """Compute an anchor Y position for a widget in screen coordinates.
    
    Different CPU components need different vertical attachment points:
    - Most registers attach at their vertical center (visually balanced).
    - RAM address bus attaches to the top of the RAM widget (conceptual: address
      selects the entire memory, not a specific word).
    - RAM data bus attaches to the currently active row (conceptual: data flows
      to/from the specific memory word being accessed).
    
    This function provides these three anchoring modes so bus visualizations can
    accurately reflect the conceptual flow of data.

    Args:
        widget: The widget to compute an anchor for.
        mode: Anchoring mode:
            - "center": vertical center of widget (default).
            - "top": top row of widget.
            - "ram_active_row": DataTable cursor row inside the widget
              (used for RAM data bus to show which word is being accessed).

    Returns:
        The anchor y in screen coordinates, or None if it can't be computed
        (widget not yet laid out).
    """

    # Get the widget's absolute screen region.
    region = safe_screen_region(widget)
    if region is None:
        return None

    # Mode "top": attach to the top edge of the widget.
    if mode == "top":
        return region.y

    # Mode "center": attach to the vertical center of the widget.
    if mode == "center":
        return region.y + max(0, region.height // 2)

    # Mode "ram_active_row": attach to the currently active DataTable row.
    # This mode is used for the RAM data bus to show which memory word is
    # currently being accessed (MAR points to this address).
    if mode == "ram_active_row":
        # The RAM DataTable updates its cursor position each refresh to highlight
        # the active memory word. We extract the cursor row to attach the bus.
        cursor_row = getattr(widget, "cursor_row", None)
        
        # If we can't find a cursor, fall back to center mode.
        if cursor_row is None:
            return region.y + max(0, region.height // 2)

        # DataTable widgets have a header row (column labels).
        # We assume 1 line of header and add it to the cursor row position.
        header_height = 1
        y = region.y + header_height + int(cursor_row)
        
        # Clamp the result to stay within the widget's region (defensive).
        return max(region.y, min(region.y + region.height - 1, y))

    # Unknown mode: raise an error to help catch configuration mistakes.
    raise ValueError(f"Unknown anchor mode: {mode}")


def which_side(bus_region: Region, widget_region: Region) -> str:
    """Determine whether a widget lies to the left or right of the bus column.
    
    The bus widget is a vertical column in the middle of the screen. CPU components
    (registers, ALU, etc.) are positioned to the left and right of this column.
    This function determines which side a widget is on, so we know which edge of
    the bus to attach the horizontal stub to.
    
    Args:
        bus_region: The bus widget's screen region.
        widget_region: The component widget's screen region.
    
    Returns:
        "left" if the widget is entirely to the left of the bus,
        "right" if the widget is entirely to the right of the bus,
        "center" if the widget overlaps or is inside the bus column.
    """

    # Widget is entirely to the left if its right edge is before the bus's left edge.
    if widget_region.x + widget_region.width <= bus_region.x:
        return "left"
    
    # Widget is entirely to the right if its left edge is after the bus's right edge.
    if widget_region.x >= bus_region.x + bus_region.width:
        return "right"
    
    # Overlapping or inside the bus column; treat as center (defensive case).
    return "center"


# For the drawing functions below, we operate on a 2D grid of characters
# represented as a list of lists of single-character strings. This allows
# us to modify individual characters easily before converting back to
# a list of strings for the final ASCII art output.

def _draw_hline(grid: list[list[str]], y: int, x1: int, x2: int, ch: str = "-") -> None:
    """Draw a horizontal line in the ASCII grid.
    
    This is a low-level drawing primitive for the ASCII art generation.
    It draws a horizontal line from x1 to x2 on row y, using the specified
    character. The line is drawn left-to-right regardless of whether x1 < x2
    or x2 < x1.
    
    Important: Only draws over blank spaces (" "), so existing characters
    (like junction markers "+") are preserved. This allows multiple drawing
    operations to compose without overwriting important markers.
    
    Args:
        grid: 2D character grid (list of rows, each row is a list of characters).
        y: Row index to draw on.
        x1: Starting column (inclusive).
        x2: Ending column (inclusive).
        ch: Character to use for the line (default: "-").
    """
    # Bounds check: ensure row y is within the grid.
    if y < 0 or y >= len(grid):
        return
    
    # Get the grid width (defensive: handle empty grid).
    width = len(grid[0]) if grid else 0
    if width <= 0:
        return

    # Normalize x1 and x2 so we always draw left-to-right.
    # This handles both x1 < x2 and x2 < x1 cases.
    start = max(0, min(x1, x2))  # Clamp to left edge of grid.
    end = min(width - 1, max(x1, x2))  # Clamp to right edge of grid.
    
    # Draw the line character by character, preserving existing non-space characters.
    for x in range(start, end + 1):
        if grid[y][x] == " ":  # Only overwrite blank spaces.
            grid[y][x] = ch


def _draw_vline(grid: list[list[str]], x: int, y1: int, y2: int, ch: str = "|") -> None:
    """Draw a vertical line in the ASCII grid.
    
    This is a low-level drawing primitive for the ASCII art generation.
    It draws a vertical line from y1 to y2 on column x, using the specified
    character. The line is drawn top-to-bottom regardless of whether y1 < y2
    or y2 < y1.
    
    Like _draw_hline, this only draws over blank spaces (" "), preserving
    existing characters (junction markers, arrowheads, etc.).
    
    Args:
        grid: 2D character grid (list of rows, each row is a list of characters).
        x: Column index to draw on.
        y1: Starting row (inclusive).
        y2: Ending row (inclusive).
        ch: Character to use for the line (default: "|").
    """
    # Get grid dimensions.
    height = len(grid)
    if height <= 0:
        return
    width = len(grid[0])
    
    # Bounds check: ensure column x is within the grid.
    if x < 0 or x >= width:
        return

    # Normalize y1 and y2 so we always draw top-to-bottom.
    # This handles both y1 < y2 and y2 < y1 cases.
    start = max(0, min(y1, y2))  # Clamp to top edge of grid.
    end = min(height - 1, max(y1, y2))  # Clamp to bottom edge of grid.
    
    # Draw the line character by character, preserving existing non-space characters.
    for y in range(start, end + 1):
        if grid[y][x] == " ":  # Only overwrite blank spaces.
            grid[y][x] = ch


def _put(grid: list[list[str]], x: int, y: int, ch: str) -> None:
    """Put a single character at (x, y) in the ASCII grid.
    
    This is used to place special markers (junction "+", arrowheads "<" ">") at
    specific positions. Unlike _draw_hline and _draw_vline, this *always*
    overwrites the existing character (even if it's not a space), so special
    markers take precedence over line segments.
    
    Args:
        grid: 2D character grid.
        x: Column index.
        y: Row index.
        ch: Character to place.
    """
    # Bounds check, then unconditionally overwrite (special markers take precedence).
    if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
        grid[y][x] = ch


def draw_connection_ascii(
    *,
    width: int,
    height: int,
    source_side: str,
    source_y: int,
    dest_side: str,
    dest_y: int,
    show_arrow: bool = True,
) -> list[str]:
    """Render a single source→dest connection as ASCII art.
    
    This is the main entry point for generating ASCII bus visualizations.
    The drawing strategy is intentionally simple and educational:
    
    1. A vertical "trunk" runs through the center of the canvas (the bus column).
    2. Horizontal "stubs" connect from the left/right edges to the trunk.
    3. Junction markers ("+") are placed where stubs meet the trunk.
    4. An arrowhead ("<" or ">") indicates the destination (data flow direction).
    
    Example output (source on left at y=2, dest on right at y=5):
        
                                   (trunk continues above)
        ----------+                (source stub at y=2, junction "+")
                  |                (trunk connects source to dest)
                  |                (trunk continues)
                  +----------->
                  |                (dest stub at y=5, junction "+", arrow ">")
                  |                (trunk continues below)
    
    The visual result makes data flow explicit: students can trace the path from
    source component through the trunk to the destination component.
    
    Args:
        width: Canvas width in characters.
        height: Canvas height in characters.
        source_side: "left" or "right" (side of bus where source component is).
        source_y: Source vertical position (0..height-1).
        dest_side: "left" or "right" (side of bus where destination component is).
        dest_y: Destination vertical position (0..height-1).
        show_arrow: Whether to draw an arrowhead at the destination edge.

    Returns:
        List of strings, each representing one row of the ASCII canvas.
    """

    # Ensure valid canvas dimensions (defensive).
    width = max(1, width)
    height = max(1, height)
    
    # Initialize the canvas as a 2D grid of spaces.
    # Each row is a list of characters; we'll modify this grid in place.
    grid: list[list[str]] = [[" "] * width for _ in range(height)]

    # Calculate key positions:
    # - Trunk runs down the center of the bus column.
    # - Edges are at the left and right boundaries of the canvas.
    trunk_x = width // 2
    left_edge = 0
    right_edge = width - 1

    # Helper function to get edge x-coordinate based on side.
    def edge_x(side: str) -> int:
        return left_edge if side == "left" else right_edge

    # Step 1: Draw horizontal stubs from source/dest endpoints to the trunk.
    # These are the horizontal lines that connect components to the bus.
    _draw_hline(grid, source_y, edge_x(source_side), trunk_x)
    _draw_hline(grid, dest_y, edge_x(dest_side), trunk_x)

    # Step 2: Draw the vertical trunk that connects the two stubs.
    # This is the main "bus line" that runs vertically through the widget.
    _draw_vline(grid, trunk_x, source_y, dest_y)

    # Step 3: Mark junction points where stubs meet the trunk with "+".
    # These junctions make the connection structure visually explicit.
    _put(grid, trunk_x, source_y, "+")
    _put(grid, trunk_x, dest_y, "+")

    # Step 4: Draw arrowhead at the destination edge (if requested).
    # The arrowhead indicates the direction of data flow.
    if show_arrow:
        if dest_side == "left":
            _put(grid, left_edge, dest_y, "<")  # Arrow pointing left.
        elif dest_side == "right":
            _put(grid, right_edge, dest_y, ">")  # Arrow pointing right.

    # Convert the 2D grid back to a list of strings (one per row).
    return ["".join(row) for row in grid]


def overlay_text(canvas: list[str], *, x: int, y: int, text: str) -> list[str]:
    """Overlay text onto an ASCII canvas.
    
    This is used to add labels (like component names or bus names) to the ASCII
    bus visualization. The text is placed at the specified position and will
    overwrite any existing characters in the canvas.
    
    The operation is best-effort: if the text extends beyond the canvas boundaries,
    it's clamped to fit. This ensures the function always succeeds even if the
    canvas is small or the position is near an edge.
    
    Args:
        canvas: List of strings representing the ASCII canvas.
        x: Starting column for the text.
        y: Row to place the text on.
        text: String to overlay.
    
    Returns:
        A new list of strings with the text overlaid.
    """

    # Empty canvas: nothing to overlay onto.
    if not canvas:
        return canvas

    # Convert canvas to a mutable 2D grid of characters.
    rows = [list(r) for r in canvas]
    height = len(rows)
    width = len(rows[0])

    # Y out of bounds: return unchanged canvas.
    if not (0 <= y < height):
        return canvas

    # Place each character of the text, clamping to canvas width.
    for i, ch in enumerate(text):
        px = x + i  # Column position for this character.
        if 0 <= px < width:  # Only place if within bounds.
            rows[y][px] = ch

    # Convert back to list of strings.
    return ["".join(r) for r in rows]
