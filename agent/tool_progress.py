"""Tool Execution Progress Tracker for Hermes Agent.

Provides structured progress tracking for multi-tool execution workflows.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolState(Enum):
    """State of a tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolExecutionStep:
    """Represents a single tool execution step."""
    name: str
    tool_name: str
    args_preview: str = ""
    state: ToolState = ToolState.PENDING
    start_time: float = 0
    end_time: float = 0
    result_preview: str = ""
    error: str = ""

    @property
    def duration(self) -> float:
        if self.start_time == 0:
            return 0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tool": self.tool_name,
            "state": self.state.value,
            "duration": round(self.duration, 2),
            "result_preview": self.result_preview,
        }


@dataclass
class ToolExecutionProgress:
    """Tracks progress of multi-tool execution."""
    id: str
    description: str
    steps: List[ToolExecutionStep] = field(default_factory=list)
    current_step_idx: int = 0
    start_time: float = field(default_factory=time.time)
    is_parallel: bool = False
    completed_count: int = 0
    failed_count: int = 0

    @property
    def total_count(self) -> int:
        return len(self.steps)

    @property
    def percent_complete(self) -> float:
        if not self.steps:
            return 0
        total = len(self.steps)
        completed = self.completed_count + self.failed_count
        if completed >= total:
            return 100
        return (completed / total) * 100

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    @property
    def is_active(self) -> bool:
        return self.completed_count + self.failed_count < len(self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "percent": round(self.percent_complete, 1),
            "completed": self.completed_count,
            "failed": self.failed_count,
            "total": self.total_count,
            "elapsed": round(self.elapsed_time, 1),
            "steps": [s.to_dict() for s in self.steps],
        }


class ToolProgressCallback:
    """Callback for tool execution progress updates.
    
    Codex-inspired: quiet, minimal, shows only key information.
    """

    def __init__(
        self,
        print_fn: Optional[Callable[[str], None]] = None,
        verbose: bool = False,
    ):
        self._print_fn = print_fn or print
        self._verbose = verbose
        self._last_message: str = ""

    def on_tool_start(self, step: ToolExecutionStep) -> None:
        """Called when a tool starts executing."""
        if self._verbose:
            self._print(f"  → {step.tool_name}: {step.args_preview[:50]}...")

    def on_tool_complete(self, step: ToolExecutionStep) -> None:
        """Called when a tool completes."""
        duration = step.duration
        if step.result_preview:
            preview = step.result_preview[:40] if len(step.result_preview) > 40 else step.result_preview
            self._print(f"  ✓ {step.tool_name}: {preview} ({duration:.1f}s)")
        else:
            self._print(f"  ✓ {step.tool_name} ({duration:.1f}s)")

    def on_tool_error(self, step: ToolExecutionStep) -> None:
        """Called when a tool fails."""
        error_msg = step.error[:60] if step.error else "unknown error"
        self._print(f"  ✗ {step.tool_name}: {error_msg}")

    def on_batch_start(self, progress: ToolExecutionProgress) -> None:
        """Called when a batch of tools starts."""
        if progress.is_parallel:
            self._print(f"  → Running {len(progress.steps)} tools in parallel...")

    def on_batch_progress(self, progress: ToolExecutionProgress) -> None:
        """Called on batch progress update."""
        if self._verbose:
            msg = f"  → Progress: {progress.completed_count}/{progress.total_count}"
            if progress.failed_count > 0:
                msg += f" (failed: {progress.failed_count})"
            self._clear_and_print(msg)

    def on_batch_complete(self, progress: ToolExecutionProgress) -> None:
        """Called when batch completes."""
        elapsed = progress.elapsed_time
        if progress.failed_count > 0:
            self._print(f"  ✗ Completed {progress.completed_count}/{progress.total_count} tools ({progress.failed_count} failed) in {elapsed:.1f}s")
        else:
            self._print(f"  ✓ All {progress.total_count} tools completed in {elapsed:.1f}s")

    def _print(self, msg: str) -> None:
        self._last_message = msg
        self._print_fn(msg)

    def _clear_and_print(self, msg: str) -> None:
        """Print with line clearing."""
        if len(self._last_message) > len(msg):
            msg = msg + " " * (len(self._last_message) - len(msg))
        self._print_fn(f"\r{msg}")


class ToolProgressTracker:
    """Manages tool execution progress tracking.
    
    Usage:
        tracker = ToolProgressTracker(callback=callback)
        
        # Start batch
        progress = tracker.start_batch("task_1", "Processing files", is_parallel=True)
        
        # Add tools
        tracker.add_tool("task_1", "read_file", "Reading config.py")
        tracker.add_tool("task_1", "search", "Searching...")
        
        # Start tool
        tracker.start_tool("task_1", "read_file")
        # ... do work ...
        tracker.complete_tool("task_1", "read_file", result_preview="OK")
        
        # Complete batch
        tracker.complete_batch("task_1")
    """

    def __init__(self, callback: Optional[ToolProgressCallback] = None):
        self._callback = callback or ToolProgressCallback()
        self._progress: Dict[str, ToolExecutionProgress] = {}
        self._current_tool: Dict[str, str] = {}  # progress_id -> tool_name
        self._lock = threading.Lock()

    def start_batch(
        self,
        batch_id: str,
        description: str,
        is_parallel: bool = False,
    ) -> ToolExecutionProgress:
        """Start a new batch execution."""
        with self._lock:
            progress = ToolExecutionProgress(
                id=batch_id,
                description=description,
                is_parallel=is_parallel,
            )
            self._progress[batch_id] = progress
        self._callback.on_batch_start(progress)
        return progress

    def add_tool(
        self,
        batch_id: str,
        tool_name: str,
        name: str = "",
        args_preview: str = "",
    ) -> Optional[ToolExecutionStep]:
        """Add a tool to a batch."""
        with self._lock:
            progress = self._progress.get(batch_id)
            if not progress:
                return None
            step = ToolExecutionStep(
                name=name or tool_name,
                tool_name=tool_name,
                args_preview=args_preview,
            )
            progress.steps.append(step)
            return step

    def start_tool(self, batch_id: str, tool_name: str) -> Optional[ToolExecutionStep]:
        """Mark a tool as started."""
        with self._lock:
            progress = self._progress.get(batch_id)
            if not progress:
                return None
            
            step = self._find_step(progress, tool_name)
            if step:
                step.state = ToolState.RUNNING
                step.start_time = time.time()
                self._current_tool[batch_id] = tool_name
                self._callback.on_tool_start(step)
            return step

    def complete_tool(
        self,
        batch_id: str,
        tool_name: str,
        result_preview: str = "",
    ) -> Optional[ToolExecutionStep]:
        """Mark a tool as completed."""
        with self._lock:
            progress = self._progress.get(batch_id)
            if not progress:
                return None
            
            step = self._find_step(progress, tool_name)
            if step:
                step.state = ToolState.COMPLETED
                step.end_time = time.time()
                step.result_preview = result_preview
                progress.completed_count += 1
                self._callback.on_tool_complete(step)
                
                if progress.id in self._current_tool:
                    del self._current_tool[progress.id]
            return step

    def fail_tool(
        self,
        batch_id: str,
        tool_name: str,
        error: str = "",
    ) -> Optional[ToolExecutionStep]:
        """Mark a tool as failed."""
        with self._lock:
            progress = self._progress.get(batch_id)
            if not progress:
                return None
            
            step = self._find_step(progress, tool_name)
            if step:
                step.state = ToolState.FAILED
                step.end_time = time.time()
                step.error = error
                progress.failed_count += 1
                self._callback.on_tool_error(step)
                
                if progress.id in self._current_tool:
                    del self._current_tool[progress.id]
            return step

    def complete_batch(self, batch_id: str) -> Optional[ToolExecutionProgress]:
        """Mark a batch as complete."""
        with self._lock:
            progress = self._progress.get(batch_id)
            if not progress:
                return None
            self._callback.on_batch_complete(progress)
            return progress

    def get_progress(self, batch_id: str) -> Optional[ToolExecutionProgress]:
        """Get progress for a batch."""
        return self._progress.get(batch_id)

    def get_all_active(self) -> List[ToolExecutionProgress]:
        """Get all active batches."""
        with self._lock:
            return [p for p in self._progress.values() if p.is_active]

    def _find_step(self, progress: ToolExecutionProgress, tool_name: str) -> Optional[ToolExecutionStep]:
        """Find a step by tool name."""
        for step in progress.steps:
            if step.tool_name == tool_name:
                return step
        return None


# Convenience functions

_tool_tracker: Optional[ToolProgressTracker] = None

def get_tool_tracker() -> ToolProgressTracker:
    """Get the global tool progress tracker."""
    global _tool_tracker
    if _tool_tracker is None:
        _tool_tracker = ToolProgressTracker()
    return _tool_tracker


def start_tool_batch(
    batch_id: str,
    description: str,
    tools: List[Dict[str, str]],
    is_parallel: bool = False,
    callback: Optional[ToolProgressCallback] = None,
) -> ToolExecutionProgress:
    """Convenience to start a batch with tools.
    
    Args:
        batch_id: Unique batch identifier
        description: Human-readable description
        tools: List of {"name": str, "tool": str, "args_preview": str}
        is_parallel: Whether tools run in parallel
        callback: Optional callback
        
    Returns:
        ToolExecutionProgress
    """
    tracker = get_tool_tracker()
    if callback:
        tracker._callback = callback
    
    progress = tracker.start_batch(batch_id, description, is_parallel)
    for t in tools:
        tracker.add_tool(
            batch_id,
            t.get("tool", ""),
            t.get("name", ""),
            t.get("args_preview", ""),
        )
    return progress
