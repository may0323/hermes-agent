#!/usr/bin/env python3
"""
Tests for Auto Memory Tool

Covers:
- Context summarization
- Entity extraction
- Pattern detection
- Memory search
"""

import json

import pytest


class TestAutoSummarize:
    """Test auto summarize functionality."""
    
    def test_summarize_empty_context(self):
        """Test error with empty context."""
        from tools.auto_memory_tool import auto_summarize_tool
        result = json.loads(auto_summarize_tool(""))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_CONTEXT"
    
    def test_summarize_with_decisions(self):
        """Test summarizing context with decisions."""
        from tools.auto_memory_tool import auto_summarize_tool
        
        context = """
We agreed to use Python for the backend.
The team will implement the API first.
Should we add authentication? Yes, we decided to add JWT.
The deadline is next Friday.
        """
        
        result = json.loads(auto_summarize_tool(context))
        
        assert result["success"] is True
        assert "summary" in result["data"]
        assert result["data"]["decisions_count"] >= 1
    
    def test_summarize_with_questions(self):
        """Test summarizing context with questions."""
        from tools.auto_memory_tool import auto_summarize_tool
        
        context = """
What programming language should we use?
How will we handle authentication?
When is the deadline?
Let's use Python.
        """
        
        result = json.loads(auto_summarize_tool(context))
        
        assert result["success"] is True
        assert "summary" in result["data"]
    
    def test_summarize_respects_max_length(self):
        """Test that max_length is respected."""
        from tools.auto_memory_tool import auto_summarize_tool
        
        context = "This is a long context. " * 100
        
        result = json.loads(auto_summarize_tool(context, max_length=100))
        
        assert result["success"] is True
        assert result["data"]["summary_length"] <= 150


class TestExtractEntities:
    """Test entity extraction."""
    
    def test_extract_empty_context(self):
        """Test error with empty context."""
        from tools.auto_memory_tool import extract_entities_tool
        result = json.loads(extract_entities_tool(""))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_CONTEXT"
    
    def test_extract_mentioned_files(self):
        """Test extracting mentioned files."""
        from tools.auto_memory_tool import extract_entities_tool
        
        context = """
I edited the config.py file and main.py.
The tests are in test_main.py.
Don't forget to update README.md.
        """
        
        result = json.loads(extract_entities_tool(context))
        
        assert result["success"] is True
        assert "mentioned_files" in result["data"]
        assert ".py" in str(result["data"]["mentioned_files"]) or "config.py" in str(result["data"]["mentioned_files"])


class TestDetectPatterns:
    """Test pattern detection."""
    
    def test_detect_empty_context(self):
        """Test error with empty context."""
        from tools.auto_memory_tool import detect_patterns_tool
        result = json.loads(detect_patterns_tool(""))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_CONTEXT"
    
    def test_detect_questions(self):
        """Test detecting questions."""
        from tools.auto_memory_tool import detect_patterns_tool
        
        context = """
What is the plan?
How should we proceed?
The answer is yes.
        """
        
        result = json.loads(detect_patterns_tool(context))
        
        assert result["success"] is True
        assert result["data"]["summary"]["total_questions"] == 2
    
    def test_detect_decisions(self):
        """Test detecting decisions."""
        from tools.auto_memory_tool import detect_patterns_tool
        
        context = """
We agreed to use Python.
The team will implement the API.
Must finish by Friday.
        """
        
        result = json.loads(detect_patterns_tool(context))
        
        assert result["success"] is True
        assert result["data"]["summary"]["total_decisions"] >= 1


class TestMemorySearch:
    """Test memory search functionality."""
    
    def test_search_empty_query(self):
        """Test error with empty query."""
        from tools.auto_memory_tool import memory_search_tool
        result = json.loads(memory_search_tool("", "some context"))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_QUERY"
    
    def test_search_empty_context(self):
        """Test error with empty context."""
        from tools.auto_memory_tool import memory_search_tool
        result = json.loads(memory_search_tool("query", ""))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_CONTEXT"
    
    def test_search_finds_matches(self):
        """Test that search finds matching content."""
        from tools.auto_memory_tool import memory_search_tool
        
        context = """
Line 1: We use Python for backend.
Line 2: JavaScript is for frontend.
Line 3: Python has great libraries.
        """
        
        result = json.loads(memory_search_tool("Python", context))
        
        assert result["success"] is True
        assert result["data"]["total_matches"] >= 2
    
    def test_search_ranked_results(self):
        """Test that results are ranked by relevance."""
        from tools.auto_memory_tool import memory_search_tool
        
        context = """
Python is amazing. Python Python Python.
JavaScript is also popular.
        """
        
        result = json.loads(memory_search_tool("Python", context))
        
        assert result["success"] is True
        results = result["data"]["results"]
        if len(results) > 1:
            assert results[0]["score"] >= results[1]["score"]


class TestAutoMemoryRegistry:
    """Test tool registration."""
    
    def test_auto_summarize_registered(self):
        """Test auto_summarize is registered."""
        import tools.auto_memory_tool
        from tools import registry
        entry = registry.registry.get_entry("auto_summarize")
        assert entry is not None
        assert entry.toolset == "memory"
    
    def test_extract_entities_registered(self):
        """Test extract_entities is registered."""
        import tools.auto_memory_tool
        from tools import registry
        entry = registry.registry.get_entry("extract_entities")
        assert entry is not None
        assert entry.toolset == "memory"
    
    def test_detect_patterns_registered(self):
        """Test detect_patterns is registered."""
        import tools.auto_memory_tool
        from tools import registry
        entry = registry.registry.get_entry("detect_patterns")
        assert entry is not None
        assert entry.toolset == "memory"
    
    def test_memory_search_registered(self):
        """Test memory_search is registered."""
        import tools.auto_memory_tool
        from tools import registry
        entry = registry.registry.get_entry("memory_search")
        assert entry is not None
        assert entry.toolset == "memory"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])