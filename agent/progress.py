"""Progress Feedback System for Hermes Agent.

Provides unified, elegant progress tracking across all scenarios:
- Tool execution progress
- API call progress (streaming, token usage)
- Session management progress (memory loading, context compression)

Codex-inspired: quiet, elegant, non-intrusive.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProgressLevel(Enum):
    """Verbosity levels for progress feedback."""
    SILENT = 0    # No output
    MINIMAL = 1   # Only final result
    NORMAL = 2   # Key milestones
    VERBOSE = 3  # Detailed progress


class ProgressState(Enum):
    """State of a progress operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressStep:
    """A single step in a progress operation."""
    name: str
    description: str = ""
    weight: float = 1.0  # Relative weight for percentage calculation
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressTracker:
    """Tracks progress of a multi-step operation."""
    id: str
    operation: str
    steps: List[ProgressStep] = field(default_factory=list)
    current_step_idx: int = 0
    state: ProgressState = ProgressState.PENDING
    start_time: float = 0
    end_time: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time == 0:
            return 0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def percent_complete(self) -> float:
        """Calculate percentage based on step weights."""
        if not self.steps:
            return 0
        completed_weight = sum(
            step.weight for i, step in enumerate(self.steps)
            if i < self.current_step_idx
        )
        current_step = self.steps[self.current_step_idx] if self.current_step_idx < len(self.steps) else None
        if current_step:
            completed_weight += current_step.weight * 0.5  # Assume 50% for current
        total_weight = sum(step.weight for step in self.steps)
        return min(100, (completed_weight / total_weight * 100) if total_weight > 0 else 0)

    @property
    def is_active(self) -> bool:
        return self.state == ProgressState.RUNNING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "operation": self.operation,
            "state": self.state.value,
            "percent": round(self.percent_complete, 1),
            "current_step": self.steps[self.current_step_idx].name if self.current_step_idx < len(self.steps) else "",
            "elapsed": round(self.elapsed_time, 1),
            "metadata": self.metadata,
        }


class ProgressCallback:
    """Callback interface for progress updates."""
    
    def on_progress_start(self, tracker: ProgressTracker) -> None:
        """Called when progress starts."""
        pass
    
    def on_progress_update(self, tracker: ProgressTracker) -> None:
        """Called on each progress update."""
        pass
    
    def on_progress_complete(self, tracker: ProgressTracker) -> None:
        """Called when progress completes."""
        pass
    
    def on_progress_error(self, tracker: ProgressTracker, error: str) -> None:
        """Called when progress fails."""
        pass


class ProgressManager:
    """Unified progress management for Hermes.
    
    Usage:
        manager = ProgressManager()
        
        # Start tracking an operation
        tracker = manager.start("task_1", "Processing files", [
            ProgressStep("scan", "Scanning files", weight=1),
            ProgressStep("process", "Processing", weight=3),
            ProgressStep("save", "Saving results", weight=1),
        ])
        
        # Update progress
        manager.update("task_1", step_idx=1)
        
        # Complete
        manager.complete("task_1")
    """
    
    _instance: Optional["ProgressManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ProgressManager":
        """Singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._trackers: Dict[str, ProgressTracker] = {}
        self._callbacks: List[ProgressCallback] = []
        self._global_state: Dict[str, Any] = {}
        self._lock_internal = threading.RLock()
        self._max_active = 10  # Max simultaneous trackers
        self._initialized = True

    def reset(self) -> None:
        """Reset the manager (mainly for testing)."""
        with self._lock_internal:
            self._trackers.clear()
            self._global_state.clear()

    def add_callback(self, callback: ProgressCallback) -> None:
        """Add a progress callback."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback) -> None:
        """Remove a progress callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def start(
        self,
        operation_id: str,
        operation_name: str,
        steps: Optional[List[ProgressStep]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProgressTracker:
        """Start tracking an operation.
        
        Args:
            operation_id: Unique identifier for this operation
            operation_name: Human-readable name
            steps: Optional list of steps (creates single-step tracker if None)
            metadata: Optional metadata dict
            
        Returns:
            ProgressTracker instance
        """
        with self._lock_internal:
            # Auto-cleanup old trackers
            self._cleanup_completed()
            
            # Check limit
            if len(self._trackers) >= self._max_active:
                oldest = min(
                    (t for t in self._trackers.values() if t.is_active),
                    key=lambda t: t.start_time,
                    default=None
                )
                if oldest:
                    self._force_complete(oldest.id)
            
            tracker = ProgressTracker(
                id=operation_id,
                operation=operation_name,
                steps=steps or [ProgressStep("main", operation_name)],
                metadata=metadata or {},
                start_time=time.time(),
                state=ProgressState.RUNNING,
            )
            self._trackers[operation_id] = tracker
            
            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb.on_progress_start(tracker)
                except Exception as e:
                    logger.debug(f"Progress callback error: {e}")
            
            return tracker

    def update(
        self,
        operation_id: str,
        step_idx: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ProgressTracker]:
        """Update progress of an operation.
        
        Args:
            operation_id: The operation ID
            step_idx: New step index (optional)
            metadata: Additional metadata to merge
            
        Returns:
            Updated tracker or None if not found
        """
        with self._lock_internal:
            tracker = self._trackers.get(operation_id)
            if not tracker or not tracker.is_active:
                return None
            
            if step_idx is not None and step_idx < len(tracker.steps):
                tracker.current_step_idx = step_idx
            
            if metadata:
                tracker.metadata.update(metadata)
            
            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb.on_progress_update(tracker)
                except Exception as e:
                    logger.debug(f"Progress callback error: {e}")
            
            return tracker

    def complete(self, operation_id: str) -> Optional[ProgressTracker]:
        """Mark an operation as completed.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            Final tracker or None if not found
        """
        with self._lock_internal:
            tracker = self._trackers.get(operation_id)
            if not tracker:
                return None
            
            tracker.state = ProgressState.COMPLETED
            tracker.end_time = time.time()
            
            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb.on_progress_complete(tracker)
                except Exception as e:
                    logger.debug(f"Progress callback error: {e}")
            
            return tracker

    def fail(self, operation_id: str, error: str = "") -> Optional[ProgressTracker]:
        """Mark an operation as failed.
        
        Args:
            operation_id: The operation ID
            error: Optional error message
            
        Returns:
            Final tracker or None if not found
        """
        with self._lock_internal:
            tracker = self._trackers.get(operation_id)
            if not tracker:
                return None
            
            tracker.state = ProgressState.FAILED
            tracker.end_time = time.time()
            if error:
                tracker.metadata["error"] = error
            
            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb.on_progress_error(tracker, error)
                except Exception as e:
                    logger.debug(f"Progress callback error: {e}")
            
            return tracker

    def cancel(self, operation_id: str) -> Optional[ProgressTracker]:
        """Cancel an operation.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            Final tracker or None if not found
        """
        with self._lock_internal:
            tracker = self._trackers.get(operation_id)
            if not tracker:
                return None
            
            tracker.state = ProgressState.CANCELLED
            tracker.end_time = time.time()
            
            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb.on_progress_complete(tracker)  # Reuse complete callback
                except Exception as e:
                    logger.debug(f"Progress callback error: {e}")
            
            return tracker

    def get(self, operation_id: str) -> Optional[ProgressTracker]:
        """Get a tracker by ID."""
        return self._trackers.get(operation_id)

    def get_all_active(self) -> List[ProgressTracker]:
        """Get all active trackers."""
        with self._lock_internal:
            return [t for t in self._trackers.values() if t.is_active]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all progress."""
        with self._lock_internal:
            active = [t for t in self._trackers.values() if t.is_active]
            return {
                "active_count": len(active),
                "trackers": {t.id: t.to_dict() for t in active},
            }

    def _cleanup_completed(self) -> None:
        """Remove old completed trackers."""
        max_age = 300  # 5 minutes
        current_time = time.time()
        to_remove = []
        
        for id, tracker in self._trackers.items():
            if tracker.state != ProgressState.RUNNING:
                age = current_time - tracker.end_time
                if age > max_age:
                    to_remove.append(id)
        
        for id in to_remove:
            del self._trackers[id]

    def _force_complete(self, operation_id: str) -> None:
        """Force complete an operation (internal use)."""
        with self._lock_internal:
            tracker = self._trackers.get(operation_id)
            if tracker and tracker.is_active:
                tracker.state = ProgressState.COMPLETED
                tracker.end_time = time.time()


class SimpleProgressCallback(ProgressCallback):
    """Simple callback that prints progress to console.
    
    Codex-inspired: quiet, minimal output.
    """
    
    def __init__(self, print_fn: Optional[Callable[[str], None]] = None, level: ProgressLevel = ProgressLevel.NORMAL):
        self._print_fn = print_fn or print
        self._level = level
        self._last_line_len = 0
    
    def on_progress_start(self, tracker: ProgressTracker) -> None:
        if self._level.value < ProgressLevel.NORMAL.value:
            return
        
        # Quiet start - just show operation name
        if tracker.steps:
            step_name = tracker.steps[0].name
            self._print(f"  → {tracker.operation}: {step_name}")
    
    def on_progress_update(self, tracker: ProgressTracker) -> None:
        if self._level.value < ProgressLevel.VERBOSE.value:
            return
        
        step = tracker.steps[tracker.current_step_idx] if tracker.current_step_idx < len(tracker.steps) else None
        if step:
            percent = tracker.percent_complete
            self._print(f"  → {tracker.operation}: {step.name} {percent:.0f}%")
    
    def on_progress_complete(self, tracker: ProgressTracker) -> None:
        if self._level.value < ProgressLevel.NORMAL.value:
            return
        
        elapsed = tracker.elapsed_time
        if elapsed < 1:
            self._print(f"  ✓ {tracker.operation} ({elapsed:.1f}s)")
        else:
            self._print(f"  ✓ {tracker.operation} ({elapsed:.1f}s)")
    
    def on_progress_error(self, tracker: ProgressTracker, error: str) -> None:
        if self._level.value < ProgressLevel.MINIMAL.value:
            return
        self._print(f"  ✗ {tracker.operation}: {error}")
    
    def _print(self, msg: str) -> None:
        # Clear previous line if longer
        if self._last_line_len > len(msg):
            msg = msg + " " * (self._last_line_len - len(msg))
        self._last_line_len = len(msg)
        self._print_fn(msg)


# Global convenience functions

_progress_manager: Optional[ProgressManager] = None

def get_progress_manager() -> ProgressManager:
    """Get the global progress manager instance."""
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    return _progress_manager

def start_progress(operation_id: str, operation_name: str, steps: Optional[List[ProgressStep]] = None) -> ProgressTracker:
    """Convenience function to start tracking."""
    return get_progress_manager().start(operation_id, operation_name, steps)

def update_progress(operation_id: str, step_idx: Optional[int] = None) -> Optional[ProgressTracker]:
    """Convenience function to update tracking."""
    return get_progress_manager().update(operation_id, step_idx)

def complete_progress(operation_id: str) -> Optional[ProgressTracker]:
    """Convenience function to complete tracking."""
    return get_progress_manager().complete(operation_id)

def fail_progress(operation_id: str, error: str = "") -> Optional[ProgressTracker]:
    """Convenience function to mark as failed."""
    return get_progress_manager().fail(operation_id, error)
