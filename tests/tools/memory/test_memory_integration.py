"""Integration tests for Claude Memory System."""

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tools.memory import (
    ClaudeMDWriter,
    CompressedObservation,
    CompressionObserver,
    SessionSummary,
    TwoTierMemory,
)


class TestMemoryIntegration:
    """End-to-end integration tests for Claude Memory System."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def two_tier_memory(self, temp_dir):
        """Create a TwoTierMemory instance."""
        return TwoTierMemory(base_path=temp_dir)
    
    @pytest.fixture
    def compression_observer(self):
        """Create a CompressionObserver instance."""
        return CompressionObserver(worker_count=1)
    
    @pytest.fixture
    def claude_md_writer(self, temp_dir):
        """Create a ClaudeMDWriter instance."""
        writer = ClaudeMDWriter()
        writer.add_project_path(temp_dir)
        return writer
    
    @pytest.mark.asyncio
    async def test_full_memory_flow(self, two_tier_memory):
        """Test the full memory flow: compress -> store -> search -> retrieve."""
        
        obs = CompressedObservation(
            session_id="integration_test_session",
            summary="完成了 PDF 解析功能的开发",
            entities=["PDFParserTool", "parse_pdf"],
            patterns=["文件处理", "性能优化"],
            importance="high",
            original_tokens=5000,
            compressed_tokens=350,
            tool_name="parse_pdf",
        )
        
        obs_id = await two_tier_memory.store_working(obs)
        assert obs_id
        
        results = await two_tier_memory.search("PDF 解析")
        assert len(results) >= 1
        assert results[0].id == obs_id
        
        observations = await two_tier_memory.get_observations([obs_id])
        assert len(observations) == 1
        assert observations[0].summary == "完成了 PDF 解析功能的开发"
        
        stats = await two_tier_memory.get_stats()
        assert stats.working_count >= 1
    
    @pytest.mark.asyncio
    async def test_compression_to_memory_pipeline(self, two_tier_memory, compression_observer):
        """Test the compression -> memory pipeline."""
        
        await compression_observer.start()
        
        tool_result = """
        Successfully parsed PDF document with 100 pages.
        
        Page 1-10: Introduction and overview
        Page 11-50: Main content chapters
        Page 51-100: Appendices and references
        
        Statistics:
        - Total paragraphs: 1,234
        - Total images: 45
        - Total tables: 23
        - Extracted text: 45,678 words
        """
        
        obs_id = await compression_observer.observe(
            tool_name="parse_pdf",
            tool_args={"file_path": "/test.pdf"},
            tool_result=tool_result,
            session_id="compression_test_session",
        )
        
        await asyncio.sleep(1)
        
        stats = compression_observer.get_stats()
        assert stats["compression_count"] >= 1
        assert stats["compression_errors"] == 0
        
        await compression_observer.stop()
    
    @pytest.mark.asyncio
    async def test_claude_md_update_flow(self, claude_md_writer, temp_dir):
        """Test CLAUDE.md auto-update flow."""
        
        summary = SessionSummary(
            session_id="claude_md_test_session",
            date="2026-04-18T10:00:00Z",
            tools_used=["parse_pdf", "extract_text", "summarize"],
            files_modified=["docs/manual.pdf", "docs/guide.docx"],
            decisions=["使用并行处理提升性能", "采用流式API减少内存占用"],
            key_outcomes=["完成了文档解析功能", "性能提升3倍"],
            patterns=["文件处理", "性能优化", "并行处理"],
        )
        
        await claude_md_writer.learn_from_session(summary)
        
        content, exists = claude_md_writer.read_claude_md(temp_dir)
        assert exists
        assert len(content) > 0
        assert "parse_pdf" in content
        assert "2026-04-18" in content
    
    @pytest.mark.asyncio
    async def test_three_layer_search_flow(self, two_tier_memory):
        """Test the three-layer search: search -> timeline -> get."""
        
        observations = [
            CompressedObservation(
                session_id="session_1",
                summary="添加了 PDF 解析工具",
                entities=["PDFParserTool"],
                patterns=["文件处理"],
                importance="high",
                original_tokens=1000,
                compressed_tokens=100,
                tool_name="parse_pdf",
            ),
            CompressedObservation(
                session_id="session_2",
                summary="优化了图像分析性能",
                entities=["ImageAnalyzer"],
                patterns=["性能优化"],
                importance="medium",
                original_tokens=800,
                compressed_tokens=80,
                tool_name="analyze_image",
            ),
        ]
        
        obs_ids = []
        for obs in observations:
            obs_id = await two_tier_memory.store_working(obs)
            obs_ids.append(obs_id)
        
        layer1_results = await two_tier_memory.search("PDF 解析")
        assert len(layer1_results) >= 1
        
        layer2_timeline = await two_tier_memory.get_timeline([layer1_results[0].id])
        assert len(layer2_timeline) == 1
        
        layer3_observations = await two_tier_memory.get_observations([layer1_results[0].id])
        assert len(layer3_observations) == 1
        assert layer3_observations[0].summary == "添加了 PDF 解析工具"
    
    @pytest.mark.asyncio
    async def test_archive_full_transcript(self, two_tier_memory):
        """Test archiving full session transcript."""
        from tools.memory import Transcript
        
        transcript = Transcript(
            session_id="archive_test_session",
            start_time="2026-04-18T10:00:00Z",
            end_time="2026-04-18T10:30:00Z",
            messages=[
                {"role": "user", "content": "帮我解析这个 PDF"},
                {"role": "assistant", "content": "好的，我来解析"},
                {"role": "tool", "name": "parse_pdf", "content": "解析完成"},
            ],
            tool_calls=[
                {"name": "parse_pdf", "args": {"file": "test.pdf"}},
            ],
        )
        
        archive_path = await two_tier_memory.store_archive(
            transcript.session_id,
            transcript,
        )
        
        assert Path(archive_path).exists()
        
        stats = await two_tier_memory.get_stats()
        assert stats.archive_count >= 1
