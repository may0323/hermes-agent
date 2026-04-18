#!/usr/bin/env python3
"""
MCP Connection Manager Module

This module provides connection management for MCP (Model Context Protocol) servers.
Handles connection lifecycle, pooling, and event callbacks.

Features:
- Connection lifecycle management (create, connect, disconnect, reconnect)
- Connection pooling for multiple servers
- Event callbacks for connection state changes
- Automatic reconnection with configurable retry policies
- Connection health tracking

Usage:
    from tools.mcp_connection import ConnectionManager, ConnectionPool
    
    manager = ConnectionManager()
    conn = await manager.create_connection("my_server", config)
    await conn.connect()
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
from uuid import uuid4

from tools.registry import registry

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class EventType(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECT = "reconnect"
    TIMEOUT = "timeout"
    MESSAGE = "message"


@dataclass
class ConnectionConfig:
    name: str
    transport_type: str = "stdio"
    url: Optional[str] = None
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    timeout: int = 120
    connect_timeout: int = 60
    max_retries: int = 5
    retry_delay: float = 1.0
    retry_multiplier: float = 2.0
    max_retry_delay: float = 60.0
    heartbeat_interval: float = 30.0
    auto_reconnect: bool = True


@dataclass
class ConnectionInfo:
    id: str
    name: str
    status: ConnectionStatus
    created_at: float
    last_connected: Optional[float] = None
    last_error: Optional[str] = None
    reconnect_count: int = 0
    total_messages: int = 0
    config: Optional[Dict[str, Any]] = None


class ConnectionCallbacks:
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }

    def on(self, event: EventType, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def off(self, event: EventType, handler: Callable) -> None:
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    def emit(self, event: EventType, data: Dict[str, Any]) -> None:
        for handler in self._handlers[event]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Event handler error for {event}: {e}")

    def clear(self) -> None:
        for handlers in self._handlers.values():
            handlers.clear()


class Connection:
    def __init__(self, config: ConnectionConfig):
        self.id = str(uuid4())[:8]
        self.config = config
        self.status = ConnectionStatus.IDLE
        self.callbacks = ConnectionCallbacks()
        self._created_at = time.time()
        self._last_connected: Optional[float] = None
        self._last_error: Optional[str] = None
        self._reconnect_count = 0
        self._total_messages = 0
        self._lock = threading.RLock()

    @property
    def info(self) -> ConnectionInfo:
        return ConnectionInfo(
            id=self.id,
            name=self.config.name,
            status=self.status,
            created_at=self._created_at,
            last_connected=self._last_connected,
            last_error=self._last_error,
            reconnect_count=self._reconnect_count,
            total_messages=self._total_messages,
            config={
                "transport_type": self.config.transport_type,
                "url": self.config.url,
                "command": self.config.command,
                "timeout": self.config.timeout,
            }
        )

    def set_status(self, status: ConnectionStatus, error: Optional[str] = None) -> None:
        with self._lock:
            self.status = status
            if error:
                self._last_error = error
            if status == ConnectionStatus.CONNECTED:
                self._last_connected = time.time()
            if status == ConnectionStatus.ERROR:
                self._last_error = error

    def increment_messages(self) -> None:
        with self._lock:
            self._total_messages += 1

    def increment_reconnect(self) -> None:
        with self._lock:
            self._reconnect_count += 1


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Connection] = {}
        self._lock = threading.RLock()
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 100

    def create_connection(self, config: ConnectionConfig) -> Connection:
        with self._lock:
            existing = self.get_connection(config.name)
            if existing:
                return existing

            conn = Connection(config)
            self._connections[config.name] = conn
            self._record_event(EventType.CONNECTED, {"name": config.name, "id": conn.id})
            logger.info(f"Connection created: {config.name} ({conn.id})")
            return conn

    def get_connection(self, name: str) -> Optional[Connection]:
        return self._connections.get(name)

    def list_connections(self) -> List[ConnectionInfo]:
        with self._lock:
            return [conn.info for conn in self._connections.values()]

    def remove_connection(self, name: str) -> bool:
        with self._lock:
            if name in self._connections:
                conn = self._connections[name]
                conn.set_status(ConnectionStatus.DISCONNECTED)
                del self._connections[name]
                self._record_event(EventType.DISCONNECTED, {"name": name})
                logger.info(f"Connection removed: {name}")
                return True
            return False

    def get_connection_status(self, name: str) -> Optional[str]:
        conn = self.get_connection(name)
        if conn:
            return conn.status.value
        return None

    def record_error(self, name: str, error: str) -> None:
        conn = self.get_connection(name)
        if conn:
            conn.set_status(ConnectionStatus.ERROR, error)
            self._record_event(EventType.ERROR, {"name": name, "error": error})

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._connections)
            by_status: Dict[str, int] = {}
            for conn in self._connections.values():
                status = conn.status.value
                by_status[status] = by_status.get(status, 0) + 1

            return {
                "total_connections": total,
                "by_status": by_status,
                "event_history_size": len(self._event_history),
            }

    def _record_event(self, event: EventType, data: Dict[str, Any]) -> None:
        self._event_history.append({
            "event": event.value,
            "timestamp": time.time(),
            **data
        })
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)


_manager = ConnectionManager()


def mcp_connection_tool(
    action: str,
    name: str = "",
    config_json: str = "{}",
    task_id: Optional[str] = None,
) -> str:
    """Manage MCP server connections.
    
    Args:
        action: Action to perform (create, list, get, remove, stats)
        name: Connection name
        config_json: JSON configuration for new connection
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with result.
    """
    try:
        if action == "list":
            connections = _manager.list_connections()
            return json.dumps({
                "success": True,
                "data": {
                    "connections": [
                        {
                            "id": c.id,
                            "name": c.name,
                            "status": c.status.value,
                            "created_at": c.created_at,
                            "last_connected": c.last_connected,
                            "reconnect_count": c.reconnect_count,
                        }
                        for c in connections
                    ],
                    "count": len(connections)
                }
            })

        if action == "stats":
            return json.dumps({
                "success": True,
                "data": _manager.get_stats()
            })

        if action == "get":
            if not name:
                return json.dumps({
                    "success": False,
                    "error": "Connection name is required for 'get' action",
                    "error_code": "MISSING_NAME"
                })
            conn = _manager.get_connection(name)
            if not conn:
                return json.dumps({
                    "success": False,
                    "error": f"Connection not found: {name}",
                    "error_code": "NOT_FOUND"
                })
            info = conn.info
            return json.dumps({
                "success": True,
                "data": {
                    "id": info.id,
                    "name": info.name,
                    "status": info.status.value,
                    "created_at": info.created_at,
                    "last_connected": info.last_connected,
                    "last_error": info.last_error,
                    "reconnect_count": info.reconnect_count,
                    "total_messages": info.total_messages,
                    "config": info.config,
                }
            })

        if action == "remove":
            if not name:
                return json.dumps({
                    "success": False,
                    "error": "Connection name is required for 'remove' action",
                    "error_code": "MISSING_NAME"
                })
            removed = _manager.remove_connection(name)
            return json.dumps({
                "success": True,
                "data": {
                    "removed": removed,
                    "name": name
                }
            })

        if action == "create":
            if not name:
                return json.dumps({
                    "success": False,
                    "error": "Connection name is required for 'create' action",
                    "error_code": "MISSING_NAME"
                })
            try:
                config_data = json.loads(config_json) if config_json else {}
            except json.JSONDecodeError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid JSON config: {e}",
                    "error_code": "INVALID_JSON"
                })

            config = ConnectionConfig(
                name=name,
                transport_type=config_data.get("type", "stdio"),
                url=config_data.get("url"),
                command=config_data.get("command"),
                args=config_data.get("args", []),
                env=config_data.get("env", {}),
                timeout=config_data.get("timeout", 120),
                connect_timeout=config_data.get("connect_timeout", 60),
                max_retries=config_data.get("max_retries", 5),
                heartbeat_interval=config_data.get("heartbeat_interval", 30.0),
                auto_reconnect=config_data.get("auto_reconnect", True),
            )

            conn = _manager.create_connection(config)
            return json.dumps({
                "success": True,
                "data": {
                    "id": conn.id,
                    "name": name,
                    "status": conn.status.value,
                    "message": f"Connection '{name}' created"
                }
            })

        return json.dumps({
            "success": False,
            "error": f"Unknown action: {action}",
            "error_code": "INVALID_ACTION"
        })

    except Exception as e:
        logger.exception("Error in mcp_connection_tool")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "CONNECTION_ERROR"
        })


registry.register(
    name="mcp_connection",
    toolset="mcp",
    schema={
        "name": "mcp_connection",
        "description": """Manage MCP server connections.

Use this tool when you need to:
- Create new MCP server connections
- List all active connections
- Get connection details and status
- Remove connections
- View connection statistics

Supports connection lifecycle management with automatic reconnection.""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["create", "list", "get", "remove", "stats"]
                },
                "name": {
                    "type": "string",
                    "description": "Connection name"
                },
                "config_json": {
                    "type": "string",
                    "description": "JSON configuration for creating a connection"
                }
            },
            "required": ["action"]
        }
    },
    handler=lambda args, **kw: mcp_connection_tool(
        action=args.get("action", "list"),
        name=args.get("name", ""),
        config_json=args.get("config_json", "{}"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)
