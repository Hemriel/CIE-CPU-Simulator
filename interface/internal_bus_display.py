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

        if not self.bus.last_active or not getattr(self.bus, "last_connection", None):
            return Text("\n".join(canvas), no_wrap=True)

        source_name, dest_name = self.bus.last_connection  # type: ignore[assignment]
        bus_region = safe_screen_region(self)
        if bus_region is None:
            return Text("\n".join(canvas), no_wrap=True)

        source_widget = self._endpoints.get(source_name)
        dest_widget = self._endpoints.get(dest_name)
        if source_widget is None or dest_widget is None:
            return Text("\n".join(canvas), no_wrap=True)

        source_region = safe_screen_region(source_widget)
        dest_region = safe_screen_region(dest_widget)
        if source_region is None or dest_region is None:
            return Text("\n".join(canvas), no_wrap=True)

        source_side = which_side(bus_region, source_region)
        dest_side = which_side(bus_region, dest_region)

        source_y_screen = widget_anchor_y(source_widget, mode="center")
        dest_y_screen = widget_anchor_y(dest_widget, mode="center")
        if source_y_screen is None or dest_y_screen is None:
            return Text("\n".join(canvas), no_wrap=True)

        source_y = max(0, min(height - 1, source_y_screen - bus_region.y))
        dest_y = max(0, min(height - 1, dest_y_screen - bus_region.y))

        canvas = draw_connection_ascii(
            width=width,
            height=height,
            source_side="left" if source_side == "left" else "right",
            source_y=source_y,
            dest_side="left" if dest_side == "left" else "right",
            dest_y=dest_y,
            show_arrow=True,
        )

        return Text("\n".join(canvas), no_wrap=True)

    def update_display(self) -> None:
        if self.bus.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        self.update(self._render_canvas())
