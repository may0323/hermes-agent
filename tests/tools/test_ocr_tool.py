#!/usr/bin/env python3
"""
Tests for OCR Tool

Covers:
- Image text extraction
- Language support
- Layout preservation
- Error handling
- File validation
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestOCRRequirements:
    """Test OCR availability check."""
    
    def test_check_requirements_when_available(self):
        """Test that check_requirements returns True when dependencies available."""
        with patch("tools.ocr_tool.PYTESSERACT_AVAILABLE", True):
            with patch("tools.ocr_tool.PIL_AVAILABLE", True):
                from tools.ocr_tool import check_ocr_requirements
                assert check_ocr_requirements() is True
    
    def test_check_requirements_when_pytesseract_missing(self):
        """Test that check_requirements returns False when pytesseract missing."""
        with patch("tools.ocr_tool.PYTESSERACT_AVAILABLE", False):
            with patch("tools.ocr_tool.PIL_AVAILABLE", True):
                from tools.ocr_tool import check_ocr_requirements
                assert check_ocr_requirements() is False
    
    def test_check_requirements_when_pil_missing(self):
        """Test that check_requirements returns False when PIL missing."""
        with patch("tools.ocr_tool.PYTESSERACT_AVAILABLE", True):
            with patch("tools.ocr_tool.PIL_AVAILABLE", False):
                from tools.ocr_tool import check_ocr_requirements
                assert check_ocr_requirements() is False


class TestFileSizeValidation:
    """Test file size validation."""
    
    def test_check_file_size_valid_file(self, tmp_path):
        """Test that valid file passes size check."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake png content" * 100)
        
        from tools.ocr_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_check_file_size_nonexistent(self):
        """Test that nonexistent file fails."""
        from tools.ocr_tool import _check_file_size
        is_valid, error_msg = _check_file_size("/nonexistent/path/image.png")
        
        assert is_valid is False
        assert "not found" in error_msg.lower()
    
    def test_check_file_size_too_large(self, tmp_path):
        """Test that oversized file fails."""
        test_file = tmp_path / "large.png"
        test_file.write_bytes(b"x" * (60 * 1024 * 1024))
        
        from tools.ocr_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is False
        assert "too large" in error_msg.lower()
    
    def test_unsupported_format(self, tmp_path):
        """Test that unsupported format fails."""
        test_file = tmp_path / "test.xyz"
        test_file.write_bytes(b"fake content")
        
        from tools.ocr_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is False
        assert "unsupported" in error_msg.lower()


class TestOCRImageExtraction:
    """Test OCR image text extraction."""
    
    def test_basic_text_extraction(self, tmp_path):
        """Test basic OCR text extraction."""
        from tools.ocr_tool import ocr_image_tool
        
        mock_img = MagicMock()
        mock_img.size = (100, 100)
        
        with patch("tools.ocr_tool.check_ocr_requirements", return_value=True):
            with patch("tools.ocr_tool._get_pil_image", return_value=MagicMock()):
                with patch("tools.ocr_tool._get_pytesseract") as mock_get_tesseract:
                    mock_tesseract = MagicMock()
                    mock_tesseract.image_to_string.return_value = "Hello World"
                    mock_get_tesseract.return_value = mock_tesseract
                    
                    with patch("tools.ocr_tool._check_file_size", return_value=(True, "")):
                        result = json.loads(ocr_image_tool(str(tmp_path / "test.png")))
        
        assert result["success"] is True
        assert result["data"]["text"] == "Hello World"
        assert result["data"]["language"] == "eng"
    
    def test_chinese_language(self, tmp_path):
        """Test OCR with Chinese language."""
        from tools.ocr_tool import ocr_image_tool
        
        with patch("tools.ocr_tool.check_ocr_requirements", return_value=True):
            with patch("tools.ocr_tool._get_pil_image", return_value=MagicMock()):
                with patch("tools.ocr_tool._get_pytesseract") as mock_get_tesseract:
                    mock_tesseract = MagicMock()
                    mock_tesseract.image_to_string.return_value = "你好世界"
                    mock_get_tesseract.return_value = mock_tesseract
                    
                    with patch("tools.ocr_tool._check_file_size", return_value=(True, "")):
                        result = json.loads(ocr_image_tool(str(tmp_path / "test.png"), language="chi_sim"))
        
        assert result["success"] is True
        assert result["data"]["language"] == "chi_sim"
    
    def test_confidence_scores(self, tmp_path):
        """Test OCR with confidence scores."""
        from tools.ocr_tool import ocr_image_tool
        
        with patch("tools.ocr_tool.check_ocr_requirements", return_value=True):
            with patch("tools.ocr_tool._get_pil_image", return_value=MagicMock()):
                with patch("tools.ocr_tool._get_pytesseract") as mock_get_tesseract:
                    mock_tesseract = MagicMock()
                    mock_tesseract.image_to_string.return_value = "Text"
                    mock_tesseract.image_to_data.return_value = {
                        'conf': ['95', '87', '92', '-1'],
                        'text': ['Hello', '', 'World', '']
                    }
                    mock_get_tesseract.return_value = mock_tesseract
                    
                    with patch("tools.ocr_tool._check_file_size", return_value=(True, "")):
                        result = json.loads(ocr_image_tool(str(tmp_path / "test.png"), get_confidence=True))
        
        assert result["success"] is True
        assert "confidence" in result["data"]
        assert "avg_confidence" in result["data"]


class TestOCRErrorHandling:
    """Test OCR error handling."""
    
    def test_missing_dependency(self, tmp_path):
        """Test that missing dependency returns proper error."""
        from tools.ocr_tool import ocr_image_tool
        
        with patch("tools.ocr_tool._check_file_size", return_value=(True, "")):
            with patch("tools.ocr_tool.check_ocr_requirements", return_value=False):
                result = json.loads(ocr_image_tool(str(tmp_path / "test.png")))
        
        assert result["success"] is False
        assert result["error_code"] == "MISSING_DEPENDENCY"
    
    def test_tesseract_not_installed(self, tmp_path):
        """Test error when Tesseract not installed."""
        from tools.ocr_tool import ocr_image_tool
        
        with patch("tools.ocr_tool._check_file_size", return_value=(True, "")):
            with patch("tools.ocr_tool.check_ocr_requirements", return_value=True):
                with patch("tools.ocr_tool._get_pil_image", return_value=MagicMock()):
                    with patch("tools.ocr_tool._get_pytesseract", side_effect=Exception("tesseract not found")):
                        result = json.loads(ocr_image_tool(str(tmp_path / "test.png")))
        
        assert result["success"] is False
        assert result["error_code"] == "TESSERACT_NOT_INSTALLED"
    
    def test_unsupported_language(self, tmp_path):
        """Test error for unsupported language."""
        from tools.ocr_tool import ocr_image_tool
        
        with patch("tools.ocr_tool._check_file_size", return_value=(True, "")):
            with patch("tools.ocr_tool.check_ocr_requirements", return_value=True):
                with patch("tools.ocr_tool._get_pil_image", return_value=MagicMock()):
                    with patch("tools.ocr_tool._get_pytesseract", side_effect=Exception("language not supported")):
                        result = json.loads(ocr_image_tool(str(tmp_path / "test.png"), language="invalid"))
        
        assert result["success"] is False
        assert result["error_code"] == "UNSUPPORTED_LANGUAGE"


class TestGetOCRLanguages:
    """Test get_ocr_languages tool."""
    
    def test_get_languages_success(self):
        """Test getting available OCR languages."""
        from tools.ocr_tool import get_ocr_languages_tool
        
        with patch("tools.ocr_tool.PYTESSERACT_AVAILABLE", True):
            with patch("tools.ocr_tool._get_pytesseract") as mock_get_tesseract:
                mock_tesseract = MagicMock()
                mock_tesseract.get_languages.return_value = ["eng", "chi_sim", "jpn"]
                mock_get_tesseract.return_value = mock_tesseract
                
                result = json.loads(get_ocr_languages_tool())
        
        assert result["success"] is True
        assert result["data"]["count"] == 3
        assert len(result["data"]["languages"]) == 3
    
    def test_get_languages_unavailable(self):
        """Test getting languages when pytesseract unavailable."""
        from tools.ocr_tool import get_ocr_languages_tool
        
        with patch("tools.ocr_tool.PYTESSERACT_AVAILABLE", False):
            result = json.loads(get_ocr_languages_tool())
        
        assert result["success"] is False
        assert result["error_code"] == "MISSING_DEPENDENCY"


class TestOCRToolRegistry:
    """Test that OCR tools are properly registered."""
    
    def test_ocr_image_registered(self):
        """Test that ocr_image is registered in the tool registry."""
        from tools import registry
        entry = registry.registry.get_entry("ocr_image")
        assert entry is not None
        assert entry.toolset == "image"
        assert entry.name == "ocr_image"
    
    def test_ocr_pdf_registered(self):
        """Test that ocr_pdf is registered in the tool registry."""
        from tools import registry
        entry = registry.registry.get_entry("ocr_pdf")
        assert entry is not None
        assert entry.toolset == "image"
    
    def test_get_ocr_languages_registered(self):
        """Test that get_ocr_languages is registered."""
        from tools import registry
        entry = registry.registry.get_entry("get_ocr_languages")
        assert entry is not None
        assert entry.toolset == "image"
    
    def test_ocr_image_schema(self):
        """Test that ocr_image has correct schema."""
        from tools import registry
        entry = registry.registry.get_entry("ocr_image")
        
        schema = entry.schema
        assert "file_path" in schema["parameters"]["properties"]
        assert "language" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["file_path"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])