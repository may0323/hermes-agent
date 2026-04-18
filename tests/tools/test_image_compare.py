#!/usr/bin/env python3
"""
Tests for Image Compare Tool

Covers:
- Image similarity comparison
- Pixel difference calculation
- Histogram comparison
- Find similar images
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestImageCompare:
    """Test image comparison."""
    
    def test_invalid_image1(self):
        """Test invalid first image returns error."""
        from tools.image_compare import compare_images
        result = json.loads(compare_images("/nonexistent1.png", "/fake2.png"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_IMAGE1"
    
    def test_invalid_image2(self, tmp_path):
        """Test invalid second image returns error."""
        from tools.image_compare import compare_images
        test_file = tmp_path / "img1.png"
        test_file.write_bytes(b"fake png")
        
        result = json.loads(compare_images(str(test_file), "/nonexistent2.png"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_IMAGE2"
    
    def test_compare_same_image(self, tmp_path):
        """Test comparing identical images."""
        from tools.image_compare import compare_images
        
        test_file = tmp_path / "test.png"
        
        from PIL import Image
        img = Image.new('RGB', (10, 10), color='green')
        img.save(str(test_file))
        
        result = json.loads(compare_images(str(test_file), str(test_file)))
        
        assert result["success"] is True
    
    def test_compare_images_with_numpy(self, tmp_path):
        """Test compare with numpy available."""
        from tools.image_compare import compare_images
        
        test_file1 = tmp_path / "test1.png"
        test_file2 = tmp_path / "test2.png"
        
        import numpy as np
        from PIL import Image
        
        img1 = Image.new('RGB', (10, 10), color='red')
        img2 = Image.new('RGB', (10, 10), color='blue')
        img1.save(str(test_file1))
        img2.save(str(test_file2))
        
        result = json.loads(compare_images(str(test_file1), str(test_file2)))
        
        assert result["success"] is True
        assert "similarity" in result["data"]
        assert "overall_score" in result["data"]["similarity"]


class TestFindSimilarImages:
    """Test find similar images."""
    
    def test_invalid_query(self):
        """Test invalid query image returns error."""
        from tools.image_compare import find_similar_images
        result = json.loads(find_similar_images("/nonexistent.png", "/some/dir"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_QUERY"
    
    def test_invalid_directory(self, tmp_path):
        """Test invalid directory returns error."""
        from tools.image_compare import find_similar_images
        test_file = tmp_path / "query.png"
        test_file.write_bytes(b"fake png")
        
        result = json.loads(find_similar_images(str(test_file), "/nonexistent/dir"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_DIRECTORY"


class TestImageCompareRegistry:
    """Test tool registration."""
    
    def test_compare_images_registered(self):
        """Test compare_images is registered."""
        import tools.image_compare
        from tools import registry
        entry = registry.registry.get_entry("compare_images")
        assert entry is not None
        assert entry.toolset == "image"
    
    def test_find_similar_images_registered(self):
        """Test find_similar_images is registered."""
        import tools.image_compare
        from tools import registry
        entry = registry.registry.get_entry("find_similar_images")
        assert entry is not None
        assert entry.toolset == "image"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])