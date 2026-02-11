"""Visual display component for the I/O queue state.

Responsibility:
- Display the current I/O contents and last control signal for an I/O component.
- Highlight when the I/O component is active vs. idle during execution.
- Provide an input prompt mechanism that blocks until the user submits text.

Entry point:
- :class:`IODisplay`: Main widget bound to an I/O instance.

Design choices:
- The back end I/O component doesn't know about the UI; instead, it uses a
    displayer hook to notify the UI when its state changes.
- The IODisplay uses a queue to bridge Textual's async event system with the
    synchronous read() method. When the user submits input, the value is enqueued,
    allowing read() to block and wait for user input using queue.get().
"""

from cpu.cpu_io import IO  # the displayer needs to know about the I/O it displays
import queue
from time import sleep

# textual specific imports. For more information, see https://textual.textualize.io/
from textual.widgets import Input


class IODisplay(Input):
    """Visual widget that displays I/O contents during execution.

    Shows the current character queue and the last control signal, and highlights
    active vs. idle periods. Also handles blocking input prompts via a queue.
    """

    def __init__(self, io_element: IO, label: str, reversed : bool = False) -> None:
        """Create an I/O display bound to the given I/O instance.

        Args:
            io_element: The I/O component to visualize.
            label: The label shown in the UI border (e.g., "IN" or "OUT").
            reversed: Whether to reverse the displayed string for right-to-left layouts.
        """
        super().__init__()
        self.id = label
        self.io_element = io_element
        self.border_title = label
        self.reversed = reversed
        # Queue for bridging async UI events with synchronous read() calls
        self.input_queue: queue.Queue[str] = queue.Queue()

    def on_mount(self) -> None:
        """Initialize the display once the widget is mounted.
        
        Registers this widget as the displayer for the IO component so that
        blocking input prompts can be routed through the UI.
        """
        # Register this widget as the displayer so IO.read() can prompt for input
        self.io_element.displayer = self
        if self.id == "output-port":
            self.read_only = True
        self.update_display()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle when user submits input by pressing Enter.
        
        This is called by Textual whenever the user presses Enter in the Input widget.
        The submitted text is enqueued so that the synchronous read() method can
        retrieve it via prompt_user_for_input().
        
        Args:
            event: The Input.Submitted event containing the submitted value.
        """
        user_input = event.value
        if user_input:
            # Enqueue the input so read() can retrieve it
            self.input_queue.put(user_input)
            # Clear the input field for the next entry
            self.value = ""
            # Remove the red "waiting" styling now that input is available
            self.remove_class("awaiting-input")

    def prompt_user_for_input(self) -> str:
        """Block until the user submits input via the Input widget.
        
        This method is called by the IO component's read() method when the input
        queue is empty. It blocks in a synchronous manner, allowing the UI to remain
        responsive while waiting for user input.
        
        Returns:
            The string that the user submitted (may be empty if cancelled).
        """
        # Add visual feedback: turn the input field red while waiting
        self.add_class("awaiting-input")
        self.border_subtitle = "waiting for input..."
        
        # Block until user submits input (queue.get() blocks)
        user_input = self.input_queue.get()
        
        # Remove waiting styling once input is received
        self.remove_class("awaiting-input")
        self.border_subtitle = "idle"
        
        return user_input

    def update_display(self) -> None:
        """Refresh the display with current I/O state.

        Updates the visible contents, shows the last control signal, and applies
        active/idle styling.
        """
        # Apply active/inactive styling based on RTN step participation
        if self.io_element.last_active:
            self.remove_class("inactive")
        else:
            self.add_class("inactive")
        
        # Update displayed values
        value = getattr(self.io_element, "contents", "")
        control = getattr(self.io_element, "_control", None)
        self.border_subtitle = f"{control or 'idle'}"
        self.content = f"{value[::-1] if self.reversed else value}"
'''
    async def prompt_user_for_input(self) -> str:
        """Prompt the user for input when the I/O queue is empty.

        This method can be customized to integrate with the UI framework
        to get user input during simulation.

        Returns:
            A single character string input by the user.
        """
        self.add_class("awaiting-input")
        self.placeholder = "Input required..."
        self.focus()
        self.awaiting_input = True
        self.read_only = False

        await self.wait_for_input()
        
        self.read_only = True
        self.awaiting_input = False
        self.remove_class("awaiting-input")

        user_input = self.value
        self.value = ""  # Clear the input field after reading
        return user_input if user_input else ""
    
    async def wait_for_input(self):
        """Wait for user input asynchronously.

        This is a placeholder method. The actual implementation would depend
        on the UI framework's event loop and input handling.
        """
        while self.awaiting_input:
            sleep(0.1)

    '''