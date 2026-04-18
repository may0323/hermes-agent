#!/usr/bin/env python3
"""
Tests for Audio Processing Tool

Covers:
- Audio info retrieval
- Audio format conversion
- Audio trimming
- Volume adjustment
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
            from tools.audio_processing import check_ffmpeg_available
            result = check_ffmpeg_available()
            assert result is True
    
    def test_check_ffmpeg_not_available(self):
        """Test when FFmpeg is not available."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            from tools.audio_processing import check_ffmpeg_available
            result = check_ffmpeg_available()
            assert result is False


class TestFileValidation:
    """Test file validation."""
    
    def test_check_file_size_valid(self, tmp_path):
        """Test valid file passes."""
        from tools.audio_processing import _check_file_size
        test_file = tmp_path / "test.mp3"
        test_file.write_bytes(b"fake audio content" * 100)
        
        is_valid, error = _check_file_size(str(test_file))
        assert is_valid is True
    
    def test_check_file_size_nonexistent(self):
        """Test nonexistent file fails."""
        from tools.audio_processing import _check_file_size
        is_valid, error = _check_file_size("/nonexistent/audio.mp3")
        assert is_valid is False
        assert "not found" in error.lower()
    
    def test_unsupported_format(self, tmp_path):
        """Test unsupported format fails."""
        from tools.audio_processing import _check_file_size
        test_file = tmp_path / "test.xyz"
        test_file.write_bytes(b"content")
        
        is_valid, error = _check_file_size(str(test_file))
        assert is_valid is False
        assert "unsupported" in error.lower()


class TestGetAudioInfo:
    """Test audio info retrieval."""
    
    def test_get_audio_info_invalid_file(self):
        """Test error with invalid file."""
        from tools.audio_processing import get_audio_info_tool
        
        result = json.loads(get_audio_info_tool("/nonexistent/audio.mp3"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE"
    
    def test_get_audio_info_with_metadata(self, tmp_path):
        """Test audio info with metadata."""
        from tools.audio_processing import get_audio_info_tool
        
        test_file = tmp_path / "test.mp3"
        test_file.write_bytes(b"fake audio")
        
        mock_metadata = {
            "format": {
                "duration": "180.5",
                "format_name": "mp3",
                "bit_rate": "128000"
            },
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "mp3",
                    "sample_rate": "44100",
                    "channels": 2,
                    "bits_per_sample": 0
                }
            ]
        }
        
        with patch("tools.audio_processing._get_audio_metadata", return_value=mock_metadata):
            result = json.loads(get_audio_info_tool(str(test_file)))
        
        assert result["success"] is True
        assert result["data"]["duration"] == 180.5
        assert result["data"]["audio"]["sample_rate"] == 44100


class TestConvertAudio:
    """Test audio conversion."""
    
    def test_convert_audio_invalid_file(self):
        """Test error with invalid file."""
        from tools.audio_processing import convert_audio_tool
        
        with patch("tools.audio_processing.check_ffmpeg_available", return_value=True):
            result = json.loads(convert_audio_tool("/nonexistent/audio.mp3"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE"
    
    def test_convert_audio_ffmpeg_not_available(self, tmp_path):
        """Test error when FFmpeg not available."""
        from tools.audio_processing import convert_audio_tool
        
        test_file = tmp_path / "test.mp3"
        test_file.write_bytes(b"fake audio")
        
        with patch("tools.audio_processing.check_ffmpeg_available", return_value=False):
            result = json.loads(convert_audio_tool(str(test_file)))
        
        assert result["success"] is False
        assert result["error_code"] == "FFMPEG_NOT_AVAILABLE"
    
    def test_convert_audio_unsupported_format(self, tmp_path):
        """Test error with unsupported output format."""
        from tools.audio_processing import convert_audio_tool
        
        test_file = tmp_path / "test.mp3"
        test_file.write_bytes(b"fake audio")
        
        with patch("tools.audio_processing.check_ffmpeg_available", return_value=True):
            result = json.loads(convert_audio_tool(str(test_file), output_format="xyz"))
        
        assert result["success"] is False
        assert result["error_code"] == "UNSUPPORTED_FORMAT"


class TestTrimAudio:
    """Test audio trimming."""
    
    def test_trim_audio_invalid_file(self):
        """Test error with invalid file."""
        from tools.audio_processing import trim_audio_tool
        
        with patch("tools.audio_processing.check_ffmpeg_available", return_value=True):
            result = json.loads(trim_audio_tool("/nonexistent/audio.mp3"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE"


class TestAdjustVolume:
    """Test volume adjustment."""
    
    def test_adjust_volume_invalid_file(self):
        """Test error with invalid file."""
        from tools.audio_processing import adjust_audio_volume_tool
        
        with patch("tools.audio_processing.check_ffmpeg_available", return_value=True):
            result = json.loads(adjust_audio_volume_tool("/nonexistent/audio.mp3"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE"
    
    def test_adjust_volume_invalid_factor(self, tmp_path):
        """Test error with invalid volume factor."""
        from tools.audio_processing import adjust_audio_volume_tool
        
        test_file = tmp_path / "test.mp3"
        test_file.write_bytes(b"fake audio")
        
        with patch("tools.audio_processing.check_ffmpeg_available", return_value=True):
            result = json.loads(adjust_audio_volume_tool(str(test_file), volume_factor=15.0))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_PARAMETER"


class TestAudioProcessingRegistry:
    """Test tool registration."""
    
    def test_get_audio_info_registered(self):
        """Test get_audio_info is registered."""
        import tools.audio_processing
        from tools import registry
        entry = registry.registry.get_entry("get_audio_info")
        assert entry is not None
        assert entry.toolset == "voice"
    
    def test_convert_audio_registered(self):
        """Test convert_audio is registered."""
        import tools.audio_processing
        from tools import registry
        entry = registry.registry.get_entry("convert_audio")
        assert entry is not None
        assert entry.toolset == "voice"
    
    def test_trim_audio_registered(self):
        """Test trim_audio is registered."""
        import tools.audio_processing
        from tools import registry
        entry = registry.registry.get_entry("trim_audio")
        assert entry is not None
        assert entry.toolset == "voice"
    
    def test_adjust_volume_registered(self):
        """Test adjust_audio_volume is registered."""
        import tools.audio_processing
        from tools import registry
        entry = registry.registry.get_entry("adjust_audio_volume")
        assert entry is not None
        assert entry.toolset == "voice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])