"""ASCII bus rendering helpers for the Textual CPU UI.

This module is responsible for turning a high-level *connection* (source component
→ destination component) into an ASCII "wire" drawn inside a bus column widget.

The UI layout in this project is responsive: widget positions change as the
terminal is resized. Therefore we compute attachment points from Textual's live
layout geometry (screen regions) on every render.

The drawing strategy is intentionally simple and educational:

- A single vertical "trunk" runs through the middle of the bus widget.
- Each endpoint is connected to the trunk by a horizontal stub.
- A small arrowhead is drawn on the destination side.

This is not a full-screen overlay; each bus draws *inside its own widget*.

Visual conventions
------------------

- The bus widget draws a vertical trunk at its center.
- Endpoints connect to the trunk via horizontal stubs.
- The destination endpoint gets an arrowhead.

RAM-specific anchoring (per project requirement)
------------------------------------------------

- Address bus connects `MAR` to the *top* of the RAM column.
- RAM data bus connects `MDR` to the currently active RAM word (the DataTable
    cursor row).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from textual.geometry import Region


@dataclass(frozen=True)
class ScreenPoint:
    """A point in screen coordinates.

    Attributes:
        x: Column (0-based) in the terminal.
        y: Row (0-based) in the terminal.
    """

    x: int
    y: int


def safe_screen_region(widget: Any) -> Region | None:
    """Best-effort fetch of a widget's screen-space region.

    Textual's API has evolved over time. In modern versions, widgets expose
    `screen_region`. If that isn't available, we fall back to `region` which is
    usually relative to the parent (and may not be usable for cross-widget math).

    Args:
        widget: Any Textual widget.

    Returns:
        A Region in screen coordinates if available, otherwise None.
    """

    region = getattr(widget, "region", None)
    if region is not None:
        x, y = int(region.x), int(region.y)
        parent = getattr(widget, "parent", None)
        while parent is not None:
            parent_region = getattr(parent, "region", None)
            if parent_region is not None:
                x += int(parent_region.x)
                y += int(parent_region.y)
            parent = getattr(parent, "parent", None)
        return Region(x, y, int(region.width), int(region.height))

    return None


def widget_anchor_y(widget: Any, *, mode: str = "center") -> int | None:
    """Compute an anchor Y position for a widget in screen coordinates.

    Supported modes:
        - "center": vertical center of widget
        - "top": top row of widget
        - "ram_active_row": DataTable cursor row inside the widget

    Returns:
        The anchor y (screen coordinates), or None if it can't be computed.
    """

    region = safe_screen_region(widget)
    if region is None:
        return None

    if mode == "top":
        return region.y

    if mode == "center":
        return region.y + max(0, region.height // 2)

    if mode == "ram_active_row":
        # The RAM table uses move_cursor(row=...) each refresh; we interpret that
        # as the active memory word and attach the data bus to that row.
        cursor_row = getattr(widget, "cursor_row", None)
        if cursor_row is None:
            cursor = getattr(widget, "cursor_coordinate", None)
            if cursor is not None:
                cursor_row = getattr(cursor, "row", None)
        if cursor_row is None:
            return region.y + max(0, region.height // 2)

        # DataTable has a header row. We assume 1 line of header.
        header_height = 1
        y = region.y + header_height + int(cursor_row)
        # Clamp into the widget region.
        return max(region.y, min(region.y + region.height - 1, y))

    raise ValueError(f"Unknown anchor mode: {mode}")


def which_side(bus_region: Region, widget_region: Region) -> str:
    """Determine whether `widget_region` lies left/right of the bus widget."""

    if widget_region.x + widget_region.width <= bus_region.x:
        return "left"
    if widget_region.x >= bus_region.x + bus_region.width:
        return "right"
    # Overlapping or inside the bus column; treat as center.
    return "center"


def _draw_hline(grid: list[list[str]], y: int, x1: int, x2: int, ch: str = "-") -> None:
    if y < 0 or y >= len(grid):
        return
    width = len(grid[0]) if grid else 0
    if width <= 0:
        return

    start = max(0, min(x1, x2))
    end = min(width - 1, max(x1, x2))
    for x in range(start, end + 1):
        if grid[y][x] == " ":
            grid[y][x] = ch


def _draw_vline(grid: list[list[str]], x: int, y1: int, y2: int, ch: str = "|") -> None:
    height = len(grid)
    if height <= 0:
        return
    width = len(grid[0])
    if x < 0 or x >= width:
        return

    start = max(0, min(y1, y2))
    end = min(height - 1, max(y1, y2))
    for y in range(start, end + 1):
        if grid[y][x] == " ":
            grid[y][x] = ch


def _put(grid: list[list[str]], x: int, y: int, ch: str) -> None:
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
    """Render a single source→dest connection as ASCII.

    Args:
        width: Canvas width.
        height: Canvas height.
        source_side: "left" or "right" (relative to the bus widget).
        source_y: Source y (0..height-1).
        dest_side: "left" or "right".
        dest_y: Destination y (0..height-1).
        show_arrow: Whether to draw an arrowhead at the destination edge.

    Returns:
        List of strings, each a row of the canvas.
    """

    width = max(1, width)
    height = max(1, height)
    grid: list[list[str]] = [[" "] * width for _ in range(height)]

    trunk_x = width // 2
    left_edge = 0
    right_edge = width - 1

    def edge_x(side: str) -> int:
        return left_edge if side == "left" else right_edge

    # Draw stubs from endpoints to the trunk.
    _draw_hline(grid, source_y, edge_x(source_side), trunk_x)
    _draw_hline(grid, dest_y, edge_x(dest_side), trunk_x)

    # Draw the vertical trunk that connects the two junctions.
    _draw_vline(grid, trunk_x, source_y, dest_y)

    # Junction markers where stubs meet trunk.
    _put(grid, trunk_x, source_y, "+")
    _put(grid, trunk_x, dest_y, "+")

    if show_arrow:
        if dest_side == "left":
            _put(grid, left_edge, dest_y, "<")
        elif dest_side == "right":
            _put(grid, right_edge, dest_y, ">")

    return ["".join(row) for row in grid]


def overlay_text(canvas: list[str], *, x: int, y: int, text: str) -> list[str]:
    """Overlay small text onto a canvas (best-effort, clamped)."""

    if not canvas:
        return canvas

    rows = [list(r) for r in canvas]
    height = len(rows)
    width = len(rows[0])

    if not (0 <= y < height):
        return canvas

    for i, ch in enumerate(text):
        px = x + i
        if 0 <= px < width:
            rows[y][px] = ch

    return ["".join(r) for r in rows]
