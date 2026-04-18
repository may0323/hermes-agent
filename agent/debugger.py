"""Agent Debugger for Hermes Agent.

Provides debugging tools for diagnosing agent behavior and issues.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DebugCommand(Enum):
    """Available debug commands."""
    TRACE = "trace"
    INSPECT = "inspect"
    PROFILE = "profile"
    EXPLAIN = "explain"
    BREAK = "break"


@dataclass
class DebugContext:
    """Context for a debug session."""
    session_id: str
    agent_id: str = ""
    started_at: float = 0
    last_activity: float = 0
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class AgentDebugger:
    """Debugging tools for Hermes Agent.
    
    Usage:
        debugger = AgentDebugger()
        
        # Add a checkpoint
        debugger.checkpoint("before_tool_call", {"tool": "read_file", "args": ...})
        
        # Inspect state
        state = debugger.inspect()
        
        # Get trace
        trace = debugger.get_trace()
        
        # Explain error
        explanation = debugger.explain_error(error)
    """

    def __init__(self, session_id: str = "default"):
        self._session_id = session_id
        self._context = DebugContext(
            session_id=session_id,
            started_at=datetime.now().timestamp(),
            last_activity=datetime.now().timestamp(),
        )
        self._trace: List[Dict[str, Any]] = []
        self._breakpoints: Dict[str, bool] = {}
        self._enabled = os.environ.get("HERMES_DEBUG", "0") == "1"
        self._lock = threading.RLock()

    @property
    def enabled(self) -> bool:
        """Check if debugging is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable debugging."""
        self._enabled = True
        self._context.started_at = datetime.now().timestamp()

    def disable(self) -> None:
        """Disable debugging."""
        self._enabled = False

    def checkpoint(
        self,
        name: str,
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Add a debug checkpoint.
        
        Returns checkpoint ID.
        """
        import uuid
        checkpoint_id = str(uuid.uuid4())[:8]

        checkpoint = {
            "id": checkpoint_id,
            "name": name,
            "timestamp": datetime.now().timestamp(),
            "data": data or {},
            "tags": tags or [],
        }

        with self._lock:
            self._context.checkpoints.append(checkpoint)
            self._context.last_activity = datetime.now().timestamp()
            self._trace.append({
                "type": "checkpoint",
                "checkpoint": checkpoint,
            })

        logger.debug(f"Debug checkpoint: {name} ({checkpoint_id})")
        return checkpoint_id

    def inspect(self) -> Dict[str, Any]:
        """Get current debug state."""
        with self._lock:
            return {
                "session_id": self._session_id,
                "enabled": self._enabled,
                "uptime": datetime.now().timestamp() - self._context.started_at,
                "checkpoints": len(self._context.checkpoints),
                "trace_entries": len(self._trace),
                "breakpoints": list(self._breakpoints.keys()),
            }

    def get_trace(
        self,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get execution trace."""
        with self._lock:
            trace = list(self._trace)

        if since:
            trace = [t for t in trace if t.get("timestamp", 0) >= since]

        return trace[-limit:]

    def add_note(self, note: str) -> None:
        """Add a debug note."""
        with self._lock:
            self._context.notes.append(f"[{datetime.now().isoformat()}] {note}")

    def log(
        self,
        level: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a debug message."""
        entry = {
            "type": "log",
            "level": level,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().timestamp(),
        }

        with self._lock:
            self._trace.append(entry)
            self._context.last_activity = datetime.now().timestamp()

        log_fn = {
            "debug": logger.debug,
            "info": logger.info,
            "warning": logger.warning,
            "error": logger.error,
        }.get(level, logger.debug)

        log_fn(f"[DEBUG] {message}")

    def set_breakpoint(self, name: str, enabled: bool = True) -> None:
        """Set a breakpoint."""
        with self._lock:
            self._breakpoints[name] = enabled

    def check_breakpoint(self, name: str) -> bool:
        """Check if a breakpoint is triggered."""
        with self._lock:
            return self._breakpoints.get(name, False)

    def capture_exception(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Capture an exception with full context."""
        tb = traceback.extract_tb(exc.__traceback__)

        exception_info = {
            "type": "exception",
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exception(type(exc), exc, exc.__traceback__),
            "stack": [
                {
                    "file": frame.filename,
                    "line": frame.lineno,
                    "function": frame.name,
                    "code": frame.line,
                }
                for frame in tb
            ],
            "context": context or {},
            "timestamp": datetime.now().timestamp(),
        }

        with self._lock:
            self._trace.append(exception_info)

        return exception_info

    def explain_error(self, error_data: Dict[str, Any]) -> str:
        """Generate explanation for an error.
        
        Returns a human-readable explanation with suggestions.
        """
        error_type = error_data.get("type", "unknown")
        error_msg = error_data.get("message", error_data.get("error", ""))
        status_code = error_data.get("status_code")

        lines = [
            f"Error Analysis: {error_type}",
            "-" * 40,
            f"Message: {error_msg}",
        ]

        if status_code:
            lines.append(f"Status Code: {status_code}")
            lines.append("")
            lines.append(self._explain_status_code(status_code))

        # Add specific advice based on error type
        if "timeout" in error_msg.lower():
            lines.extend([
                "",
                "Suggestions:",
                "  1. Check network connectivity",
                "  2. Increase timeout settings",
                "  3. Try again with smaller payload",
            ])
        elif "auth" in error_type.lower() or "401" in str(status_code):
            lines.extend([
                "",
                "Suggestions:",
                "  1. Verify API key is correct",
                "  2. Check if key has required permissions",
                "  3. Ensure key hasn't expired",
            ])
        elif "rate_limit" in error_type.lower() or "429" in str(status_code):
            lines.extend([
                "",
                "Suggestions:",
                "  1. Wait before retrying",
                "  2. Implement exponential backoff",
                "  3. Consider upgrading API plan",
            ])

        return "\n".join(lines)

    def _explain_status_code(self, code: int) -> str:
        """Explain HTTP status code."""
        explanations = {
            400: "Bad Request - The request was invalid or cannot be served.",
            401: "Unauthorized - Authentication is required or has failed.",
            403: "Forbidden - You don't have permission to access this resource.",
            404: "Not Found - The requested resource could not be found.",
            429: "Too Many Requests - Rate limit exceeded. Please wait.",
            500: "Internal Server Error - Something went wrong on the server.",
            502: "Bad Gateway - Server received an invalid response.",
            503: "Service Unavailable - Server is temporarily unavailable.",
            504: "Gateway Timeout - Server took too long to respond.",
        }
        return explanations.get(code, f"Unknown status code: {code}")

    def get_summary(self) -> str:
        """Get a summary of the debug session."""
        with self._lock:
            checkpoint_count = len(self._context.checkpoints)
            trace_count = len(self._trace)
            note_count = len(self._context.notes)

        lines = [
            "=" * 40,
            "DEBUG SESSION SUMMARY",
            "=" * 40,
            f"Session ID: {self._session_id}",
            f"Enabled: {self._enabled}",
            f"Uptime: {datetime.now().timestamp() - self._context.started_at:.1f}s",
            f"Checkpoints: {checkpoint_count}",
            f"Trace Entries: {trace_count}",
            f"Notes: {note_count}",
        ]

        if self._context.notes:
            lines.append("")
            lines.append("Recent Notes:")
            for note in self._context.notes[-5:]:
                lines.append(f"  {note}")

        lines.append("=" * 40)
        return "\n".join(lines)

    def export_trace(self, filepath: str) -> bool:
        """Export trace to file."""
        try:
            with open(filepath, "w") as f:
                json.dump({
                    "session_id": self._session_id,
                    "context": {
                        "started_at": self._context.started_at,
                        "last_activity": self._context.last_activity,
                        "checkpoints": self._context.checkpoints,
                        "notes": self._context.notes,
                    },
                    "trace": self._trace,
                }, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export trace: {e}")
            return False


class BreakpointManager:
    """Manages breakpoints for debugging."""

    def __init__(self):
        self._breakpoints: Dict[str, Dict[str, Any]] = {}
        self._enabled = True
        self._lock = threading.Lock()

    def add(
        self,
        name: str,
        condition: Optional[Callable[[], bool]] = None,
        action: Optional[Callable[[], None]] = None,
    ) -> None:
        """Add a breakpoint."""
        with self._lock:
            self._breakpoints[name] = {
                "condition": condition,
                "action": action,
                "hit_count": 0,
            }

    def remove(self, name: str) -> None:
        """Remove a breakpoint."""
        with self._lock:
            if name in self._breakpoints:
                del self._breakpoints[name]

    def check(self, name: str) -> bool:
        """Check if breakpoint should trigger."""
        if not self._enabled:
            return False

        with self._lock:
            bp = self._breakpoints.get(name)
            if not bp:
                return False

        # Check condition
        if bp["condition"] and not bp["condition"]():
            return False

        # Update hit count
        with self._lock:
            bp["hit_count"] += 1

        # Execute action
        if bp["action"]:
            try:
                bp["action"]()
            except Exception as e:
                logger.error(f"Breakpoint action error: {e}")

        return True

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def get_stats(self) -> Dict[str, Any]:
        """Get breakpoint statistics."""
        with self._lock:
            return {
                name: {"hit_count": bp["hit_count"]}
                for name, bp in self._breakpoints.items()
            }


# Global debugger instance

_debugger: Optional[AgentDebugger] = None

def get_debugger(session_id: str = "default") -> AgentDebugger:
    """Get the global debugger instance."""
    global _debugger
    if _debugger is None:
        _debugger = AgentDebugger(session_id)
    return _debugger
