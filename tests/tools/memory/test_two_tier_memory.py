"""Unit tests for TwoTierMemory."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tools.memory import CompressedObservation, TwoTierMemory


class TestTwoTierMemory:
    """Test cases for TwoTierMemory class."""
    
    @pytest.fixture
    def memory(self, tmp_path):
        """Create a TwoTierMemory instance with temp directory."""
        return TwoTierMemory(base_path=tmp_path)
    
    @pytest.fixture
    def sample_observation(self):
        """Create a sample observation."""
        return CompressedObservation(
            session_id="test_session_123",
            summary="测试：添加了 PDF 并行解析功能",
            entities=["PDFParserTool", "ThreadPoolExecutor"],
            patterns=["性能优化", "并行处理"],
            importance="high",
            original_tokens=5000,
            compressed_tokens=350,
            tool_name="parse_pdf",
        )
    
    @pytest.mark.asyncio
    async def test_store_working(self, memory, sample_observation):
        """Test storing observation in working memory."""
        obs_id = await memory.store_working(sample_observation)
        
        assert obs_id == sample_observation.id
        assert obs_id.startswith("obs_")
        
        working_file = memory._get_working_file()
        assert working_file.exists()
        
        with open(working_file, "r") as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["id"] == obs_id
        assert data[0]["summary"] == sample_observation.summary
    
    @pytest.mark.asyncio
    async def test_store_multiple_observations(self, memory):
        """Test storing multiple observations."""
        for i in range(5):
            obs = CompressedObservation(
                session_id=f"session_{i}",
                summary=f"观察 {i}",
                importance="medium",
                original_tokens=1000,
                compressed_tokens=100,
            )
            await memory.store_working(obs)
        
        working_file = memory._get_working_file()
        with open(working_file, "r") as f:
            data = json.load(f)
        
        assert len(data) == 5
    
    @pytest.mark.asyncio
    async def test_search_finds_matching_observation(self, memory, sample_observation):
        """Test search finds matching observation."""
        await memory.store_working(sample_observation)
        
        results = await memory.search("PDF")
        
        assert len(results) == 1
        assert results[0].id == sample_observation.id
        assert results[0].score > 0
    
    @pytest.mark.asyncio
    async def test_search_with_chinese(self, memory, sample_observation):
        """Test search with Chinese characters."""
        await memory.store_working(sample_observation)
        
        results = await memory.search("并行")
        
        assert len(results) >= 1
        assert any("并行" in r.preview for r in results)
    
    @pytest.mark.asyncio
    async def test_search_returns_multiple_results(self, memory):
        """Test search returns multiple results ordered by relevance."""
        observations = [
            CompressedObservation(
                session_id=f"session_{i}",
                summary=f"观察 {i}: PDF 解析",
                importance="medium",
                original_tokens=1000,
                compressed_tokens=100,
                tool_name="tool_a",
            )
            for i in range(3)
        ]
        
        for obs in observations:
            await memory.store_working(obs)
        
        results = await memory.search("PDF")
        
        assert len(results) == 3
        assert all(r.score > 0 for r in results)
    
    @pytest.mark.asyncio
    async def test_search_with_limit(self, memory):
        """Test search respects limit parameter."""
        for i in range(10):
            obs = CompressedObservation(
                session_id=f"session_{i}",
                summary=f"测试观察 {i}",
                importance="medium",
                original_tokens=1000,
                compressed_tokens=100,
            )
            await memory.store_working(obs)
        
        results = await memory.search("测试", limit=5)
        
        assert len(results) == 5
    
    @pytest.mark.asyncio
    async def test_search_importance_filter(self, memory):
        """Test search with importance filter."""
        high_obs = CompressedObservation(
            session_id="high_session",
            summary="重要观察",
            importance="high",
            original_tokens=1000,
            compressed_tokens=100,
        )
        low_obs = CompressedObservation(
            session_id="low_session",
            summary="一般观察",
            importance="low",
            original_tokens=1000,
            compressed_tokens=100,
        )
        
        await memory.store_working(high_obs)
        await memory.store_working(low_obs)
        
        results = await memory.search("观察", importance_filter=["high"])
        
        assert len(results) == 1
        assert results[0].importance == "high"
    
    @pytest.mark.asyncio
    async def test_get_timeline(self, memory, sample_observation):
        """Test getting timeline entries."""
        await memory.store_working(sample_observation)
        
        timeline = await memory.get_timeline([sample_observation.id])
        
        assert len(timeline) == 1
        assert timeline[0].id == sample_observation.id
        assert timeline[0].session_id == sample_observation.session_id
        assert "parse_pdf" in timeline[0].context
    
    @pytest.mark.asyncio
    async def test_get_observations(self, memory, sample_observation):
        """Test getting full observations."""
        await memory.store_working(sample_observation)
        
        observations = await memory.get_observations([sample_observation.id])
        
        assert len(observations) == 1
        assert observations[0].id == sample_observation.id
        assert observations[0].summary == sample_observation.summary
        assert observations[0].entities == sample_observation.entities
    
    @pytest.mark.asyncio
    async def test_get_stats(self, memory, sample_observation):
        """Test getting memory statistics."""
        await memory.store_working(sample_observation)
        
        stats = await memory.get_stats()
        
        assert stats.working_count == 1
        assert stats.working_tokens == sample_observation.compressed_tokens
        assert stats.compression_ratio == "14:1"
    
    @pytest.mark.asyncio
    async def test_get_stats_with_compression_ratio(self, memory):
        """Test stats show correct compression ratio."""
        obs = CompressedObservation(
            session_id="session_1",
            summary="Test",
            original_tokens=1000,
            compressed_tokens=100,
        )
        await memory.store_working(obs)
        
        stats = await memory.get_stats()
        
        assert stats.working_count == 1
        assert stats.compression_ratio == "10:1"
    
    @pytest.mark.asyncio
    async def test_store_archive(self, memory):
        """Test storing transcript in archive."""
        from tools.memory import Transcript
        
        transcript = Transcript(
            session_id="archive_test_123",
            start_time="2026-04-18T10:00:00Z",
            end_time="2026-04-18T10:30:00Z",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
            tool_calls=[
                {"name": "test_tool", "args": {}},
            ],
        )
        
        archive_path = await memory.store_archive(transcript.session_id, transcript)
        
        assert Path(archive_path).exists()
        
        with open(archive_path, "r") as f:
            data = json.load(f)
        
        assert data["session_id"] == transcript.session_id
        assert len(data["messages"]) == 2
    
    @pytest.mark.asyncio
    async def test_working_file_per_date(self, memory):
        """Test that observations are stored in date-specific files.
        
        Note: Observations created on the same day go to the same file.
        This test verifies that multiple observations share one file per day.
        """
        obs1 = CompressedObservation(
            session_id="session_1",
            summary="Today",
            original_tokens=100,
            compressed_tokens=10,
        )
        obs2 = CompressedObservation(
            session_id="session_2",
            summary="Same day",
            original_tokens=100,
            compressed_tokens=10,
        )
        
        await memory.store_working(obs1)
        await memory.store_working(obs2)
        
        working_files = list(memory.working_path.glob("*.json"))
        
        assert len(working_files) == 1
        assert working_files[0].name.startswith("2026-04-18")
        
        with open(working_files[0], "r") as f:
            data = json.load(f)
        
        assert len(data) == 2
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, memory):
        """Test loading from nonexistent file returns empty list."""
        observations = memory._load_working_file(
            memory.working_path / "nonexistent.json"
        )
        
        assert observations == []
    
    @pytest.mark.asyncio
    async def test_search_no_matches(self, memory):
        """Test search with no matches."""
        obs = CompressedObservation(
            session_id="session_1",
            summary="特定内容",
            original_tokens=100,
            compressed_tokens=10,
        )
        await memory.store_working(obs)
        
        results = await memory.search("完全不匹配的内容")
        
        assert len(results) == 0
