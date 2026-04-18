"""Diagnostic Collector for Hermes Agent.

Collects and analyzes runtime diagnostics for debugging and troubleshooting.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DiagnosticLevel(Enum):
    """Verbosity level for diagnostics."""
    BASIC = "basic"       # System info only
    NORMAL = "normal"     # +运行时 metrics
    VERBOSE = "verbose"   # +详细 trace


class DiagnosticCategory(Enum):
    """Categories of diagnostic data."""
    SYSTEM = "system"
    RUNTIME = "runtime"
    TOOLS = "tools"
    API = "api"
    MEMORY = "memory"
    ERRORS = "errors"


@dataclass
class DiagnosticEntry:
    """A single diagnostic entry."""
    timestamp: float
    category: DiagnosticCategory
    level: DiagnosticLevel
    name: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "category": self.category.value,
            "level": self.level.value,
            "name": self.name,
            "value": self._serialize_value(self.value),
            "metadata": self.metadata,
        }

    def _serialize_value(self, value: Any) -> Any:
        """Serialize value to JSON-compatible format."""
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return len(value)
        if hasattr(value, "__dict__"):
            return str(value)
        return str(value)


@dataclass
class SystemInfo:
    """System information snapshot."""
    python_version: str = ""
    platform_system: str = ""
    platform_release: str = ""
    platform_version: str = ""
    processor: str = ""
    cpu_count: int = 0
    memory_total: int = 0
    memory_available: int = 0
    disk_total: int = 0
    disk_free: int = 0
    hermes_version: str = "unknown"
    hermes_home: str = ""
    environment: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def collect(cls) -> "SystemInfo":
        """Collect current system information."""
        import shutil

        info = cls()
        info.python_version = sys.version.split()[0]
        info.platform_system = platform.system()
        info.platform_release = platform.release()
        info.platform_version = platform.version()
        info.processor = platform.processor()
        info.cpu_count = os.cpu_count() or 1

        try:
            mem = os.popen("free -b 2>/dev/null").read() if platform.system() == "Linux" else ""
            if mem:
                lines = mem.split("\n")
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 2:
                        info.memory_total = int(parts[1])
                        info.memory_available = int(parts[6])
        except Exception:
            pass

        try:
            disk = shutil.disk_usage("/")
            info.disk_total = disk.total
            info.disk_free = disk.free
        except Exception:
            pass

        info.hermes_home = os.environ.get("HERMES_HOME", "~/.hermes")

        # Collect relevant env vars (no secrets)
        safe_vars = [
            "HERMES_HOME", "HERMES_PROFILE", "HERMES_TUI",
            "PATH", "PYTHONPATH", "LANG", "TZ",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",  # Just checking existence
        ]
        for var in safe_vars:
            value = os.environ.get(var, "")
            if var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
                info.environment[var] = "***" if value else "(not set)"
            else:
                info.environment[var] = value

        return info

    def to_dict(self) -> Dict[str, Any]:
        return {
            "python_version": self.python_version,
            "platform": f"{self.platform_system} {self.platform_release}",
            "cpu_count": self.cpu_count,
            "memory_total_gb": round(self.memory_total / (1024**3), 2),
            "memory_available_gb": round(self.memory_available / (1024**3), 2),
            "disk_free_gb": round(self.disk_free / (1024**3), 2),
            "hermes_home": self.hermes_home,
            "environment": self.environment,
        }


class DiagnosticCollector:
    """Collects diagnostic data during agent runtime.
    
    Usage:
        collector = DiagnosticCollector()
        collector.start()
        
        # Collect diagnostics
        collector.collect("tools", "tool_used", "read_file", metadata={"duration": 0.5})
        
        # Get snapshot
        snapshot = collector.get_snapshot()
        
        # Generate report
        report = collector.generate_report()
    """

    def __init__(self, level: DiagnosticLevel = DiagnosticLevel.NORMAL):
        self._level = level
        self._entries: List[DiagnosticEntry] = []
        self._lock = threading.RLock()
        self._start_time = time.time()
        self._system_info: Optional[SystemInfo] = None
        self._callbacks: List[Callable[[DiagnosticEntry], None]] = []

    def start(self) -> None:
        """Start collecting diagnostics."""
        self._start_time = time.time()
        self._system_info = SystemInfo.collect()

    def collect(
        self,
        category: DiagnosticCategory,
        name: str,
        value: Any,
        level: Optional[DiagnosticLevel] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Collect a diagnostic entry."""
        if (level or DiagnosticLevel.NORMAL).value > self._level.value:
            return

        entry = DiagnosticEntry(
            timestamp=time.time(),
            category=category,
            level=level or DiagnosticLevel.NORMAL,
            name=name,
            value=value,
            metadata=metadata or {},
        )

        with self._lock:
            self._entries.append(entry)

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(entry)
            except Exception as e:
                logger.debug(f"Diagnostic callback error: {e}")

    def add_callback(self, callback: Callable[[DiagnosticEntry], None]) -> None:
        """Add a callback for new entries."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[DiagnosticEntry], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_entries(
        self,
        category: Optional[DiagnosticCategory] = None,
        since: Optional[float] = None,
    ) -> List[DiagnosticEntry]:
        """Get diagnostic entries, optionally filtered."""
        with self._lock:
            entries = list(self._entries)

        if category:
            entries = [e for e in entries if e.category == category]
        if since:
            entries = [e for e in entries if e.timestamp >= since]

        return entries

    def get_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of current diagnostics."""
        with self._lock:
            entries = list(self._entries)

        # Group by category
        by_category: Dict[str, List[Dict]] = {}
        for entry in entries:
            cat = entry.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(entry.to_dict())

        return {
            "system": self._system_info.to_dict() if self._system_info else {},
            "runtime": {
                "uptime_seconds": round(time.time() - self._start_time, 2),
                "total_entries": len(entries),
            },
            "entries_by_category": {k: len(v) for k, v in by_category.items()},
        }

    def get_errors(self) -> List[DiagnosticEntry]:
        """Get all error entries."""
        return self.get_entries(DiagnosticCategory.ERRORS)

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._entries.clear()

    def generate_report(self) -> str:
        """Generate a human-readable diagnostic report."""
        snapshot = self.get_snapshot()
        entries = self.get_entries()

        lines = [
            "=" * 60,
            "HERMES AGENT DIAGNOSTIC REPORT",
            "=" * 60,
            "",
            "## System Information",
            f"  Python: {snapshot['system'].get('python_version', 'unknown')}",
            f"  Platform: {snapshot['system'].get('platform', 'unknown')}",
            f"  CPUs: {snapshot['system'].get('cpu_count', 'unknown')}",
            f"  Memory: {snapshot['system'].get('memory_available_gb', 'unknown')}GB available",
            f"  Disk: {snapshot['system'].get('disk_free_gb', 'unknown')}GB free",
            f"  Hermes Home: {snapshot['system'].get('hermes_home', 'unknown')}",
            "",
            "## Runtime Statistics",
            f"  Uptime: {snapshot['runtime']['uptime_seconds']}s",
            f"  Total Entries: {snapshot['runtime']['total_entries']}",
            "",
            "## Entries by Category",
        ]

        for cat, count in snapshot["entries_by_category"].items():
            lines.append(f"  {cat}: {count}")

        # Show recent errors
        errors = self.get_errors()
        if errors:
            lines.extend(["", "## Recent Errors"])
            for err in errors[-5:]:
                lines.append(f"  [{err.timestamp}] {err.name}: {err.value}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def export_json(self) -> str:
        """Export diagnostics as JSON."""
        snapshot = self.get_snapshot()
        entries = self.get_entries()
        return json.dumps({
            "snapshot": snapshot,
            "entries": [e.to_dict() for e in entries],
        }, indent=2)


# Global singleton

_diagnostic_collector: Optional[DiagnosticCollector] = None

def get_diagnostic_collector(level: DiagnosticLevel = DiagnosticLevel.NORMAL) -> DiagnosticCollector:
    """Get the global diagnostic collector."""
    global _diagnostic_collector
    if _diagnostic_collector is None:
        _diagnostic_collector = DiagnosticCollector(level)
    return _diagnostic_collector
