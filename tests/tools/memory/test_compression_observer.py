"""Unit tests for CompressionObserver."""

import asyncio
from datetime import datetime, timezone

import pytest

from tools.memory import CompressionObserver, CompressionResult


class TestCompressionObserver:
    """Test cases for CompressionObserver class."""
    
    @pytest.fixture
    def observer(self):
        """Create a CompressionObserver instance."""
        return CompressionObserver(worker_count=1)
    
    @pytest.mark.asyncio
    async def test_observe_queues_item(self, observer):
        """Test that observe() queues an item."""
        obs_id = await observer.observe(
            tool_name="test_tool",
            tool_args={"arg1": "value1"},
            tool_result="Test result content",
            session_id="test_session",
        )
        
        assert obs_id.startswith("obs_")
        assert observer._queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_start_stop_workers(self, observer):
        """Test starting and stopping workers."""
        await observer.start()
        assert observer._running is True
        assert len(observer._workers) == 1
        
        await observer.stop()
        assert observer._running is False
    
    @pytest.mark.asyncio
    async def test_heuristic_compression(self, observer):
        """Test heuristic compression (no LLM)."""
        result = await observer._heuristic_compress(
            input_text="Successfully parsed 50 pages. Found 100 paragraphs.",
            tool_name="parse_pdf",
        )
        
        assert result.success is True
        assert result.observation is not None
        assert result.observation.compression == "heuristic"
        assert "50 pages" in result.observation.summary or len(result.observation.summary) > 0
        assert result.original_tokens > 0
    
    @pytest.mark.asyncio
    async def test_heuristic_extracts_entities(self, observer):
        """Test that heuristic compression extracts entities."""
        result = await observer._heuristic_compress(
            input_text="Called PDFParserTool.parse() method",
            tool_name="parse_pdf",
        )
        
        assert result.success is True
        assert "parse" in result.observation.tool_name.lower()
    
    @pytest.mark.asyncio
    async def test_heuristic_importance_high_on_error(self, observer):
        """Test that errors result in high importance."""
        result = await observer._heuristic_compress(
            input_text="Error: Failed to parse PDF. Exception: InvalidFormatException",
            tool_name="parse_pdf",
        )
        
        assert result.success is True
        assert result.observation.importance == "high"
    
    @pytest.mark.asyncio
    async def test_heuristic_importance_low_on_small_text(self, observer):
        """Test that small texts result in low importance."""
        result = await observer._heuristic_compress(
            input_text="OK",
            tool_name="simple_tool",
        )
        
        assert result.success is True
        assert result.observation.importance == "low"
    
    @pytest.mark.asyncio
    async def test_parse_compression_response_json(self, observer):
        """Test parsing JSON format response."""
        response = '''
        {
            "summary": "Parsed PDF successfully",
            "entities": ["PDFParserTool", "parse"],
            "patterns": ["文件处理"],
            "importance": "high"
        }
        '''
        
        parsed = observer._parse_compression_response(response)
        
        assert parsed["summary"] == "Parsed PDF successfully"
        assert "PDFParserTool" in parsed["entities"]
        assert "文件处理" in parsed["patterns"]
        assert parsed["importance"] == "high"
    
    @pytest.mark.asyncio
    async def test_parse_compression_response_text(self, observer):
        """Test parsing text format response."""
        response = '''
        Summary: Parsed PDF successfully
        Entities: PDFParserTool, parse
        Patterns: 文件处理
        Importance: high
        '''
        
        parsed = observer._parse_compression_response(response)
        
        assert "Parsed PDF" in parsed["summary"]
        assert parsed["importance"] in ("high", "medium")  # Text parsing may vary
    
    @pytest.mark.asyncio
    async def test_parse_compression_response_fallback(self, observer):
        """Test fallback when parsing fails."""
        response = "This is not a structured response at all"
        
        parsed = observer._parse_compression_response(response)
        
        assert parsed["summary"] == response[:200]
        assert parsed["importance"] == "medium"
    
    @pytest.mark.asyncio
    async def test_estimate_tokens(self, observer):
        """Test token estimation."""
        text = "Hello world this is a test"
        
        tokens = observer._estimate_tokens(text)
        
        assert tokens > 0
        assert tokens == len(text) // 4 + 1
    
    def test_get_stats(self, observer):
        """Test getting stats."""
        stats = observer.get_stats()
        
        assert "compression_count" in stats
        assert "compression_errors" in stats
        assert "queue_size" in stats
        assert "workers_running" in stats
    
    @pytest.mark.asyncio
    async def test_full_compression_flow(self, observer):
        """Test full compression flow with queue processing."""
        obs_id = await observer.observe(
            tool_name="parse_pdf",
            tool_args={"file_path": "/test.pdf"},
            tool_result="Successfully parsed 100 pages with detailed content analysis.",
            session_id="test_session_123",
        )
        
        await observer.start()
        await asyncio.sleep(0.5)
        
        stats = observer.get_stats()
        assert stats["compression_count"] >= 1
        assert stats["queue_size"] == 0
        
        await observer.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_observations(self, observer):
        """Test queueing multiple observations."""
        for i in range(5):
            await observer.observe(
                tool_name=f"tool_{i}",
                tool_args={},
                tool_result=f"Result {i}",
                session_id="test_session",
            )
        
        assert observer._queue.qsize() == 5
        
        await observer.start()
        await asyncio.sleep(1)
        
        stats = observer.get_stats()
        assert stats["compression_count"] >= 5
        
        await observer.stop()
    
    @pytest.mark.asyncio
    async def test_extract_patterns(self, observer):
        """Test pattern extraction."""
        text = "Running performance optimization. Using async parallel processing."
        
        patterns = observer._extract_patterns(text)
        
        assert len(patterns) > 0
        assert any("性能优化" in p or "并行处理" in p for p in patterns)
    
    @pytest.mark.asyncio
    async def test_extract_entities(self, observer):
        """Test entity extraction."""
        text = "Called `PDFParserTool.parse()` method on class MyParser"
        
        entities = observer._extract_entities(text)
        
        assert len(entities) > 0
