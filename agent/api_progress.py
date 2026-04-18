"""API Call Progress Tracker for Hermes Agent.

Tracks streaming responses and token usage with elegant, Codex-inspired feedback.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Tracks token usage for an API call."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": self.input_tokens,
            "output": self.output_tokens,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total": self.total,
        }


@dataclass
class APIProgressTracker:
    """Tracks progress of a single API call."""
    id: str
    model: str
    start_time: float = field(default_factory=time.time)
    stream_started: bool = False
    first_token_time: Optional[float] = None
    last_token_time: float = field(default_factory=time.time)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    chunks_received: int = 0
    estimated_output_tokens: int = 0
    is_complete: bool = False

    @property
    def tokens_per_second(self) -> float:
        """Calculate streaming speed."""
        if not self.stream_started or self.first_token_time is None:
            return 0
        elapsed = self.last_token_time - self.first_token_time
        if elapsed <= 0:
            return 0
        return self.chunks_received / elapsed

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    def update_from_response(self, response_data: Dict[str, Any]) -> None:
        """Update from API response data."""
        if "usage" in response_data:
            usage = response_data["usage"]
            self.token_usage.input_tokens = usage.get("prompt_tokens", 0)
            self.token_usage.output_tokens = usage.get("completion_tokens", 0)
            if "cache_hits" in usage:
                self.token_usage.cache_hits = usage.get("cache_hits", 0)
            if "cache_misses" in usage:
                self.token_usage.cache_misses = usage.get("cache_misses", 0)

        if hasattr(response_data, "model"):
            self.model = getattr(response_data, "model", self.model)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model": self.model,
            "elapsed": round(self.elapsed_time, 2),
            "tokens_per_second": round(self.tokens_per_second, 1),
            "chunks_received": self.chunks_received,
            "is_streaming": self.stream_started and not self.is_complete,
            "usage": self.token_usage.to_dict(),
        }


class APICallProgressCallback:
    """Callback for API call progress updates.
    
    Codex-inspired: shows model name, streaming indicator, and token count.
    """

    def __init__(
        self,
        print_fn: Optional[Callable[[str], None]] = None,
        show_tokens: bool = True,
        show_speed: bool = True,
    ):
        self._print_fn = print_fn or print
        self._show_tokens = show_tokens
        self._show_speed = show_speed
        self._active_trackers: Dict[str, APIProgressTracker] = {}
        self._lock = threading.Lock()
        self._last_lines: Dict[str, str] = {}

    def start_tracking(self, call_id: str, model: str) -> APIProgressTracker:
        """Start tracking an API call."""
        tracker = APIProgressTracker(id=call_id, model=model)
        with self._lock:
            self._active_trackers[call_id] = tracker
        self._print_start(tracker)
        return tracker

    def on_stream_start(self, call_id: str) -> None:
        """Called when streaming starts."""
        with self._lock:
            tracker = self._active_trackers.get(call_id)
        if tracker:
            tracker.stream_started = True
            tracker.first_token_time = time.time()

    def on_token(self, call_id: str, chunk_size: int = 1) -> None:
        """Called for each token received."""
        with self._lock:
            tracker = self._active_trackers.get(call_id)
        if tracker:
            tracker.chunks_received += chunk_size
            tracker.last_token_time = time.time()
            self._print_progress(tracker)

    def on_complete(self, call_id: str, response_data: Optional[Dict[str, Any]] = None) -> None:
        """Called when API call completes."""
        with self._lock:
            tracker = self._active_trackers.get(call_id)
            if tracker:
                tracker.is_complete = True
                if response_data:
                    tracker.update_from_response(response_data)
                del self._active_trackers[call_id]
        self._print_complete(tracker)

    def on_error(self, call_id: str, error: str) -> None:
        """Called when API call fails."""
        with self._lock:
            tracker = self._active_trackers.get(call_id)
            if tracker:
                tracker.is_complete = True
                del self._active_trackers[call_id]
        self._print_error(tracker, error)

    def _print_start(self, tracker: APIProgressTracker) -> None:
        """Print start message."""
        self._print_fn(f"  → {tracker.model}: waiting for response...")

    def _print_progress(self, tracker: APIProgressTracker) -> None:
        """Print progress update."""
        parts = [f"  ⏳ {tracker.model}:"]

        if tracker.stream_started:
            parts.append(f"streaming")
            parts.append(f"{tracker.chunks_received} tokens")

        if self._show_speed and tracker.tokens_per_second > 0:
            parts.append(f"({tracker.tokens_per_second:.1f} tok/s)")

        if self._show_tokens and tracker.token_usage.total > 0:
            parts.append(f"| cache: {tracker.token_usage.cache_hits}")

        parts.append(f"[{tracker.elapsed_time:.1f}s]")

        line = " ".join(parts)
        self._clear_and_print(line, tracker.id)

    def _print_complete(self, tracker: Optional[APIProgressTracker]) -> None:
        """Print completion message."""
        if tracker is None:
            return
        usage = tracker.token_usage
        elapsed = tracker.elapsed_time
        speed = usage.output_tokens / elapsed if elapsed > 0 else 0

        if self._show_tokens:
            cache_info = ""
            if usage.cache_hits > 0 or usage.cache_misses > 0:
                cache_info = f" | cache hits: {usage.cache_hits}"
            self._print_fn(f"  ✓ {tracker.model}: +{usage.output_tokens} tokens{cache_info} ({speed:.1f} tok/s)")
        else:
            self._print_fn(f"  ✓ {tracker.model}: done ({elapsed:.1f}s)")

    def _print_error(self, tracker: Optional[APIProgressTracker], error: str) -> None:
        """Print error message."""
        if tracker:
            self._print_fn(f"  ✗ {tracker.model}: {error}")
        else:
            self._print_fn(f"  ✗ API call failed: {error}")

    def _clear_and_print(self, line: str, tracker_id: str) -> None:
        """Clear previous line and print new progress."""
        with self._lock:
            last = self._last_lines.get(tracker_id, "")
            if len(last) > len(line):
                line = line + " " * (len(last) - len(line))
            self._last_lines[tracker_id] = line
        self._print_fn(f"\r{line}")


class StreamingProgressAdapter:
    """Adapter that wraps a streaming response and tracks progress.
    
    Usage:
        adapter = StreamingProgressAdapter(callback, call_id, model)
        for chunk in adapter.wrap(streaming_response):
            yield chunk
    """

    def __init__(
        self,
        callback: Optional[APICallProgressCallback],
        call_id: str,
        model: str,
    ):
        self.callback = callback
        self.call_id = call_id
        self.model = model
        self._tracker: Optional[APIProgressTracker] = None

    def __enter__(self) -> "StreamingProgressAdapter":
        if self.callback:
            self._tracker = self.callback.start_tracking(self.call_id, self.model)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            if self.callback:
                self.callback.on_error(self.call_id, str(exc_val))
        return False

    def wrap(self, streaming_response):
        """Wrap a streaming response to track progress."""
        if self.callback:
            self.callback.on_stream_start(self.call_id)

        try:
            for chunk in streaming_response:
                if self.callback:
                    self.callback.on_token(self.call_id, 1)
                yield chunk
            if self.callback:
                self.callback.on_complete(self.call_id)
        except Exception as e:
            if self.callback:
                self.callback.on_error(self.call_id, str(e))
            raise
