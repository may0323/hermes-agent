#!/usr/bin/env python3
"""
Tests for Video Frame Extractor Tool

Covers:
- Frame extraction
- Multiple frame extraction
- Video info retrieval
- Error handling
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestFFmpegAvailability:
    """Test FFmpeg availability check."""
    
    def test_check_ffmpeg_available(self):
        """Test FFmpeg availability check."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            from tools.video_frame_extractor import check_ffmpeg_available
            result = check_ffmpeg_available()
            assert result is True
    
    def test_check_ffmpeg_not_available(self):
        """Test when FFmpeg is not available."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            from tools.video_frame_extractor import check_ffmpeg_available
            result = check_ffmpeg_available()
            assert result is False


class TestFileValidation:
    """Test file validation."""
    
    def test_check_file_size_valid(self, tmp_path):
        """Test valid file passes."""
        from tools.video_frame_extractor import _check_file_size
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video content" * 100)
        
        is_valid, error = _check_file_size(str(test_file))
        assert is_valid is True
    
    def test_check_file_size_nonexistent(self):
        """Test nonexistent file fails."""
        from tools.video_frame_extractor import _check_file_size
        is_valid, error = _check_file_size("/nonexistent/video.mp4")
        assert is_valid is False
        assert "not found" in error.lower()
    
    def test_unsupported_format(self, tmp_path):
        """Test unsupported format fails."""
        from tools.video_frame_extractor import _check_file_size
        test_file = tmp_path / "test.xyz"
        test_file.write_bytes(b"content")
        
        is_valid, error = _check_file_size(str(test_file))
        assert is_valid is False
        assert "unsupported" in error.lower()


class TestExtractFrame:
    """Test frame extraction."""
    
    def test_extract_frame_ffmpeg_not_available(self, tmp_path):
        """Test error when FFmpeg not available."""
        from tools.video_frame_extractor import extract_frame_tool
        
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")
        
        with patch("tools.video_frame_extractor.check_ffmpeg_available", return_value=False):
            result = json.loads(extract_frame_tool(str(test_file), 1.0))
        
        assert result["success"] is False
        assert result["error_code"] == "FFMPEG_NOT_AVAILABLE"
    
    def test_extract_frame_invalid_file(self):
        """Test error with invalid file."""
        from tools.video_frame_extractor import extract_frame_tool
        
        with patch("tools.video_frame_extractor.check_ffmpeg_available", return_value=True):
            result = json.loads(extract_frame_tool("/nonexistent/video.mp4"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE"


class TestMultipleFrames:
    """Test multiple frame extraction."""
    
    def test_extract_multiple_empty_timestamps(self, tmp_path):
        """Test error with empty timestamps."""
        from tools.video_frame_extractor import extract_multiple_frames_tool
        
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")
        
        with patch("tools.video_frame_extractor.check_ffmpeg_available", return_value=True):
            result = json.loads(extract_multiple_frames_tool(str(test_file), []))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_INPUT"
    
    def test_extract_multiple_too_many_frames(self, tmp_path):
        """Test error with too many frames."""
        from tools.video_frame_extractor import extract_multiple_frames_tool
        
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")
        
        timestamps = list(range(30))
        
        with patch("tools.video_frame_extractor.check_ffmpeg_available", return_value=True):
            result = json.loads(extract_multiple_frames_tool(str(test_file), timestamps))
        
        assert result["success"] is False
        assert result["error_code"] == "TOO_MANY_FRAMES"


class TestGetVideoInfo:
    """Test video info retrieval."""
    
    def test_get_video_info_invalid_file(self):
        """Test error with invalid file."""
        from tools.video_frame_extractor import get_video_info_tool
        
        result = json.loads(get_video_info_tool("/nonexistent/video.mp4"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE"


class TestVideoToolRegistry:
    """Test tool registration."""
    
    def test_extract_video_frame_registered(self):
        """Test extract_video_frame is registered."""
        import tools.video_frame_extractor
        from tools import registry
        entry = registry.registry.get_entry("extract_video_frame")
        assert entry is not None
        assert entry.toolset == "video"
    
    def test_extract_multiple_frames_registered(self):
        """Test extract_multiple_video_frames is registered."""
        import tools.video_frame_extractor
        from tools import registry
        entry = registry.registry.get_entry("extract_multiple_video_frames")
        assert entry is not None
        assert entry.toolset == "video"
    
    def test_get_video_info_registered(self):
        """Test get_video_info is registered."""
        import tools.video_frame_extractor
        from tools import registry
        entry = registry.registry.get_entry("get_video_info")
        assert entry is not None
        assert entry.toolset == "video"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])