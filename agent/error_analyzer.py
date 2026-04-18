"""Error Analyzer for Hermes Agent.

Analyzes errors and provides actionable fix suggestions.
"""

from __future__ import annotations

import json
import logging
import threading
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity level of an error."""
    CRITICAL = "critical"     # Must fix immediately
    HIGH = "high"             # Should fix soon
    MEDIUM = "medium"         # Should investigate
    LOW = "low"              # Can be ignored


class ErrorCategory(Enum):
    """Category of an error."""
    API = "api"               # API-related errors
    AUTH = "auth"             # Authentication/authorization
    NETWORK = "network"       # Network connectivity
    TOOL = "tool"             # Tool execution errors
    CONTEXT = "context"       # Context/memory errors
    CONFIG = "config"         # Configuration errors
    UNKNOWN = "unknown"


@dataclass
class ErrorSuggestion:
    """A suggestion to fix an error."""
    action: str
    description: str
    command: Optional[str] = None
    docs_url: Optional[str] = None
    priority: int = 1  # 1 = highest priority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "description": self.description,
            "command": self.command,
            "docs_url": self.docs_url,
            "priority": self.priority,
        }


@dataclass
class AnalyzedError:
    """A fully analyzed error with suggestions."""
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    suggestions: List[ErrorSuggestion]
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "context": self.context,
            "timestamp": self.timestamp,
        }


class ErrorAnalyzer:
    """Analyzes errors and provides actionable fix suggestions.
    
    Usage:
        analyzer = ErrorAnalyzer()
        
        # Analyze an error
        result = analyzer.analyze(error_data)
        
        # Print suggestions
        for suggestion in result.suggestions:
            print(f"  {suggestion.action}: {suggestion.description}")
        
        # Get error history
        history = analyzer.get_history()
        
        # Generate report
        report = analyzer.generate_report()
    """

    # Error pattern definitions
    ERROR_PATTERNS = {
        # API Errors
        "api_timeout": {
            "patterns": ["timeout", "timed out", "request timeout"],
            "category": ErrorCategory.API,
            "severity": ErrorSeverity.MEDIUM,
        },
        "api_rate_limit": {
            "patterns": ["rate limit", "429", "too many requests"],
            "category": ErrorCategory.API,
            "severity": ErrorSeverity.HIGH,
        },
        "api_auth": {
            "patterns": ["401", "403", "unauthorized", "forbidden", "authentication"],
            "category": ErrorCategory.AUTH,
            "severity": ErrorSeverity.CRITICAL,
        },
        "api_quota": {
            "patterns": ["quota", "exceeded", "limit", "credits"],
            "category": ErrorCategory.API,
            "severity": ErrorSeverity.HIGH,
        },
        "api_server_error": {
            "patterns": ["500", "502", "503", "504", "server error", "internal error"],
            "category": ErrorCategory.API,
            "severity": ErrorSeverity.MEDIUM,
        },
        "api_invalid_request": {
            "patterns": ["400", "bad request", "invalid request"],
            "category": ErrorCategory.API,
            "severity": ErrorSeverity.HIGH,
        },
        # Network Errors
        "network_connection": {
            "patterns": ["connection", "connect", "network", "refused", "unreachable"],
            "category": ErrorCategory.NETWORK,
            "severity": ErrorSeverity.HIGH,
        },
        "network_dns": {
            "patterns": ["dns", "hostname", "resolve"],
            "category": ErrorCategory.NETWORK,
            "severity": ErrorSeverity.MEDIUM,
        },
        # Tool Errors
        "tool_not_found": {
            "patterns": ["tool not found", "unknown tool", "invalid tool"],
            "category": ErrorCategory.TOOL,
            "severity": ErrorSeverity.HIGH,
        },
        "tool_execution": {
            "patterns": ["execution failed", "tool error", "failed to execute"],
            "category": ErrorCategory.TOOL,
            "severity": ErrorSeverity.MEDIUM,
        },
        "tool_timeout": {
            "patterns": ["tool timeout", "execution timeout"],
            "category": ErrorCategory.TOOL,
            "severity": ErrorSeverity.MEDIUM,
        },
        # Context Errors
        "context_overflow": {
            "patterns": ["context overflow", "too many tokens", "context limit", "maximum context"],
            "category": ErrorCategory.CONTEXT,
            "severity": ErrorSeverity.HIGH,
        },
        "context_compression": {
            "patterns": ["compression", "compress context"],
            "category": ErrorCategory.CONTEXT,
            "severity": ErrorSeverity.LOW,
        },
        # Config Errors
        "config_missing": {
            "patterns": ["config", "configuration", "missing", "not found"],
            "category": ErrorCategory.CONFIG,
            "severity": ErrorSeverity.HIGH,
        },
    }

    # Fix suggestions by error type
    FIX_SUGGESTIONS = {
        "api_timeout": [
            ErrorSuggestion(
                action="Increase timeout",
                description="Set a longer timeout for API calls",
                command="export HERMES_API_TIMEOUT=120",
                priority=1,
            ),
            ErrorSuggestion(
                action="Retry",
                description="The server may be temporarily overloaded",
                priority=2,
            ),
        ],
        "api_rate_limit": [
            ErrorSuggestion(
                action="Wait and retry",
                description="Rate limit hit. Wait before retrying.",
                priority=1,
            ),
            ErrorSuggestion(
                action="Implement backoff",
                description="Use exponential backoff for retries",
                priority=2,
            ),
            ErrorSuggestion(
                action="Upgrade plan",
                description="Consider upgrading your API plan for higher limits",
                priority=3,
            ),
        ],
        "api_auth": [
            ErrorSuggestion(
                action="Check API key",
                description="Verify your API key is correct",
                command="hermes config set api_key YOUR_KEY",
                priority=1,
            ),
            ErrorSuggestion(
                action="Check permissions",
                description="Ensure your API key has required permissions",
                priority=2,
            ),
        ],
        "api_quota": [
            ErrorSuggestion(
                action="Check usage",
                description="Review your API usage and quotas",
                priority=1,
            ),
            ErrorSuggestion(
                action="Add credits",
                description="Add credits to your API account",
                priority=1,
            ),
        ],
        "network_connection": [
            ErrorSuggestion(
                action="Check connection",
                description="Verify your internet connection",
                priority=1,
            ),
            ErrorSuggestion(
                action="Check firewall",
                description="Ensure firewall allows outbound connections",
                priority=2,
            ),
        ],
        "context_overflow": [
            ErrorSuggestion(
                action="Compress context",
                description="Trigger context compression to reduce size",
                command=None,
                priority=1,
            ),
            ErrorSuggestion(
                action="Clear history",
                description="Start a new session or clear conversation history",
                command="/reset",
                priority=2,
            ),
            ErrorSuggestion(
                action="Use smaller model",
                description="Use a model with larger context window",
                command="/model claude-3-5-sonnet-200k",
                priority=3,
            ),
        ],
        "tool_not_found": [
            ErrorSuggestion(
                action="Check tool name",
                description="Verify the tool name is correct",
                priority=1,
            ),
            ErrorSuggestion(
                action="Enable toolset",
                description="Ensure the tool's toolset is enabled",
                command="hermes tools enable <toolset>",
                priority=2,
            ),
        ],
        "config_missing": [
            ErrorSuggestion(
                action="Run setup",
                description="Run the setup wizard to configure",
                command="hermes setup",
                priority=1,
            ),
            ErrorSuggestion(
                action="Check config file",
                description="Verify config.yaml exists and is valid",
                command="cat ~/.hermes/config.yaml",
                priority=2,
            ),
        ],
    }

    def __init__(self):
        self._history: List[AnalyzedError] = []
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def analyze(
        self,
        error_data: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnalyzedError:
        """Analyze an error and generate suggestions.
        
        Args:
            error_data: Error information (dict, Exception, or string)
            context: Additional context about the error
            
        Returns:
            AnalyzedError with category, severity, and suggestions
        """
        # Extract error info
        if isinstance(error_data, Exception):
            error_type = type(error_data).__name__
            message = str(error_data)
            tb = traceback.format_exception(type(error_data), error_data, error_data.__traceback__)
        elif isinstance(error_data, dict):
            error_type = error_data.get("type", error_data.get("error_type", "Unknown"))
            message = error_data.get("message", error_data.get("error", ""))
            tb = error_data.get("traceback", [])
        else:
            error_type = "Unknown"
            message = str(error_data)
            tb = []

        # Classify error
        category, severity, error_key = self._classify_error(message)

        # Get suggestions
        suggestions = self._get_suggestions(error_key, category)

        # Create analyzed error
        analyzed = AnalyzedError(
            error_type=error_type,
            message=message,
            category=category,
            severity=severity,
            suggestions=suggestions,
            context=context or {},
            timestamp=datetime.now().timestamp(),
        )

        # Record in history
        with self._lock:
            self._history.append(analyzed)
            self._error_counts[error_key] += 1

        return analyzed

    def _classify_error(self, message: str) -> tuple:
        """Classify an error based on its message."""
        message_lower = message.lower()

        for error_key, info in self.ERROR_PATTERNS.items():
            for pattern in info["patterns"]:
                if pattern.lower() in message_lower:
                    return info["category"], info["severity"], error_key

        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM, "unknown"

    def _get_suggestions(
        self,
        error_key: str,
        category: ErrorCategory,
    ) -> List[ErrorSuggestion]:
        """Get fix suggestions for an error."""
        suggestions = []

        # Get specific suggestions
        if error_key in self.FIX_SUGGESTIONS:
            suggestions.extend(self.FIX_SUGGESTIONS[error_key])

        # Add category-based suggestions
        if category == ErrorCategory.API:
            suggestions.append(ErrorSuggestion(
                action="Check API status",
                description="Check provider status page for outages",
                docs_url="https://status.anthropic.com",
                priority=5,
            ))
        elif category == ErrorCategory.NETWORK:
            suggestions.append(ErrorSuggestion(
                action="Check proxy settings",
                description="If behind proxy, configure HERMES_PROXY",
                priority=5,
            ))

        # Sort by priority
        suggestions.sort(key=lambda s: s.priority)
        return suggestions[:5]  # Max 5 suggestions

    def explain_error(self, error_data: Any) -> str:
        """Generate a human-readable error explanation.
        
        Args:
            error_data: Error information
            
        Returns:
            Formatted explanation string
        """
        analyzed = self.analyze(error_data)

        lines = [
            "=" * 50,
            "ERROR ANALYSIS",
            "=" * 50,
            f"Type: {analyzed.error_type}",
            f"Category: {analyzed.category.value}",
            f"Severity: {analyzed.severity.value}",
            "",
            f"Message: {analyzed.message}",
            "",
            "Suggestions:",
        ]

        for i, suggestion in enumerate(analyzed.suggestions, 1):
            lines.append(f"  {i}. {suggestion.action}")
            lines.append(f"     {suggestion.description}")
            if suggestion.command:
                lines.append(f"     Command: {suggestion.command}")
            if suggestion.docs_url:
                lines.append(f"     Docs: {suggestion.docs_url}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def get_history(
        self,
        category: Optional[ErrorCategory] = None,
        limit: int = 100,
    ) -> List[AnalyzedError]:
        """Get error history."""
        with self._lock:
            history = list(self._history)

        if category:
            history = [e for e in history if e.category == category]

        return history[-limit:]

    def get_error_counts(self) -> Dict[str, int]:
        """Get counts of each error type."""
        with self._lock:
            return dict(self._error_counts)

    def generate_report(self) -> str:
        """Generate an error analysis report."""
        with self._lock:
            history = list(self._history)
            counts = dict(self._error_counts)

        if not history:
            return "No errors recorded yet."

        # Count by category
        by_category: Dict[str, int] = defaultdict(int)
        for error in history:
            by_category[error.category.value] += 1

        # Count by severity
        by_severity: Dict[str, int] = defaultdict(int)
        for error in history:
            by_severity[error.severity.value] += 1

        lines = [
            "=" * 60,
            "ERROR ANALYSIS REPORT",
            "=" * 60,
            f"Total Errors: {len(history)}",
            "",
            "By Category:",
        ]

        for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {cat}: {count}")

        lines.extend(["", "By Severity:"])
        for sev, count in sorted(by_severity.items()):
            lines.append(f"  {sev}: {count}")

        # Most common errors
        if counts:
            lines.extend(["", "Most Common:"])
            for err_type, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"  {err_type}: {count}")

        # Recent errors
        lines.extend(["", "Recent Errors:"])
        for error in history[-5:]:
            lines.append(
                f"  [{error.severity.value}] {error.error_type}: "
                f"{error.message[:50]}..."
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def export_json(self) -> str:
        """Export error history as JSON."""
        with self._lock:
            return json.dumps({
                "error_counts": self._error_counts,
                "history": [e.to_dict() for e in self._history],
            }, indent=2)

    def clear(self) -> None:
        """Clear error history."""
        with self._lock:
            self._history.clear()
            self._error_counts.clear()


# Global analyzer instance

_error_analyzer: Optional[ErrorAnalyzer] = None

def get_error_analyzer() -> ErrorAnalyzer:
    """Get the global error analyzer."""
    global _error_analyzer
    if _error_analyzer is None:
        _error_analyzer = ErrorAnalyzer()
    return _error_analyzer
