"""Ticker and animation control for auto-paced compilation and CPU execution.

Responsibility:
- Manage a continuously repeating timer (ticker) that drives the main event loop
  for stepping through assembly and CPU execution.
- Provide pause/resume control so users can step manually (one RTN step at a time)
  or auto-progress at a configurable speed.
- Allow dynamic speed adjustment (faster/slower) with logarithmic scaling to provide
  fine-grained control at slow speeds and coarse control at fast speeds.

Design note:
- The ticker uses Textual's `set_interval()` to schedule callbacks at regular
  intervals. The interval (in seconds) controls the time between ticks.
- Speed adjustment uses logarithmic bucketing: different delta values apply
  depending on the current interval. This ensures that speed changes are
  perceptually smooth (e.g., speeding up from 0.05s is a small change; speeding up
  from 5.0s is a large change, but both feel like similar increments to the user).
- The ticker can be paused/resumed while maintaining the current interval setting.
- When interval changes, the ticker is restarted to apply the new timing immediately.

Timing model:
- Minimum interval (fastest): 0.01 seconds (100 ticks/second)
- Maximum interval (slowest): 10.0 seconds (0.1 ticks/second)
- Default interval: 1.0 seconds (1 tick/second)
- Each tick triggers one step: either one assembly state transition or one RTN step.

Entry points / public API:
- `TickerController` class for managing ticker state and speed.
  - `start(tick_callback)`: Begin ticking with a callback.
  - `pause()`, `resume()`, `toggle()`: Control animation state.
  - `increase_speed()`, `decrease_speed()`: Adjust ticker speed.
  - `set_interval()`, `get_interval()`: Direct interval control.
  - `is_running()`: Check current state.

Contained items:
- Speed adjustment tables (SPEED_UP, SPEED_DOWN) for interval bucketing.
- Ticker management methods with automatic restart on interval changes.
"""

from typing import Callable


class TickerController:
    """Manages auto-progress ticker (speed, pause/resume).
    
    Responsibilities:
    - Ticker interval management
    - Pause/resume control
    - Speed adjustment (increase/decrease)
    - Running state tracking
    """

    # Configuration constants
    DEFAULT_INTERVAL = 1.0
    MAX_INTERVAL = 10.0
    MIN_INTERVAL = 0.01
    DELTA_DIRECTIONS = {"UP", "DOWN"}

    # Speed adjustment bands: maps interval ranges to adjustment deltas.
    # Separate UP/DOWN tables handle hysteresis at boundaries: when increasing speed
    # (UP), larger jumps happen at slightly higher thresholds than when decreasing
    # speed (DOWN). This creates a comfortable "sweet spot" where users can fine-tune
    # around key speeds without overshooting.
    #
    # The thresholds have intentional margins (e.g., 5.1 vs 4.99) to handle Python
    # float precision: after arithmetic operations, 2.0 may become 2.0000001 or
    # 1.9999999, and the margins ensure consistent behavior regardless of rounding.
    #
    # Tuples: (interval_threshold, delta_when_interval_above_threshold)
    # Read as: "if interval >= 5.1 (when going UP), use delta=1.0"
    SPEED_BANDS = {
        "UP": [(5.1, 1.0), (2.1, 0.5), (0.11, 0.1), (0.0, 0.01)],
        "DOWN": [(4.99, 1.0), (1.99, 0.5), (0.099, 0.1), (0.0, 0.01)],
    }

    def speed_delta(self, direction: str) -> float:
        """Determine delta from the lookup table for the given direction.
        
        Looks up the appropriate speed adjustment delta (0.01, 0.1, 0.5, or 1.0)
        based on the current interval and the direction of adjustment (UP=faster,
        DOWN=slower). The direction determines which threshold table to use,
        enabling hysteresis for comfortable boundary behavior.
        
        Args:
            direction: "UP" (increasing speed) or "DOWN" (decreasing speed)
        
        Returns:
            float: The delta to apply (0.01, 0.1, 0.5, or 1.0)
        """
        for threshold, delta in self.SPEED_BANDS[direction]:
            if self.interval >= threshold:
                return delta
        return 0.01  # Fallback (should not reach here if bands are complete)

    def __init__(self, app):
        """Initialize the ticker controller.
        
        Args:
            app: Reference to the main app for ticker management
        """
        self.app = app
        self.interval = self.DEFAULT_INTERVAL
        self.running = False
        self._ticker = None
        self._tick_callback = None

    def start(self, tick_callback: Callable) -> None:
        """Start the ticker with a callback.
        
        Args:
            tick_callback: Callback function to call on each tick
        """
        self._tick_callback = tick_callback
        if self._ticker:
            self._ticker.stop()
        self._ticker = self.app.set_interval(
            self.interval,
            tick_callback,
            pause=not self.running
        )

    def pause(self) -> None:
        """Pause the ticker."""
        self.running = False
        if self._ticker:
            self._ticker.pause()

    def resume(self) -> None:
        """Resume the ticker."""
        self.running = True
        if self._ticker:
            self._ticker.resume()

    def toggle(self) -> bool:
        """Toggle running state.
        
        Returns:
            bool: New running state
        """
        if self.running:
            self.pause()
        else:
            self.resume()
        return self.running

    def increase_speed(self) -> float:
        """Increase speed (decrease interval).
        
        Looks up the appropriate delta for the UP direction based on the current
        interval, then subtracts it from the interval. Smaller intervals = faster
        ticking. The delta size is determined by the current interval: faster
        speeds use smaller deltas for fine control, slower speeds use larger
        deltas for coarser jumps.
        
        Returns:
            float: New interval value (clamped to MIN_INTERVAL)
        """
        # Look up delta from UP band, subtract from interval (makes it smaller/faster)
        self.interval = max(self.MIN_INTERVAL, self.interval - self.speed_delta("UP"))
        self._restart_ticker()
        return self.interval

    def decrease_speed(self) -> float:
        """Decrease speed (increase interval).
        
        Looks up the appropriate delta for the DOWN direction based on the current
        interval, then adds it to the interval. Larger intervals = slower ticking.
        The boundary thresholds differ from increase_speed to provide hysteresis:
        this prevents rapid oscillation when adjusting speed near critical values.
        
        Returns:
            float: New interval value (clamped to MAX_INTERVAL)
        """
        # Look up delta from DOWN band, add to interval (makes it larger/slower)
        self.interval = min(self.MAX_INTERVAL, self.interval + self.speed_delta("DOWN"))
        self._restart_ticker()
        return self.interval

    def set_interval(self, interval: float) -> None:
        """Set the ticker interval directly.
        
        Args:
            interval: New interval in seconds
        """
        interval = max(self.MIN_INTERVAL, min(self.MAX_INTERVAL, interval))
        self.interval = interval
        self._restart_ticker()

    def get_interval(self) -> float:
        """Get the current ticker interval.
        
        Returns:
            float: Current interval in seconds
        """
        return self.interval

    def is_running(self) -> bool:
        """Check if ticker is running.
        
        Returns:
            bool: True if ticker is running
        """
        return self.running

    def _restart_ticker(self) -> None:
        """Restart ticker with current interval and preserve running state."""
        if self._ticker and self._tick_callback:
            was_running = self.running
            self._ticker.stop()
            # Recreate ticker with new interval
            self._ticker = self.app.set_interval(
                self.interval,
                self._tick_callback,
                pause=not was_running
            )
            self.running = was_running

def test_deltas():
    """Test speed delta calculations for correctness."""
    controller = TickerController(None)

    up_inner_test = [
        "up_inner_tests",
        [
        (6.0, 1.0),
        (3.0, 0.5),
        (1, 0.1),
        (0.05, 0.01),
        ]
    ]

    up_boundary_tests = [
        "up_boundary_tests",
        [
        (10.0, 1.0),
        (5.0, 0.5),
        (2.0, 0.1),
        (0.1, 0.01),
        (0.01, 0.01),
        ]
    ]

    down_inner_tests = [
        "down_inner_tests",
        [
        (0.05, 0.01),
        (1, 0.1),
        (3.0, 0.5),
        (6.0, 1.0),
        ]
    ]
    
    down_boundary_tests = [
        "down_boundary_tests",
        [
        (10.0, 1.0),
        (5.0, 1),
        (2.0, 0.5),
        (0.1, 0.1),
        (0.01, 0.01),
        ]
    ]

    test_scenarios = [
        up_inner_test,
        up_boundary_tests,
        down_inner_tests,
        down_boundary_tests,
    ]
    for (scenario_name, tests) in test_scenarios:
        for (interval, expected_delta) in tests:
            controller.interval = interval
            direction = "UP" if "up" in scenario_name else "DOWN"
            delta = controller.speed_delta(direction)
            assert delta == expected_delta, f"Failed {scenario_name} for interval={interval}: expected {expected_delta}, got {delta}"
        print(f"All tests passed for {scenario_name}")

    print("All delta tests passed.")

if __name__ == "__main__":
    test_deltas()