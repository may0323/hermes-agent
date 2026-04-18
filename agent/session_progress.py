"""Session Management Progress Tracker for Hermes Agent.

Tracks session lifecycle progress: initialization, memory loading, context compression, etc.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionPhase(Enum):
    """Phases of session lifecycle."""
    INITIALIZING = "initializing"
    LOADING_MEMORY = "loading_memory"
    BUILDING_CONTEXT = "building_context"
    READY = "ready"
    COMPRESSING = "compressing"
    ENDING = "ending"


@dataclass
class SessionProgressStep:
    """A step in session progress."""
    phase: SessionPhase
    description: str
    duration: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionProgress:
    """Tracks session lifecycle progress."""
    session_id: str
    start_time: float = field(default_factory=time.time)
    current_phase: SessionPhase = SessionPhase.INITIALIZING
    phase_history: List[SessionProgressStep] = field(default_factory=list)
    memory_entries_loaded: int = 0
    context_size: int = 0  # tokens
    compression_count: int = 0
    last_activity: float = field(default_factory=time.time)

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    @property
    def is_active(self) -> bool:
        return self.current_phase not in (SessionPhase.ENDING,)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id[:8] + "...",
            "phase": self.current_phase.value,
            "elapsed": round(self.elapsed_time, 1),
            "memory_entries": self.memory_entries_loaded,
            "context_tokens": self.context_size,
            "compressions": self.compression_count,
        }


class SessionProgressCallback:
    """Callback for session progress updates.
    
    Shows quiet, elegant session status.
    """

    SESSION_PHASE_DESCRIPTIONS = {
        SessionPhase.INITIALIZING: "Starting session",
        SessionPhase.LOADING_MEMORY: "Loading memory",
        SessionPhase.BUILDING_CONTEXT: "Building context",
        SessionPhase.READY: "Ready",
        SessionPhase.COMPRESSING: "Compressing context",
        SessionPhase.ENDING: "Ending session",
    }

    def __init__(
        self,
        print_fn: Optional[Callable[[str], None]] = None,
        verbose: bool = False,
    ):
        self._print_fn = print_fn or print
        self._verbose = verbose
        self._last_message: str = ""

    def on_phase_change(self, progress: SessionProgress, previous_phase: SessionPhase) -> None:
        """Called when session phase changes."""
        desc = self.SESSION_PHASE_DESCRIPTIONS.get(progress.current_phase, progress.current_phase.value)
        
        if progress.current_phase == SessionPhase.READY:
            self._print_fn(f"  ✓ Session ready (loaded {progress.memory_entries_loaded} memories, {progress.context_size} tokens)")
        elif progress.current_phase == SessionPhase.COMPRESSING:
            if self._verbose:
                self._print_fn(f"  → Context compression ({progress.compression_count})...")
        elif self._verbose or progress.current_phase == SessionPhase.INITIALIZING:
            if previous_phase != progress.current_phase:
                self._print_fn(f"  → {desc}")

    def on_activity(self, progress: SessionProgress, activity: str) -> None:
        """Called on significant activity."""
        if self._verbose:
            self._print_fn(f"  → {activity}")


class SessionProgressTracker:
    """Tracks session lifecycle progress.
    
    Usage:
        tracker = SessionProgressTracker(callback)
        
        # Track session start
        progress = tracker.start_session("sess_123")
        
        # Track phases
        tracker.set_phase("sess_123", SessionPhase.LOADING_MEMORY)
        tracker.update_metadata("sess_123", memory_entries=5)
        
        tracker.set_phase("sess_123", SessionPhase.READY)
        
        # Track compression
        tracker.set_phase("sess_123", SessionPhase.COMPRESSING)
        tracker.set_phase("sess_123", SessionPhase.READY)
        
        # End session
        tracker.end_session("sess_123")
    """

    def __init__(self, callback: Optional[SessionProgressCallback] = None):
        self._callback = callback or SessionProgressCallback()
        self._sessions: Dict[str, SessionProgress] = {}
        self._lock = threading.Lock()

    def start_session(self, session_id: str) -> SessionProgress:
        """Start tracking a new session."""
        with self._lock:
            progress = SessionProgress(session_id=session_id)
            self._sessions[session_id] = progress
        return progress

    def set_phase(self, session_id: str, phase: SessionPhase) -> Optional[SessionProgress]:
        """Set the current phase of a session."""
        with self._lock:
            progress = self._sessions.get(session_id)
            if not progress:
                return None
            
            previous = progress.current_phase
            if previous != phase:
                # Record previous phase duration
                if progress.phase_history:
                    last = progress.phase_history[-1]
                    last.duration = time.time() - progress.start_time
                
                progress.current_phase = phase
                progress.last_activity = time.time()
                
                # Add to history
                progress.phase_history.append(
                    SessionProgressStep(
                        phase=phase,
                        description=self._callback.SESSION_PHASE_DESCRIPTIONS.get(phase, phase.value),
                    )
                )
                
                # Notify callback
                self._callback.on_phase_change(progress, previous)
            
            return progress

    def update_metadata(
        self,
        session_id: str,
        memory_entries: Optional[int] = None,
        context_size: Optional[int] = None,
        **kwargs,
    ) -> Optional[SessionProgress]:
        """Update session metadata."""
        with self._lock:
            progress = self._sessions.get(session_id)
            if not progress:
                return None
            
            if memory_entries is not None:
                progress.memory_entries_loaded = memory_entries
            if context_size is not None:
                progress.context_size = context_size
            
            progress.last_activity = time.time()
            
            for key, value in kwargs.items():
                progress.phase_history[-1].metadata[key] = value if progress.phase_history else {}
            
            return progress

    def increment_compression(self, session_id: str) -> Optional[SessionProgress]:
        """Increment compression count."""
        with self._lock:
            progress = self._sessions.get(session_id)
            if not progress:
                return None
            progress.compression_count += 1
            progress.last_activity = time.time()
            return progress

    def end_session(self, session_id: str) -> Optional[SessionProgress]:
        """End session tracking."""
        with self._lock:
            progress = self._sessions.get(session_id)
            if not progress:
                return None
            
            progress.current_phase = SessionPhase.ENDING
            self._callback.on_phase_change(progress, SessionPhase.ENDING)
            
            # Clean up old sessions
            self._cleanup_sessions()
            
            return progress

    def get_progress(self, session_id: str) -> Optional[SessionProgress]:
        """Get session progress."""
        return self._sessions.get(session_id)

    def get_active_session(self) -> Optional[SessionProgress]:
        """Get the most recently active session."""
        with self._lock:
            active = [s for s in self._sessions.values() if s.is_active]
            if not active:
                return None
            return max(active, key=lambda s: s.last_activity)

    def get_all_active(self) -> List[SessionProgress]:
        """Get all active sessions."""
        with self._lock:
            return [s for s in self._sessions.values() if s.is_active]

    def _cleanup_sessions(self) -> None:
        """Remove ended sessions older than 5 minutes."""
        current_time = time.time()
        max_age = 300
        to_remove = []
        
        for session_id, progress in self._sessions.items():
            if not progress.is_active:
                age = current_time - progress.last_activity
                if age > max_age:
                    to_remove.append(session_id)
        
        for session_id in to_remove:
            del self._sessions[session_id]


# Convenience functions

_session_tracker: Optional[SessionProgressTracker] = None

def get_session_tracker() -> SessionProgressTracker:
    """Get the global session tracker."""
    global _session_tracker
    if _session_tracker is None:
        _session_tracker = SessionProgressTracker()
    return _session_tracker
