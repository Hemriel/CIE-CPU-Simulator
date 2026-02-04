"""ASCII visualization of external buses (address and data buses).

Responsibility:
- Displays connections on the external buses (address bus for memory selection,
  data bus for memory read/write).
- Handles special anchoring: address bus connects to the top of RAM (conceptually
  selects the entire memory), data bus connects to the active RAM row (conceptually
  transfers data to/from that specific word).
- Recomputes wire positions dynamically from live widget layout (responsive).

Entry point:
- The :class:`OuterBusDisplay` class, a Textual Static widget that renders
  ASCII bus connections.

Design note:
- Like all display components, this decouples front-end (ASCII rendering) from
  back-end (Bus control signals).
- Each outer bus (address and data) gets its own display widget, allowing them
  to use different anchoring modes for their respective purposes.
"""

from __future__ import annotations

from typing import Mapping

# Textual-specific imports. For more information, see https://textual.textualize.io/
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


class OuterBusDisplay(Static):
    """Display an external bus (address or data) with its active connection.
    
    External buses connect CPU components to RAM and I/O. Each bus gets its own
    widget for independent visualization.
    
    This widget is instantiated separately for each external bus with a title
    (e.g., "address-bus", "data-bus"), allowing different anchoring strategies
    for conceptual clarity.
    
    Attributes:
        bus: The Bus object holding connection metadata.
        title: Display title (e.g., "address-bus" for address bus widget).
        _endpoints: Mapping of ComponentName to widget for layout computation.
    """

    def __init__(self, bus: Bus, title: str, endpoints: Mapping[ComponentName, object]) -> None:
        """Initialize the external bus display widget.
        
        Args:
            bus: The Bus object whose connections should be visualized.
            title: Display title for this bus (used as the widget ID).
            endpoints: Mapping of component names to their widget objects for
                layout computation (used to find attachment points).
        """
        super().__init__()
        self.id = title
        self.bus = bus
        self.title = title
        self._endpoints = endpoints

    def on_mount(self) -> None:
        self.update_display()

    def on_resize(self) -> None:
        self.update_display()

    def _anchor_mode_for(self, component: ComponentName) -> str:
        """Determine the vertical anchoring mode for a component.
        
        Different components attach to different points on RAM to reflect their
        conceptual roles:
        - MAR (address) attaches to the top of RAM (selects memory address).
        - MDR (data) attaches to the active row (transfers to/from that word).
        - Other components default to center.
        
        Args:
            component: The component name to determine anchoring for.
        
        Returns:
            "top" for address bus anchoring, "ram_active_row" for data bus,
            or "center" for other components.
        """
        # User requirement:
        # - Address bus should connect MAR to the *top* of the RAM.
        # - RAM data bus should connect MDR to the *active row* in RAM.
        if component == ComponentName.RAM_ADDRESS:
            return "top"
        if component == ComponentName.RAM_DATA:
            return "ram_active_row"
        return "center"

    def _render_canvas(self) -> Text:
        """Render the ASCII bus visualization for the current transfer state.
        
        This method implements the outer bus rendering logic:
        1. Check if bus is active and has connections to visualize.
        2. Extract the single source and destination for this cycle.
        3. Compute layout positions using component-specific anchor modes.
        4. Draw the ASCII wire using the standard trunk-and-stub strategy.
        
        Unlike the internal bus, external buses always draw a single connection
        (no multi-source case) but use component-specific anchoring to show
        conceptual relationships (e.g., address bus to RAM top, data bus to
        active row).
        
        Returns:
            A Rich Text object containing the rendered ASCII canvas.
        """
        width = max(1, self.size.width)
        height = max(1, self.size.height)

        canvas = [" " * width for _ in range(height)]

        # Check if bus has an active transfer.
        connections = getattr(self.bus, "last_connections", [])
        if not self.bus.last_active or not connections:
            return Text("\n".join(canvas), no_wrap=True)

        # Outer bus currently draws a single connection per cycle.
        source_name, dest_name = connections[0]
        
        # Get the bus widget's region in screen coordinates.
        bus_region = safe_screen_region(self)
        if bus_region is None:
            return Text("\n".join(canvas), no_wrap=True)

        # Get both endpoint widgets.
        source_widget = self._endpoints.get(source_name)
        dest_widget = self._endpoints.get(dest_name)
        if source_widget is None or dest_widget is None:
            return Text("\n".join(canvas), no_wrap=True)

        # Get endpoint regions in screen coordinates.
        source_region = safe_screen_region(source_widget)
        dest_region = safe_screen_region(dest_widget)
        if source_region is None or dest_region is None:
            return Text("\n".join(canvas), no_wrap=True)

        # Determine which side of the bus each endpoint is on.
        source_side = which_side(bus_region, source_region)
        dest_side = which_side(bus_region, dest_region)

        # Compute anchor positions using component-specific modes.
        # This allows different components to attach at different points.
        source_y_screen = widget_anchor_y(source_widget, mode=self._anchor_mode_for(source_name))
        dest_y_screen = widget_anchor_y(dest_widget, mode=self._anchor_mode_for(dest_name))
        if source_y_screen is None or dest_y_screen is None:
            return Text("\n".join(canvas), no_wrap=True)

        # Convert from screen coordinates to canvas-relative coordinates.
        source_y = max(0, min(height - 1, source_y_screen - bus_region.y))
        dest_y = max(0, min(height - 1, dest_y_screen - bus_region.y))

        # Draw the connection using the standard trunk-and-stub strategy.
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
        """Update the display to reflect current bus state.
        
        Refreshes the canvas and toggles the 'inactive' CSS class based on whether
        the bus is currently active (has a transfer in progress).
        """
        if self.bus.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        self.update(self._render_canvas())
