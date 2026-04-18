#!/usr/bin/env python3
"""
Tests for Batch Image Analyze Tool

Covers:
- Batch image analysis
- Directory scanning
- Error handling
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestFileSizeValidation:
    """Test file size validation."""
    
    def test_check_file_size_valid(self, tmp_path):
        """Test valid file passes."""
        from tools.image_batch_analyze import _check_file_size
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake png" * 100)
        
        is_valid, error = _check_file_size(str(test_file))
        assert is_valid is True
    
    def test_check_file_size_nonexistent(self):
        """Test nonexistent file fails."""
        from tools.image_batch_analyze import _check_file_size
        is_valid, error = _check_file_size("/nonexistent/image.png")
        assert is_valid is False
        assert "not found" in error.lower()
    
    def test_unsupported_format(self, tmp_path):
        """Test unsupported format fails."""
        from tools.image_batch_analyze import _check_file_size
        test_file = tmp_path / "test.xyz"
        test_file.write_bytes(b"content")
        
        is_valid, error = _check_file_size(str(test_file))
        assert is_valid is False
        assert "unsupported" in error.lower()


class TestBatchAnalyzeImages:
    """Test batch image analysis."""
    
    def test_empty_input(self):
        """Test empty input returns error."""
        from tools.image_batch_analyze import batch_analyze_images
        result = json.loads(batch_analyze_images([]))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_INPUT"
    
    def test_batch_too_large(self):
        """Test oversized batch returns error."""
        from tools.image_batch_analyze import batch_analyze_images
        file_paths = [f"/fake/image{i}.png" for i in range(30)]
        
        result = json.loads(batch_analyze_images(file_paths))
        
        assert result["success"] is False
        assert result["error_code"] == "BATCH_TOO_LARGE"
    
    def test_batch_analyze_single_image(self, tmp_path):
        """Test batch analyze with single image."""
        from tools.image_batch_analyze import batch_analyze_images
        from PIL import Image
        
        test_file = tmp_path / "test.png"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(str(test_file))
        
        result = json.loads(batch_analyze_images([str(test_file)]))
        
        assert result["success"] is True
        assert result["data"]["total"] == 1


class TestBatchAnalyzeDirectory:
    """Test directory scanning."""
    
    def test_nonexistent_directory(self):
        """Test nonexistent directory returns error."""
        from tools.image_batch_analyze import batch_analyze_directory
        result = json.loads(batch_analyze_directory("/nonexistent/dir"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_PATH"
    
    def test_not_a_directory(self, tmp_path):
        """Test file path instead of directory returns error."""
        from tools.image_batch_analyze import batch_analyze_directory
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"content")
        
        result = json.loads(batch_analyze_directory(str(test_file)))
        
        assert result["success"] is False
        assert result["error_code"] == "NOT_A_DIRECTORY"
    
    def test_no_matching_files(self, tmp_path):
        """Test no matching files returns error."""
        from tools.image_batch_analyze import batch_analyze_directory
        result = json.loads(batch_analyze_directory(str(tmp_path), pattern="*.xyz"))
        
        assert result["success"] is False
        assert result["error_code"] == "NO_FILES_FOUND"


class TestBatchToolRegistry:
    """Test tool registration."""
    
    def test_batch_analyze_images_registered(self):
        """Test batch_analyze_images is registered."""
        import tools.image_batch_analyze
        from tools import registry
        entry = registry.registry.get_entry("batch_analyze_images")
        assert entry is not None
        assert entry.toolset == "image"
    
    def test_batch_analyze_directory_registered(self):
        """Test batch_analyze_directory is registered."""
        import tools.image_batch_analyze
        from tools import registry
        entry = registry.registry.get_entry("batch_analyze_directory")
        assert entry is not None
        assert entry.toolset == "image"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])