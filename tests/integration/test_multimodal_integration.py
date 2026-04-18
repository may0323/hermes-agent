#!/usr/bin/env python3
"""Integration tests for Hermes Multimodal Agent modules - basic smoke tests."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Import all tool modules to trigger registration
import tools.pdf_parser_tool
import tools.docx_parser_tool
import tools.spreadsheet_parser_tool
import tools.ocr_tool
import tools.image_batch_analyze
import tools.image_compare
import tools.video_frame_extractor
import tools.video_analyzer
import tools.audio_processing
import tools.auto_memory_tool
import tools.parallel_executor_tool
import tools.skills_hub_tool
import tools.mcp_transport
import tools.mcp_connection
import tools.mcp_health


class TestToolRegistration:
    """Test that all tools are properly registered."""

    def test_all_modules_importable(self):
        """All tool modules should be importable."""
        # All imports succeeded at module level
        assert True

    def test_all_tools_registered(self):
        """All tools should be registered in the registry."""
        from tools.registry import registry
        
        expected_tools = {
            # Document
            "parse_pdf", "get_pdf_info",
            "parse_docx", "get_docx_info",
            "parse_spreadsheet", "get_spreadsheet_info",
            # Image
            "ocr_image", "ocr_pdf", "get_ocr_languages",
            "batch_analyze_images", "batch_analyze_directory",
            "compare_images", "find_similar_images",
            # Video
            "extract_video_frame", "extract_multiple_video_frames",
            "get_video_info", "analyze_video",
            "generate_video_thumbnail", "extract_video_audio",
            # Voice
            "get_audio_info", "convert_audio",
            "trim_audio", "adjust_audio_volume",
            # Memory
            "auto_summarize", "extract_entities",
            "detect_patterns", "memory_search",
            # Subagents
            "execute_parallel", "aggregate_results", "delegate_task",
            # Skills
            "list_skills", "search_skills",
            "get_skill_details", "check_skill_compatibility",
            # MCP
            "mcp_transport", "mcp_connection", "mcp_health",
        }
        
        all_tools = set(registry.get_all_tool_names())
        missing = expected_tools - all_tools
        if missing:
            pytest.fail(f"Missing tools: {missing}")

    def test_all_toolsets_exist(self):
        """All expected toolsets should exist."""
        from tools.registry import registry
        
        expected_toolsets = {
            "document", "image", "video", "voice",
            "memory", "subagents", "skills", "mcp"
        }
        
        all_toolsets = set(registry.get_registered_toolset_names())
        missing = expected_toolsets - all_toolsets
        if missing:
            pytest.fail(f"Missing toolsets: {missing}")

    def test_tools_per_toolset(self):
        """Each toolset should have the correct number of tools."""
        from tools.registry import registry
        
        expected_counts = {
            "document": 6,
            "image": 7,
            "video": 6,
            "voice": 4,
            "memory": 4,
            "subagents": 3,
            "skills": 4,
            "mcp": 3,
        }
        
        for toolset, expected_count in expected_counts.items():
            tools = registry.get_tool_names_for_toolset(toolset)
            if len(tools) != expected_count:
                pytest.fail(f"Toolset {toolset} has {len(tools)} tools, expected {expected_count}")


class TestSkillsHubFunctionality:
    """Test Skills Hub functionality."""

    def test_list_skills(self):
        """list_skills should return all skills."""
        from tools.skills_hub_tool import list_skills_tool
        
        result = list_skills_tool()
        data = json.loads(result)
        assert data["success"] is True
        assert "skills" in data["data"]
        assert "categories" in data["data"]

    def test_list_skills_by_category(self):
        """list_skills with category filter should work."""
        from tools.skills_hub_tool import list_skills_tool
        
        result = list_skills_tool(category="coding")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["category"] == "coding"

    def test_search_skills(self):
        """search_skills should find matching skills."""
        from tools.skills_hub_tool import search_skills_tool
        
        result = search_skills_tool(query="code")
        data = json.loads(result)
        assert data["success"] is True
        assert "matches" in data["data"]

    def test_get_skill_details(self):
        """get_skill_details should work for known skills."""
        from tools.skills_hub_tool import get_skill_details_tool
        
        result = get_skill_details_tool(skill_name="code_analysis")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["name"] == "code_analysis"

    def test_check_skill_compatibility(self):
        """check_skill_compatibility should work."""
        from tools.skills_hub_tool import check_skill_compatibility_tool
        
        result = check_skill_compatibility_tool(
            skill_name="code_analysis",
            context="analyzing code patterns"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert "compatibility_score" in data["data"]


class TestMCPFunctionality:
    """Test MCP tools functionality."""

    def test_mcp_transport_list(self):
        """mcp_transport list should work."""
        from tools.mcp_transport import mcp_transport_tool
        
        result = mcp_transport_tool(action="list")
        data = json.loads(result)
        assert data["success"] is True
        assert "transport_types" in data["data"]

    def test_mcp_connection_list(self):
        """mcp_connection list should work."""
        from tools.mcp_connection import mcp_connection_tool
        
        result = mcp_connection_tool(action="list")
        data = json.loads(result)
        assert data["success"] is True
        assert "connections" in data["data"]

    def test_mcp_connection_create(self):
        """mcp_connection create should work."""
        from tools.mcp_connection import mcp_connection_tool
        
        result = mcp_connection_tool(
            action="create",
            name="test_conn",
            config_json='{"type": "stdio", "command": "node"}'
        )
        data = json.loads(result)
        assert data["success"] is True

    def test_mcp_health_summary(self):
        """mcp_health summary should work."""
        from tools.mcp_health import mcp_health_tool
        
        result = mcp_health_tool(action="summary")
        data = json.loads(result)
        assert data["success"] is True

    def test_mcp_health_register(self):
        """mcp_health register should work."""
        from tools.mcp_health import mcp_health_tool
        
        result = mcp_health_tool(action="register", server_name="test_server")
        data = json.loads(result)
        assert data["success"] is True


class TestSubagentFunctionality:
    """Test subagent tools functionality."""

    def test_execute_parallel_rejects_empty(self):
        """execute_parallel should reject empty tasks."""
        from tools.parallel_executor_tool import execute_parallel_tool
        
        result = execute_parallel_tool(tasks=[])
        data = json.loads(result)
        assert data["success"] is False

    def test_aggregate_results_rejects_empty(self):
        """aggregate_results should reject empty results."""
        from tools.parallel_executor_tool import aggregate_results_tool
        
        result = aggregate_results_tool(results=[])
        data = json.loads(result)
        assert data["success"] is False

    def test_delegate_task_validation(self):
        """delegate_task should validate empty description."""
        from tools.parallel_executor_tool import delegate_task_tool
        
        result = delegate_task_tool(task_description="", agent_type="general")
        data = json.loads(result)
        assert data["success"] is False


class TestMemoryFunctionality:
    """Test memory tools functionality."""

    def test_auto_summarize(self):
        """auto_summarize should work."""
        from tools.auto_memory_tool import auto_summarize_tool
        
        result = auto_summarize_tool(context="This is a test. " * 10)
        data = json.loads(result)
        assert data["success"] is True


class TestDocumentToolsetIntegration:
    """Test document toolset integration."""

    def test_document_tools_in_registry(self):
        """Document tools should be in document toolset."""
        from tools.registry import registry
        tools = registry.get_tool_names_for_toolset("document")
        assert len(tools) == 6
        assert "parse_pdf" in tools
        assert "get_pdf_info" in tools
        assert "parse_docx" in tools
        assert "parse_spreadsheet" in tools


class TestImageToolsetIntegration:
    """Test image toolset integration."""

    def test_image_tools_in_registry(self):
        """Image tools should be in image toolset."""
        from tools.registry import registry
        tools = registry.get_tool_names_for_toolset("image")
        assert len(tools) == 7
        assert "ocr_image" in tools
        assert "batch_analyze_images" in tools


class TestVideoToolsetIntegration:
    """Test video toolset integration."""

    def test_video_tools_in_registry(self):
        """Video tools should be in video toolset."""
        from tools.registry import registry
        tools = registry.get_tool_names_for_toolset("video")
        assert len(tools) == 6
        assert "extract_video_frame" in tools
        assert "get_video_info" in tools


class TestVoiceToolsetIntegration:
    """Test voice toolset integration."""

    def test_voice_tools_in_registry(self):
        """Voice tools should be in voice toolset."""
        from tools.registry import registry
        tools = registry.get_tool_names_for_toolset("voice")
        assert len(tools) == 4
        assert "get_audio_info" in tools
        assert "convert_audio" in tools


class TestMemoryToolsetIntegration:
    """Test memory toolset integration."""

    def test_memory_tools_in_registry(self):
        """Memory tools should be in memory toolset."""
        from tools.registry import registry
        tools = registry.get_tool_names_for_toolset("memory")
        assert len(tools) == 4
        assert "auto_summarize" in tools
        assert "memory_search" in tools


class TestSubagentsToolsetIntegration:
    """Test subagents toolset integration."""

    def test_subagent_tools_in_registry(self):
        """Subagent tools should be in subagents toolset."""
        from tools.registry import registry
        tools = registry.get_tool_names_for_toolset("subagents")
        assert len(tools) == 3
        assert "execute_parallel" in tools
        assert "delegate_task" in tools


class TestSkillsToolsetIntegration:
    """Test skills toolset integration."""

    def test_skills_tools_in_registry(self):
        """Skills tools should be in skills toolset."""
        from tools.registry import registry
        tools = registry.get_tool_names_for_toolset("skills")
        assert len(tools) == 4
        assert "list_skills" in tools
        assert "search_skills" in tools


class TestMCPToolsetIntegration:
    """Test MCP toolset integration."""

    def test_mcp_tools_in_registry(self):
        """MCP tools should be in mcp toolset."""
        from tools.registry import registry
        tools = registry.get_tool_names_for_toolset("mcp")
        assert len(tools) == 3
        assert "mcp_transport" in tools
        assert "mcp_connection" in tools
        assert "mcp_health" in tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
