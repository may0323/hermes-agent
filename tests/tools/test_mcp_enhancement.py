"""Tests for tools/mcp_transport.py, mcp_connection.py, and mcp_health.py."""

import json

import pytest

from tools.mcp_connection import (
    ConnectionConfig,
    ConnectionManager,
    ConnectionStatus,
    EventType,
    mcp_connection_tool,
)
from tools.mcp_health import (
    HealthLevel,
    HealthThreshold,
    HealthMonitor,
    mcp_health_tool,
)
from tools.mcp_transport import (
    ConnectionState,
    TransportConfig,
    TransportFactory,
    TransportType,
    mcp_transport_tool,
)


class TestMcpTransportTool:
    def test_list_transport_types(self):
        result = mcp_transport_tool(action="list")
        data = json.loads(result)
        assert data["success"] is True
        assert "transport_types" in data["data"]
        assert "connection_states" in data["data"]
        assert "stdio" in data["data"]["transport_types"]

    def test_create_stdio_transport(self):
        config = json.dumps({
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "server"],
        })
        result = mcp_transport_tool(action="create", config_json=config)
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["config"]["transport_type"] == "stdio"
        assert data["data"]["config"]["command"] == "npx"

    def test_create_http_transport(self):
        config = json.dumps({
            "type": "http",
            "url": "https://example.com/mcp",
        })
        result = mcp_transport_tool(action="create", config_json=config)
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["config"]["transport_type"] == "http"
        assert data["data"]["config"]["url"] == "https://example.com/mcp"

    def test_invalid_action(self):
        result = mcp_transport_tool(action="invalid")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "INVALID_ACTION"

    def test_invalid_json_config(self):
        result = mcp_transport_tool(action="create", config_json="not json")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "INVALID_JSON"


class TestTransportFactory:
    def test_create_stdio_transport(self):
        config = TransportConfig(transport_type=TransportType.STDIO, command="npx")
        transport = TransportFactory.create(config)
        assert transport is not None

    def test_create_http_transport(self):
        config = TransportConfig(transport_type=TransportType.HTTP, url="https://example.com")
        transport = TransportFactory.create(config)
        assert transport is not None

    def test_from_dict(self):
        data = {"type": "stdio", "command": "node", "args": ["server.js"]}
        transport = TransportFactory.from_dict(data)
        assert transport is not None


class TestMcpConnectionTool:
    def test_list_connections_empty(self):
        result = mcp_connection_tool(action="list")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["count"] == 0

    def test_create_connection(self):
        config = json.dumps({
            "type": "stdio",
            "command": "npx",
        })
        result = mcp_connection_tool(action="create", name="test_server", config_json=config)
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["name"] == "test_server"
        assert data["data"]["status"] == "idle"

    def test_get_connection(self):
        config = json.dumps({"type": "stdio", "command": "npx"})
        mcp_connection_tool(action="create", name="get_test", config_json=config)

        result = mcp_connection_tool(action="get", name="get_test")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["name"] == "get_test"

    def test_get_connection_not_found(self):
        result = mcp_connection_tool(action="get", name="nonexistent")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "NOT_FOUND"

    def test_remove_connection(self):
        config = json.dumps({"type": "stdio", "command": "npx"})
        mcp_connection_tool(action="create", name="remove_test", config_json=config)

        result = mcp_connection_tool(action="remove", name="remove_test")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["removed"] is True

    def test_stats(self):
        result = mcp_connection_tool(action="stats")
        data = json.loads(result)
        assert data["success"] is True
        assert "total_connections" in data["data"]

    def test_create_missing_name(self):
        result = mcp_connection_tool(action="create", name="")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "MISSING_NAME"


class TestConnectionManager:
    def test_create_connection(self):
        manager = ConnectionManager()
        config = ConnectionConfig(name="server1", transport_type="stdio", command="node")
        conn = manager.create_connection(config)
        assert conn is not None
        assert conn.config.name == "server1"

    def test_get_connection(self):
        manager = ConnectionManager()
        config = ConnectionConfig(name="server2", transport_type="stdio", command="node")
        manager.create_connection(config)
        conn = manager.get_connection("server2")
        assert conn is not None
        assert conn.config.name == "server2"

    def test_get_connection_not_found(self):
        manager = ConnectionManager()
        conn = manager.get_connection("nonexistent")
        assert conn is None

    def test_list_connections(self):
        manager = ConnectionManager()
        manager.create_connection(ConnectionConfig(name="s1", transport_type="stdio", command="node"))
        manager.create_connection(ConnectionConfig(name="s2", transport_type="http", url="http://x.com"))
        connections = manager.list_connections()
        assert len(connections) == 2

    def test_remove_connection(self):
        manager = ConnectionManager()
        config = ConnectionConfig(name="to_remove", transport_type="stdio", command="node")
        manager.create_connection(config)
        removed = manager.remove_connection("to_remove")
        assert removed is True
        assert manager.get_connection("to_remove") is None

    def test_remove_nonexistent(self):
        manager = ConnectionManager()
        removed = manager.remove_connection("nonexistent")
        assert removed is False


class TestMcpHealthTool:
    def test_summary_empty(self):
        result = mcp_health_tool(action="summary")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["total_servers"] == 0

    def test_register_server(self):
        result = mcp_health_tool(action="register", server_name="healthy_server")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["server_name"] == "healthy_server"

    def test_status_unknown_server(self):
        result = mcp_health_tool(action="status", server_name="nonexistent")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["level"] == "unknown"

    def test_record_request(self):
        mcp_health_tool(action="register", server_name="record_test")
        result = mcp_health_tool(
            action="record",
            server_name="record_test",
            config_json=json.dumps({"latency_ms": 50.0, "error": False})
        )
        data = json.loads(result)
        assert data["success"] is True

    def test_history(self):
        mcp_health_tool(action="register", server_name="history_test")
        mcp_health_tool(action="record", server_name="history_test", config_json=json.dumps({"latency_ms": 100.0}))
        result = mcp_health_tool(action="history", server_name="history_test")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["server_name"] == "history_test"

    def test_unregister(self):
        mcp_health_tool(action="register", server_name="to_unregister")
        result = mcp_health_tool(action="unregister", server_name="to_unregister")
        data = json.loads(result)
        assert data["success"] is True

    def test_missing_server_name(self):
        result = mcp_health_tool(action="status", server_name="")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == "MISSING_SERVER_NAME"


class TestHealthMonitor:
    def test_register_server(self):
        monitor = HealthMonitor()
        monitor.register_server("test_server")
        threshold = HealthThreshold(min_requests_for_threshold=1)
        monitor.register_server("test_server2", threshold)
        monitor.record_request("test_server2", latency_ms=10.0, error=False)
        health = monitor.get_health("test_server2")
        assert health is not None
        assert health.level == HealthLevel.HEALTHY

    def test_record_request_success(self):
        monitor = HealthMonitor()
        monitor.register_server("req_test")
        monitor.record_request("req_test", latency_ms=50.0, error=False)
        health = monitor.get_health("req_test")
        assert health.total_requests == 1
        assert health.error_count == 0

    def test_record_request_error(self):
        monitor = HealthMonitor()
        monitor.register_server("err_test")
        monitor.record_request("err_test", latency_ms=100.0, error=True)
        health = monitor.get_health("err_test")
        assert health.total_requests == 1
        assert health.error_count == 1
        assert health.error_rate == 1.0

    def test_error_rate_threshold(self):
        monitor = HealthMonitor()
        threshold = HealthThreshold(error_rate=0.1, min_requests_for_threshold=5)
        monitor.register_server("threshold_test", threshold)

        for _ in range(9):
            monitor.record_request("threshold_test", error=False)
        monitor.record_request("threshold_test", error=True)

        health = monitor.get_health("threshold_test")
        assert health.error_rate >= 0.1

    def test_get_summary(self):
        monitor = HealthMonitor()
        monitor.register_server("sum1")
        monitor.register_server("sum2")
        monitor.record_request("sum1", latency_ms=10.0)
        monitor.record_request("sum2", latency_ms=20.0)
        summary = monitor.get_summary()
        assert summary["total_servers"] == 2
        assert len(summary["servers"]) == 2

    def test_unregister_server(self):
        monitor = HealthMonitor()
        monitor.register_server("unreg_test")
        monitor.unregister_server("unreg_test")
        health = monitor.get_health("unreg_test")
        assert health is None


class TestConnectionConfig:
    def test_default_config(self):
        config = ConnectionConfig(name="test")
        assert config.name == "test"
        assert config.transport_type == "stdio"
        assert config.timeout == 120
        assert config.max_retries == 5

    def test_custom_config(self):
        config = ConnectionConfig(
            name="custom",
            transport_type="http",
            url="https://example.com",
            timeout=300,
        )
        assert config.name == "custom"
        assert config.url == "https://example.com"
        assert config.timeout == 300


class TestHealthThreshold:
    def test_default_threshold(self):
        threshold = HealthThreshold()
        assert threshold.latency_ms == 1000.0
        assert threshold.error_rate == 0.05
        assert threshold.availability == 95.0

    def test_custom_threshold(self):
        threshold = HealthThreshold(
            latency_ms=500.0,
            error_rate=0.02,
            availability=99.0,
        )
        assert threshold.latency_ms == 500.0
        assert threshold.error_rate == 0.02
        assert threshold.availability == 99.0
