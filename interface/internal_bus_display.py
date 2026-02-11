"""ASCII visualization of the internal (data) bus within the CPU.

Responsibility:
- Displays the currently active data transfer on the internal bus.
- Handles both single-source and multi-source connections (e.g., ALU operations
  where multiple registers feed into one destination).
- Recomputes wire positions dynamically from live widget layout (responsive).

Entry point:
- The :class:`InternalBusDisplay` class, a Textual Static widget that renders
  ASCII bus connections inside the bus column.

Design note:
- Like all display components, this decouples the front-end (ASCII rendering)
  from the back-end (Bus control signals). The Bus object holds the connection
  metadata; this widget just visualizes it.
- Special handling: Multi-source connections (where several components feed
  into one destination) draw a shared vertical trunk with multiple stubs, making
  data aggregation visually explicit (e.g., ALU receiving inputs from ACC and IX).
"""

from __future__ import annotations

from typing import Mapping

# Textual-specific imports. For more information, see https://textual.textualize.io/
from rich.text import Text
from textual.widgets import Static

from common.constants import ComponentName
from simulator.buses import Bus

from interface.bus_ascii import (
    draw_connection_ascii,
    safe_screen_region,
    widget_anchor_y,
    which_side,
)


class InternalBusDisplay(Static):
    """Display the internal data bus with currently active connection.
    
    This widget renders the active transfer on the internal bus. Unlike simpler
    register displays, it must handle two distinct cases:
    - Single source → destination (typical RTN transfer like ACC → MAR).
    - Multiple sources → one destination (ALU aggregation like ACC + IX → ALU).
    
    In the multi-source case, the widget draws a shared trunk with all source
    stubs feeding into it, making it visually clear that multiple sources
    contribute to one operation.
    
    The widget updates on resize to recompute endpoint positions from the live
    layout, ensuring the bus stays aligned when the terminal changes size.
    
    Attributes:
        bus: The Bus object holding connection metadata.
        _endpoints: Mapping of ComponentName to widget for layout computation.
    """

    def __init__(self, bus: Bus, endpoints: Mapping[ComponentName, object]) -> None:
        """Initialize the internal bus display widget.
        
        Args:
            bus: The Bus object whose connections should be visualized.
            endpoints: Mapping of component names to their widget objects for
                layout computation (used to find attachment points).
        """
        super().__init__()
        self.id = "internal-bus-display"
        self.bus = bus
        self._endpoints = endpoints

    def on_mount(self) -> None:
        self.update_display()

    def on_resize(self) -> None:
        self.update_display()

    def _render_canvas(self) -> Text:
        """Render the ASCII bus visualization for the current transfer state.
        
        This method implements the core rendering logic:
        1. Check if bus is active and has connections to visualize.
        2. Extract the destination and all sources for this cycle.
        3. Compute layout positions (screen coordinates → canvas-relative).
        4. For single source: use simple trunk-and-stub drawing.
        5. For multiple sources: draw shared trunk with multiple stubs.
        
        Returns:
            A Rich Text object containing the rendered ASCII canvas.
        """
        width = max(1, self.size.width)
        height = max(1, self.size.height)

        # Default blank canvas.
        canvas = [" " * width for _ in range(height)]

        # Check if bus has an active transfer.
        connections = getattr(self.bus, "last_connections", [])
        if not self.bus.last_active or not connections:
            return Text("\n".join(canvas), no_wrap=True)

        # Extract destination (same for all connections in this cycle).
        # Support 1 connection (typical RTN transfers) and multi-source connections
        # with a shared destination (ALU operations).
        dest_name = connections[0][1]
        source_names = [src for (src, dst) in connections if dst == dest_name]
        
        # Get the bus widget's region in screen coordinates.
        bus_region = safe_screen_region(self)
        if bus_region is None:
            return Text("\n".join(canvas), no_wrap=True)

        # Compute destination position.
        dest_widget = self._endpoints.get(dest_name)
        if dest_widget is None:
            return Text("\n".join(canvas), no_wrap=True)
        dest_region = safe_screen_region(dest_widget)
        if dest_region is None:
            return Text("\n".join(canvas), no_wrap=True)

        dest_side = which_side(bus_region, dest_region)
        dest_y_screen = widget_anchor_y(dest_widget, mode="center")
        if dest_y_screen is None:
            return Text("\n".join(canvas), no_wrap=True)
        
        # Convert from screen coordinates to canvas-relative coordinates.
        dest_y = max(0, min(height - 1, dest_y_screen - bus_region.y))
        dest_side_norm = "left" if dest_side == "left" else "right"

        # Collect all source positions (skip any missing endpoints).
        source_points: list[tuple[str, int]] = []
        for source_name in source_names:
            source_widget = self._endpoints.get(source_name)
            if source_widget is None:
                continue
            source_region = safe_screen_region(source_widget)
            if source_region is None:
                continue
            source_side = which_side(bus_region, source_region)
            source_y_screen = widget_anchor_y(source_widget, mode="center")
            if source_y_screen is None:
                continue
            source_y = max(0, min(height - 1, source_y_screen - bus_region.y))
            source_points.append(("left" if source_side == "left" else "right", source_y))

        if not source_points:
            return Text("\n".join(canvas), no_wrap=True)

        # Single-connection case: use the standard trunk-and-stub drawing.
        if len(source_points) == 1:
            source_side_norm, source_y = source_points[0]
            canvas = draw_connection_ascii(
                width=width,
                height=height,
                source_side=source_side_norm,
                source_y=source_y,
                dest_side=dest_side_norm,
                dest_y=dest_y,
                show_arrow=True,
            )
            return Text("\n".join(canvas), no_wrap=True)

        # Multi-source to one destination: draw a shared trunk and multiple stubs.
        # This happens in operations like ALU where two inputs feed into one output.
        trunk_x = width // 2
        left_edge = 0
        right_edge = width - 1

        def edge_x(side: str) -> int:
            return left_edge if side == "left" else right_edge

        # Find the bounding y range for all sources and destination.
        ys = [y for _, y in source_points] + [dest_y]
        y_min, y_max = min(ys), max(ys)

        # Convert canvas strings back to a mutable grid for drawing.
        grid = [list(row) for row in canvas]

        # Draw the shared vertical trunk spanning all sources and destination.
        for y in range(y_min, y_max + 1):
            if grid[y][trunk_x] == " ":
                grid[y][trunk_x] = "|"

        # Draw stubs from each source to the trunk, marking junctions.
        for side, y in source_points:
            ex = edge_x(side)
            x1, x2 = (ex, trunk_x) if ex <= trunk_x else (trunk_x, ex)
            for x in range(x1, x2 + 1):
                if grid[y][x] == " ":
                    grid[y][x] = "-"
            grid[y][trunk_x] = "+"  # Junction marker.

        # Draw the destination stub + arrow (indicates data flow direction).
        dex = edge_x(dest_side_norm)
        x1, x2 = (dex, trunk_x) if dex <= trunk_x else (trunk_x, dex)
        for x in range(x1, x2 + 1):
            if grid[dest_y][x] == " ":
                grid[dest_y][x] = "-"
        grid[dest_y][trunk_x] = "+"  # Junction marker.
        grid[dest_y][dex] = "<" if dest_side_norm == "left" else ">"  # Arrowhead.

        canvas = ["".join(r) for r in grid]
        return Text("\n".join(canvas), no_wrap=True)

    def update_display(self) -> None:
        """Update the display to reflect current bus state.
        
        Refreshes the canvas and toggles the 'inactive' CSS class based on whether
        the bus is currently active (has a transfer in progress).
        """
        if self.bus.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        self.update(self._render_canvas())
