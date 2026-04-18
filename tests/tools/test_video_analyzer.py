#!/usr/bin/env python3
"""
Tests for Video Analyzer Tool

Covers:
- Video analysis
- Thumbnail generation
- Audio extraction
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestFileValidation:
    """Test file validation."""
    
    def test_check_file_size_valid(self, tmp_path):
        """Test valid file passes."""
        from tools.video_analyzer import _check_file_size
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video content" * 100)
        
        is_valid, error = _check_file_size(str(test_file))
        assert is_valid is True
    
    def test_check_file_size_nonexistent(self):
        """Test nonexistent file fails."""
        from tools.video_analyzer import _check_file_size
        is_valid, error = _check_file_size("/nonexistent/video.mp4")
        assert is_valid is False
        assert "not found" in error.lower()


class TestAnalyzeVideo:
    """Test video analysis."""
    
    def test_analyze_video_invalid_file(self):
        """Test error with invalid file."""
        from tools.video_analyzer import analyze_video_tool
        
        result = json.loads(analyze_video_tool("/nonexistent/video.mp4"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE"
    
    def test_analyze_video_with_metadata(self, tmp_path):
        """Test video analysis with metadata."""
        from tools.video_analyzer import analyze_video_tool
        
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video content")
        
        mock_metadata = {
            "format": {
                "duration": "120.5",
                "size": "1048576",
                "format_name": "mov,mp4"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                    "bit_rate": "5000000",
                    "pix_fmt": "yuv420p"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                    "bit_rate": "128000"
                }
            ]
        }
        
        with patch("tools.video_analyzer._get_video_metadata", return_value=mock_metadata):
            result = json.loads(analyze_video_tool(str(test_file)))
        
        assert result["success"] is True
        assert result["data"]["summary"]["duration_seconds"] == 120.5
        assert result["data"]["video"]["resolution"] == "1920x1080"


class TestThumbnailGeneration:
    """Test thumbnail generation."""
    
    def test_thumbnail_ffmpeg_not_available(self, tmp_path):
        """Test error when FFmpeg not available."""
        from tools.video_analyzer import generate_video_thumbnail_tool
        
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")
        
        with patch("tools.video_analyzer.check_ffmpeg_available", return_value=False):
            result = json.loads(generate_video_thumbnail_tool(str(test_file)))
        
        assert result["success"] is False
        assert result["error_code"] == "FFMPEG_NOT_AVAILABLE"


class TestAudioExtraction:
    """Test audio extraction."""
    
    def test_audio_extraction_invalid_file(self):
        """Test error with invalid file."""
        from tools.video_analyzer import extract_video_audio_tool
        
        with patch("tools.video_analyzer.check_ffmpeg_available", return_value=True):
            result = json.loads(extract_video_audio_tool("/nonexistent/video.mp4"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE"
    
    def test_audio_extraction_ffmpeg_not_available(self, tmp_path):
        """Test error when FFmpeg not available."""
        from tools.video_analyzer import extract_video_audio_tool
        
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")
        
        with patch("tools.video_analyzer.check_ffmpeg_available", return_value=False):
            result = json.loads(extract_video_audio_tool(str(test_file)))
        
        assert result["success"] is False
        assert result["error_code"] == "FFMPEG_NOT_AVAILABLE"


class TestVideoAnalyzerRegistry:
    """Test tool registration."""
    
    def test_analyze_video_registered(self):
        """Test analyze_video is registered."""
        import tools.video_analyzer
        from tools import registry
        entry = registry.registry.get_entry("analyze_video")
        assert entry is not None
        assert entry.toolset == "video"
    
    def test_generate_thumbnail_registered(self):
        """Test generate_video_thumbnail is registered."""
        import tools.video_analyzer
        from tools import registry
        entry = registry.registry.get_entry("generate_video_thumbnail")
        assert entry is not None
        assert entry.toolset == "video"
    
    def test_extract_audio_registered(self):
        """Test extract_video_audio is registered."""
        import tools.video_analyzer
        from tools import registry
        entry = registry.registry.get_entry("extract_video_audio")
        assert entry is not None
        assert entry.toolset == "video"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])