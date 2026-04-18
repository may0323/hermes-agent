"""Performance Analyzer for Hermes Agent.

Analyzes tool and API call performance metrics.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics."""
    DURATION = "duration"
    COUNT = "count"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


@dataclass
class PerformanceMetric:
    """A single performance metric."""
    name: str
    metric_type: MetricType
    value: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceSummary:
    """Summary of performance metrics."""
    name: str
    total_calls: int = 0
    total_duration: float = 0
    avg_duration: float = 0
    min_duration: float = 0
    max_duration: float = 0
    error_count: int = 0
    error_rate: float = 0
    p50_duration: float = 0
    p95_duration: float = 0
    p99_duration: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_calls": self.total_calls,
            "total_duration": round(self.total_duration, 3),
            "avg_duration": round(self.avg_duration, 3),
            "min_duration": round(self.min_duration, 3),
            "max_duration": round(self.max_duration, 3),
            "error_count": self.error_count,
            "error_rate": round(self.error_rate, 3),
            "p50": round(self.p50_duration, 3),
            "p95": round(self.p95_duration, 3),
            "p99": round(self.p99_duration, 3),
        }


class PerformanceAnalyzer:
    """Analyzes performance of tools and API calls.
    
    Usage:
        analyzer = PerformanceAnalyzer()
        
        # Record a tool call
        with analyzer.track("read_file"):
            # do work
            pass
        
        # Record API call
        analyzer.record_api(
            "claude-3-5-sonnet",
            duration=1.5,
            tokens=500,
            cache_hits=100,
        )
        
        # Get summary
        summary = analyzer.get_summary("read_file")
        
        # Generate report
        report = analyzer.generate_report()
    """

    def __init__(self):
        self._metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self._durations: Dict[str, List[float]] = defaultdict(list)
        self._counts: Dict[str, int] = defaultdict(int)
        self._errors: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self._start_time = time.time()

    def record(
        self,
        name: str,
        duration: float,
        metric_type: MetricType = MetricType.DURATION,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            metric_type=metric_type,
            value=duration,
            timestamp=time.time(),
            metadata=metadata or {},
        )

        with self._lock:
            self._metrics[name].append(metric)

            if metric_type == MetricType.DURATION:
                self._durations[name].append(duration)

    def record_tool(
        self,
        tool_name: str,
        duration: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a tool execution."""
        with self._lock:
            self._counts[tool_name] += 1
            self._durations[tool_name].append(duration)

            if not success:
                self._errors[tool_name] += 1

            self._metrics[tool_name].append(PerformanceMetric(
                name=tool_name,
                metric_type=MetricType.DURATION,
                value=duration,
                timestamp=time.time(),
                metadata={
                    "success": success,
                    **(metadata or {}),
                },
            ))

    def record_api(
        self,
        model: str,
        duration: float,
        tokens: int = 0,
        cache_hits: int = 0,
        error: bool = False,
    ) -> None:
        """Record an API call."""
        name = f"api:{model}"

        with self._lock:
            self._counts[name] += 1
            self._durations[name].append(duration)

            if error:
                self._errors[name] += 1

            self._metrics[name].append(PerformanceMetric(
                name=name,
                metric_type=MetricType.DURATION,
                value=duration,
                timestamp=time.time(),
                metadata={
                    "tokens": tokens,
                    "cache_hits": cache_hits,
                    "error": error,
                },
            ))

    def get_summary(self, name: str) -> PerformanceSummary:
        """Get performance summary for a named operation."""
        with self._lock:
            durations = list(self._durations.get(name, []))
            count = self._counts.get(name, 0)
            errors = self._errors.get(name, 0)

        if not durations:
            return PerformanceSummary(name=name)

        durations.sort()
        n = len(durations)

        summary = PerformanceSummary(
            name=name,
            total_calls=count,
            total_duration=sum(durations),
            avg_duration=sum(durations) / n,
            min_duration=durations[0],
            max_duration=durations[-1],
            error_count=errors,
            error_rate=errors / count if count > 0 else 0,
            p50_duration=durations[int(n * 0.5)],
            p95_duration=durations[int(n * 0.95)] if n > 1 else durations[0],
            p99_duration=durations[int(n * 0.99)] if n > 1 else durations[0],
        )

        return summary

    def get_all_summaries(self) -> List[PerformanceSummary]:
        """Get summaries for all tracked operations."""
        with self._lock:
            names = list(self._durations.keys())

        return [self.get_summary(name) for name in names]

    def get_slowest(self, limit: int = 5) -> List[PerformanceSummary]:
        """Get the slowest operations by average duration."""
        summaries = self.get_all_summaries()
        return sorted(summaries, key=lambda s: s.avg_duration, reverse=True)[:limit]

    def get_most_errors(self, limit: int = 5) -> List[PerformanceSummary]:
        """Get operations with most errors."""
        summaries = self.get_all_summaries()
        return sorted(summaries, key=lambda s: s.error_count, reverse=True)[:limit]

    def get_recent_metrics(
        self,
        name: str,
        since: float,
        limit: int = 100,
    ) -> List[PerformanceMetric]:
        """Get recent metrics for an operation."""
        with self._lock:
            metrics = [
                m for m in self._metrics.get(name, [])
                if m.timestamp >= since
            ]
        return metrics[-limit:]

    def generate_report(self) -> str:
        """Generate a performance report."""
        summaries = self.get_all_summaries()
        uptime = time.time() - self._start_time

        lines = [
            "=" * 60,
            "PERFORMANCE REPORT",
            "=" * 60,
            f"Uptime: {uptime:.1f}s",
            f"Tracked Operations: {len(summaries)}",
            "",
        ]

        if summaries:
            # Overall stats
            total_calls = sum(s.total_calls for s in summaries)
            total_duration = sum(s.total_duration for s in summaries)
            total_errors = sum(s.error_count for s in summaries)

            lines.extend([
                "Overall:",
                f"  Total Calls: {total_calls}",
                f"  Total Duration: {total_duration:.2f}s",
                f"  Total Errors: {total_errors}",
                f"  Overall Error Rate: {(total_errors/total_calls*100) if total_calls else 0:.1f}%",
                "",
            ])

            # Slowest operations
            lines.append("Top 5 Slowest (by avg duration):")
            for i, s in enumerate(self.get_slowest(5), 1):
                lines.append(f"  {i}. {s.name}: {s.avg_duration:.3f}s avg ({s.total_calls} calls)")

            lines.append("")

            # Error-prone operations
            error_ops = [s for s in summaries if s.error_count > 0]
            if error_ops:
                lines.append("Operations with Errors:")
                for s in sorted(error_ops, key=lambda x: x.error_rate, reverse=True)[:5]:
                    lines.append(
                        f"  - {s.name}: {s.error_count} errors "
                        f"({s.error_rate*100:.1f}% error rate)"
                    )
                lines.append("")

            # Detailed table
            lines.append("All Operations:")
            lines.append(f"  {'Name':<30} {'Calls':>8} {'Avg':>10} {'P95':>10} {'Errors':>8}")
            lines.append("  " + "-" * 70)
            for s in sorted(summaries, key=lambda x: x.total_calls, reverse=True):
                lines.append(
                    f"  {s.name:<30} {s.total_calls:>8} "
                    f"{s.avg_duration:>10.3f}s {s.p95_duration:>10.3f}s {s.error_count:>8}"
                )
        else:
            lines.append("No performance data collected yet.")

        lines.append("=" * 60)
        return "\n".join(lines)

    def export_json(self) -> str:
        """Export performance data as JSON."""
        summaries = [s.to_dict() for s in self.get_all_summaries()]
        return json.dumps({
            "uptime": time.time() - self._start_time,
            "summaries": summaries,
        }, indent=2)

    def clear(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
            self._durations.clear()
            self._counts.clear()
            self._errors.clear()
        self._start_time = time.time()


class PerformanceTracker:
    """Context manager for tracking operation duration."""

    def __init__(
        self,
        analyzer: PerformanceAnalyzer,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self._analyzer = analyzer
        self._name = name
        self._metadata = metadata
        self._start_time: Optional[float] = None
        self._success = True

    def __enter__(self) -> "PerformanceTracker":
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        duration = time.time() - self._start_time if self._start_time else 0
        self._success = exc_type is None
        self._analyzer.record_tool(
            self._name,
            duration,
            success=self._success,
            metadata=self._metadata,
        )
        return False

    def mark_error(self) -> None:
        """Mark the operation as an error."""
        self._success = False


# Global analyzer instance

_performance_analyzer: Optional[PerformanceAnalyzer] = None

def get_performance_analyzer() -> PerformanceAnalyzer:
    """Get the global performance analyzer."""
    global _performance_analyzer
    if _performance_analyzer is None:
        _performance_analyzer = PerformanceAnalyzer()
    return _performance_analyzer
