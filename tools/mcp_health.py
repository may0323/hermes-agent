#!/usr/bin/env python3
"""
MCP Health Monitor Module

This module provides health monitoring for MCP (Model Context Protocol) servers.
Tracks server health metrics, performs health checks, and provides alerts.

Features:
- Health check scheduling and execution
- Latency and availability tracking
- Error rate monitoring
- Resource usage monitoring
- Health history and alerts
- Configurable health thresholds

Usage:
    from tools.mcp_health import HealthMonitor, HealthStatus
    
    monitor = HealthMonitor()
    status = monitor.check_server_health("my_server")
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)


class HealthLevel(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MetricType(Enum):
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"


@dataclass
class HealthCheckResult:
    server_name: str
    level: HealthLevel
    latency_ms: Optional[float] = None
    error_count: int = 0
    total_requests: int = 0
    error_rate: float = 0.0
    availability: float = 100.0
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthThreshold:
    latency_ms: float = 1000.0
    error_rate: float = 0.05
    availability: float = 95.0
    min_requests_for_threshold: int = 10


@dataclass
class HealthHistoryEntry:
    server_name: str
    level: HealthLevel
    latency_ms: Optional[float]
    error_rate: float
    availability: float
    timestamp: float


class HealthMonitor:
    def __init__(self, max_history: int = 100):
        self._health_data: Dict[str, HealthCheckResult] = {}
        self._history: Dict[str, List[HealthHistoryEntry]] = {}
        self._thresholds: Dict[str, HealthThreshold] = {}
        self._lock = threading.RLock()
        self._max_history = max_history
        self._callbacks: List[Callable[[HealthCheckResult], None]] = []
        self._alert_handlers: Dict[str, List[Callable]] = {}

    def register_server(self, name: str, threshold: Optional[HealthThreshold] = None) -> None:
        with self._lock:
            if threshold:
                self._thresholds[name] = threshold
            else:
                self._thresholds[name] = HealthThreshold()
            if name not in self._history:
                self._history[name] = []

    def unregister_server(self, name: str) -> None:
        with self._lock:
            if name in self._health_data:
                del self._health_data[name]
            if name in self._history:
                del self._history[name]
            if name in self._thresholds:
                del self._thresholds[name]

    def record_request(
        self,
        server_name: str,
        latency_ms: Optional[float] = None,
        error: bool = False,
    ) -> None:
        with self._lock:
            if server_name not in self._health_data:
                self._health_data[server_name] = HealthCheckResult(
                    server_name=server_name,
                    level=HealthLevel.UNKNOWN,
                )

            data = self._health_data[server_name]
            data.total_requests += 1
            if error:
                data.error_count += 1
            if latency_ms is not None:
                data.latency_ms = latency_ms

            data.error_rate = data.error_count / data.total_requests if data.total_requests > 0 else 0

            threshold = self._thresholds.get(server_name, HealthThreshold())
            if data.total_requests >= threshold.min_requests_for_threshold:
                data.level = self._calculate_level(data, threshold)

            self._update_history(server_name, data)

    def _calculate_level(self, data: HealthCheckResult, threshold: HealthThreshold) -> HealthLevel:
        if data.latency_ms is not None and data.latency_ms > threshold.latency_ms:
            return HealthLevel.DEGRADED
        if data.error_rate > threshold.error_rate:
            return HealthLevel.UNHEALTHY
        if data.availability < threshold.availability:
            return HealthLevel.DEGRADED
        if data.error_rate > 0 or (data.latency_ms is not None and data.latency_ms > threshold.latency_ms * 0.5):
            return HealthLevel.DEGRADED
        return HealthLevel.HEALTHY

    def _update_history(self, server_name: str, data: HealthCheckResult) -> None:
        entry = HealthHistoryEntry(
            server_name=server_name,
            level=data.level,
            latency_ms=data.latency_ms,
            error_rate=data.error_rate,
            availability=data.availability,
            timestamp=time.time(),
        )
        self._history[server_name].append(entry)
        if len(self._history[server_name]) > self._max_history:
            self._history[server_name].pop(0)

    def get_health(self, server_name: str) -> Optional[HealthCheckResult]:
        return self._health_data.get(server_name)

    def get_all_health(self) -> List[HealthCheckResult]:
        return list(self._health_data.values())

    def get_history(
        self,
        server_name: str,
        limit: int = 50,
    ) -> List[HealthHistoryEntry]:
        history = self._history.get(server_name, [])
        return history[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._health_data)
            by_level: Dict[str, int] = {}
            for data in self._health_data.values():
                level = data.level.value
                by_level[level] = by_level.get(level, 0) + 1

            return {
                "total_servers": total,
                "by_health_level": by_level,
                "servers": [
                    {
                        "name": data.server_name,
                        "level": data.level.value,
                        "latency_ms": data.latency_ms,
                        "error_rate": round(data.error_rate, 4),
                        "availability": data.availability,
                        "total_requests": data.total_requests,
                    }
                    for data in self._health_data.values()
                ]
            }

    def check_health(self, server_name: str) -> HealthCheckResult:
        data = self._health_data.get(server_name)
        if not data:
            return HealthCheckResult(
                server_name=server_name,
                level=HealthLevel.UNKNOWN,
                message="Server not registered",
            )

        threshold = self._thresholds.get(server_name, HealthThreshold())
        data.level = self._calculate_level(data, threshold)

        if data.level == HealthLevel.UNHEALTHY:
            self._trigger_alert(server_name, data)

        return data

    def add_alert_handler(self, level: str, handler: Callable) -> None:
        if level not in self._alert_handlers:
            self._alert_handlers[level] = []
        self._alert_handlers[level].append(handler)

    def _trigger_alert(self, server_name: str, data: HealthCheckResult) -> None:
        level_key = data.level.value
        if level_key in self._alert_handlers:
            for handler in self._alert_handlers[level_key]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")


_monitor = HealthMonitor()


def mcp_health_tool(
    action: str,
    server_name: str = "",
    config_json: str = "{}",
    task_id: Optional[str] = None,
) -> str:
    """Monitor MCP server health.
    
    Args:
        action: Action to perform (check, status, history, summary, register, record)
        server_name: Server name for health checks
        config_json: JSON configuration for server registration
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with health information.
    """
    try:
        if action == "summary":
            return json.dumps({
                "success": True,
                "data": _monitor.get_summary()
            })

        if action == "status":
            if not server_name:
                return json.dumps({
                    "success": False,
                    "error": "server_name is required for status action",
                    "error_code": "MISSING_SERVER_NAME"
                })
            result = _monitor.get_health(server_name)
            if not result:
                return json.dumps({
                    "success": True,
                    "data": {
                        "server_name": server_name,
                        "level": "unknown",
                        "message": "No health data available"
                    }
                })
            return json.dumps({
                "success": True,
                "data": {
                    "server_name": result.server_name,
                    "level": result.level.value,
                    "latency_ms": result.latency_ms,
                    "error_rate": round(result.error_rate, 4),
                    "availability": result.availability,
                    "total_requests": result.total_requests,
                    "error_count": result.error_count,
                    "message": result.message,
                    "timestamp": result.timestamp,
                }
            })

        if action == "check":
            if not server_name:
                return json.dumps({
                    "success": False,
                    "error": "server_name is required for check action",
                    "error_code": "MISSING_SERVER_NAME"
                })
            result = _monitor.check_health(server_name)
            return json.dumps({
                "success": True,
                "data": {
                    "server_name": result.server_name,
                    "level": result.level.value,
                    "latency_ms": result.latency_ms,
                    "error_rate": round(result.error_rate, 4),
                    "availability": result.availability,
                    "message": result.message,
                }
            })

        if action == "history":
            if not server_name:
                return json.dumps({
                    "success": False,
                    "error": "server_name is required for history action",
                    "error_code": "MISSING_SERVER_NAME"
                })
            history = _monitor.get_history(server_name)
            return json.dumps({
                "success": True,
                "data": {
                    "server_name": server_name,
                    "entries": [
                        {
                            "level": e.level.value,
                            "latency_ms": e.latency_ms,
                            "error_rate": round(e.error_rate, 4),
                            "availability": e.availability,
                            "timestamp": e.timestamp,
                        }
                        for e in history
                    ],
                    "count": len(history)
                }
            })

        if action == "register":
            if not server_name:
                return json.dumps({
                    "success": False,
                    "error": "server_name is required for register action",
                    "error_code": "MISSING_SERVER_NAME"
                })
            try:
                config = json.loads(config_json) if config_json else {}
            except json.JSONDecodeError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid JSON config: {e}",
                    "error_code": "INVALID_JSON"
                })

            threshold = HealthThreshold(
                latency_ms=config.get("latency_ms", 1000.0),
                error_rate=config.get("error_rate", 0.05),
                availability=config.get("availability", 95.0),
                min_requests_for_threshold=config.get("min_requests", 10),
            )
            _monitor.register_server(server_name, threshold)
            return json.dumps({
                "success": True,
                "data": {
                    "server_name": server_name,
                    "message": f"Server '{server_name}' registered for health monitoring"
                }
            })

        if action == "unregister":
            if not server_name:
                return json.dumps({
                    "success": False,
                    "error": "server_name is required for unregister action",
                    "error_code": "MISSING_SERVER_NAME"
                })
            _monitor.unregister_server(server_name)
            return json.dumps({
                "success": True,
                "data": {
                    "server_name": server_name,
                    "message": f"Server '{server_name}' unregistered"
                }
            })

        if action == "record":
            if not server_name:
                return json.dumps({
                    "success": False,
                    "error": "server_name is required for record action",
                    "error_code": "MISSING_SERVER_NAME"
                })
            try:
                config = json.loads(config_json) if config_json else {}
            except json.JSONDecodeError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid JSON config: {e}",
                    "error_code": "INVALID_JSON"
                })

            _monitor.record_request(
                server_name=server_name,
                latency_ms=config.get("latency_ms"),
                error=config.get("error", False),
            )
            return json.dumps({
                "success": True,
                "data": {
                    "server_name": server_name,
                    "message": "Request recorded"
                }
            })

        return json.dumps({
            "success": False,
            "error": f"Unknown action: {action}",
            "error_code": "INVALID_ACTION"
        })

    except Exception as e:
        logger.exception("Error in mcp_health_tool")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "HEALTH_ERROR"
        })


registry.register(
    name="mcp_health",
    toolset="mcp",
    schema={
        "name": "mcp_health",
        "description": """Monitor MCP server health.

Use this tool when you need to:
- Check health status of MCP servers
- View health history
- Get health summary across all servers
- Register/unregister servers for monitoring
- Record request metrics for health tracking

Tracks latency, error rates, and availability metrics.""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["check", "status", "history", "summary", "register", "unregister", "record"]
                },
                "server_name": {
                    "type": "string",
                    "description": "Server name for health operations"
                },
                "config_json": {
                    "type": "string",
                    "description": "JSON configuration for registration or record"
                }
            },
            "required": ["action"]
        }
    },
    handler=lambda args, **kw: mcp_health_tool(
        action=args.get("action", "summary"),
        server_name=args.get("server_name", ""),
        config_json=args.get("config_json", "{}"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)
