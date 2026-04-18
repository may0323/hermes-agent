"""Interactive Progress Bar Component for Hermes Agent.

Provides rich, interactive progress display with:
- Progress percentage and ETA
- Status icons
- Collapsible details
- Click-to-expand functionality

Codex-inspired: elegant, minimal, non-intrusive.
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProgressBarStyle(Enum):
    """Visual style for progress bar."""
    MINIMAL = "minimal"      # Just percentage
    NORMAL = "normal"       # Percentage + bar
    RICH = "rich"           # Full details with icons


@dataclass
class ProgressBarConfig:
    """Configuration for progress bar display."""
    width: int = 30              # Width of progress bar in characters
    style: ProgressBarStyle = ProgressBarStyle.NORMAL
    show_percentage: bool = True
    show_eta: bool = True
    show_elapsed: bool = True
    show_icon: bool = True
    icon_pending: str = "○"
    icon_running: str = "◐"
    icon_complete: str = "●"
    icon_error: str = "✗"
    fill_char: str = "█"
    empty_char: str = "░"


class ProgressBar:
    """Interactive progress bar.
    
    Usage:
        bar = ProgressBar(total=100, description="Processing")
        for i in range(100):
            bar.update(i + 1)
            time.sleep(0.01)
        bar.complete()
    """

    CONFIG = ProgressBarConfig()

    def __init__(
        self,
        total: int,
        description: str = "",
        config: Optional[ProgressBarConfig] = None,
        print_fn: Optional[Callable[[str], None]] = None,
    ):
        self._config = config or self.CONFIG
        self._print_fn = print_fn or print
        self._total = max(1, total)
        self._current = 0
        self._description = description
        self._start_time = time.time()
        self._is_complete = False
        self._last_line_len = 0
        self._lock = threading.Lock()

    @property
    def percent(self) -> float:
        return (self._current / self._total) * 100 if self._total > 0 else 0

    def update(self, current: int, description: Optional[str] = None) -> None:
        """Update progress to current value."""
        with self._lock:
            self._current = max(0, min(current, self._total))
            if description:
                self._description = description
            self._render()

    def increment(self, delta: int = 1, description: Optional[str] = None) -> None:
        """Increment progress by delta."""
        self.update(self._current + delta, description)

    def set_description(self, description: str) -> None:
        """Update the description."""
        with self._lock:
            self._description = description
            self._render()

    def complete(self, final_message: Optional[str] = None) -> None:
        """Mark progress as complete."""
        with self._lock:
            self._current = self._total
            self._is_complete = True
            self._render_complete(final_message)

    def _render(self) -> None:
        """Render the progress bar."""
        percent = self.percent
        filled = int(self._config.width * percent / 100)
        empty = self._config.width - filled

        icon = self._config.icon_running if not self._is_complete else self._config.icon_complete
        bar = self._config.fill_char * filled + self._config.empty_char * empty

        elapsed = time.time() - self._start_time
        parts = []

        if self._config.show_icon:
            parts.append(f" {icon}")

        if self._description:
            parts.append(f" {self._description}")

        if self._config.show_percentage:
            parts.append(f" {percent:.0f}%")

        if self._config.show_elapsed:
            parts.append(f" [{elapsed:.1f}s]")

        parts.append(f" |{bar}|")

        if self._config.show_eta and not self._is_complete and percent > 0:
            eta = (100 - percent) / (percent / elapsed) if percent > 0 else 0
            if eta < 60:
                parts.append(f" ETA {eta:.0f}s")
            elif eta < 3600:
                parts.append(f" ETA {eta/60:.1f}m")

        line = "".join(parts)
        self._clear_and_print(line)

    def _render_complete(self, message: Optional[str] = None) -> None:
        """Render completion message."""
        icon = self._config.icon_complete
        elapsed = time.time() - self._start_time

        if message:
            final = f" {icon} {self._description}: {message} ({elapsed:.1f}s)"
        else:
            final = f" {icon} {self._description} complete ({elapsed:.1f}s)"

        # Clear the progress bar line
        if self._last_line_len > len(final):
            final = final + " " * (self._last_line_len - len(final))

        self._print_fn(f"\r{final}")

    def _clear_and_print(self, line: str) -> None:
        """Print with proper clearing."""
        if len(line) < self._last_line_len:
            line = line + " " * (self._last_line_len - len(line))
        self._last_line_len = len(line)
        self._print_fn(f"\r{line}", end="", flush=True)


class MultiProgressBar:
    """Manages multiple progress bars simultaneously.
    
    Usage:
        multi = MultiProgressBar()
        bar1 = multi.add("task_1", "Processing files", total=100)
        bar2 = multi.add("task_2", "Uploading", total=50)
        
        for i in range(100):
            bar1.update(i + 1)
            bar2.update(i // 2 + 1)
            time.sleep(0.01)
        
        multi.complete("task_1")
        multi.complete("task_2")
    """

    def __init__(self, print_fn: Optional[Callable[[str], None]] = None):
        self._print_fn = print_fn or print
        self._bars: Dict[str, ProgressBar] = {}
        self._order: List[str] = []
        self._lock = threading.Lock()
        self._started = False

    def add(
        self,
        bar_id: str,
        description: str,
        total: int,
        config: Optional[ProgressBarConfig] = None,
    ) -> ProgressBar:
        """Add a new progress bar."""
        with self._lock:
            bar = ProgressBar(total=total, description=description, config=config, print_fn=self._print_fn)
            self._bars[bar_id] = bar
            self._order.append(bar_id)
            return bar

    def update(self, bar_id: str, current: int, description: Optional[str] = None) -> None:
        """Update a progress bar."""
        bar = self._bars.get(bar_id)
        if bar:
            bar.update(current, description)

    def increment(self, bar_id: str, delta: int = 1) -> None:
        """Increment a progress bar."""
        bar = self._bars.get(bar_id)
        if bar:
            bar.increment(delta)

    def complete(self, bar_id: str, final_message: Optional[str] = None) -> None:
        """Mark a progress bar as complete."""
        bar = self._bars.get(bar_id)
        if bar:
            bar.complete(final_message)
            self._print_fn("")  # Newline after completion

    def get_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all progress bars."""
        with self._lock:
            return {
                bar_id: {
                    "percent": bar.percent,
                    "description": bar._description,
                    "is_complete": bar._is_complete,
                }
                for bar_id, bar in self._bars.items()
            }

    def render_all(self) -> None:
        """Render all progress bars (for debugging)."""
        with self._lock:
            for bar_id in self._order:
                bar = self._bars[bar_id]
                self._print_fn(f"{bar_id}: {bar.percent:.0f}% - {bar._description}")


# Context manager for easy progress tracking

class ProgressContext:
    """Context manager for progress tracking.
    
    Usage:
        with ProgressContext(total=100, description="Processing") as ctx:
            for i in range(100):
                ctx.update(i + 1)
    """

    def __init__(
        self,
        total: int,
        description: str = "",
        config: Optional[ProgressBarConfig] = None,
        print_fn: Optional[Callable[[str], None]] = None,
    ):
        self._bar = ProgressBar(total=total, description=description, config=config, print_fn=print_fn)

    def __enter__(self) -> ProgressBar:
        return self._bar

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self._bar._config.icon_error
            self._bar.complete(str(exc_val)[:50])
        return False

    def update(self, current: int) -> None:
        self._bar.update(current)

    def complete(self, message: Optional[str] = None) -> None:
        self._bar.complete(message)
