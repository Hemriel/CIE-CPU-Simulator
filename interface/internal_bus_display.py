"""Textual widget for the inner data bus.

This widget draws an ASCII "wire" inside the bus column that connects the
currently active source component to the destination component.

The connection endpoints are computed dynamically from the live layout, so the
wire stays aligned when the terminal is resized.
"""

from __future__ import annotations

from typing import Mapping

from rich.text import Text
from textual.widgets import Static

from common.constants import ComponentName
from cpu.buses import Bus

from interface.bus_ascii import (
    draw_connection_ascii,
    safe_screen_region,
    widget_anchor_y,
    which_side,
)


class InternalBusDisplay(Static):
    """Draw the inner data bus and its currently active connection."""

    def __init__(self, bus: Bus, endpoints: Mapping[ComponentName, object]) -> None:
        super().__init__()
        self.id = "internal-bus-display"
        self.bus = bus
        self._endpoints = endpoints

    def on_mount(self) -> None:
        self.update_display()

    def on_resize(self) -> None:
        self.update_display()

    def _render_canvas(self) -> Text:
        width = max(1, self.size.width)
        height = max(1, self.size.height)

        # Default blank canvas.
        canvas = [" " * width for _ in range(height)]

        connections = getattr(self.bus, "last_connections", [])
        if not self.bus.last_active or not connections:
            return Text("\n".join(canvas), no_wrap=True)

        # Support 1 connection (typical RTN transfers) and multi-source connections
        # with a shared destination (ALU operations).
        dest_name = connections[0][1]
        source_names = [src for (src, dst) in connections if dst == dest_name]
        bus_region = safe_screen_region(self)
        if bus_region is None:
            return Text("\n".join(canvas), no_wrap=True)

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
        dest_y = max(0, min(height - 1, dest_y_screen - bus_region.y))
        dest_side_norm = "left" if dest_side == "left" else "right"

        # Collect sources (skip any missing endpoints).
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

        # Single-connection case.
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
        trunk_x = width // 2
        left_edge = 0
        right_edge = width - 1

        def edge_x(side: str) -> int:
            return left_edge if side == "left" else right_edge

        ys = [y for _, y in source_points] + [dest_y]
        y_min, y_max = min(ys), max(ys)

        grid = [list(row) for row in canvas]

        # Vertical trunk.
        for y in range(y_min, y_max + 1):
            if grid[y][trunk_x] == " ":
                grid[y][trunk_x] = "|"

        # Source stubs.
        for side, y in source_points:
            ex = edge_x(side)
            x1, x2 = (ex, trunk_x) if ex <= trunk_x else (trunk_x, ex)
            for x in range(x1, x2 + 1):
                if grid[y][x] == " ":
                    grid[y][x] = "-"
            grid[y][trunk_x] = "+"

        # Destination stub + arrow.
        dex = edge_x(dest_side_norm)
        x1, x2 = (dex, trunk_x) if dex <= trunk_x else (trunk_x, dex)
        for x in range(x1, x2 + 1):
            if grid[dest_y][x] == " ":
                grid[dest_y][x] = "-"
        grid[dest_y][trunk_x] = "+"
        grid[dest_y][dex] = "<" if dest_side_norm == "left" else ">"

        canvas = ["".join(r) for r in grid]
        return Text("\n".join(canvas), no_wrap=True)

    def update_display(self) -> None:
        if self.bus.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        self.update(self._render_canvas())
