#!/usr/bin/env python3
"""
Tests for PDF Parser Tool

Covers:
- PDF text extraction
- Metadata extraction
- Error handling
- File validation
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPDFRequirements:
    """Test pypdf availability check."""
    
    def test_check_requirements_when_available(self):
        """Test that check_requirements returns True when pypdf is available."""
        with patch("tools.pdf_parser_tool.PYPDF_AVAILABLE", True):
            from tools.pdf_parser_tool import check_pdf_requirements
            assert check_pdf_requirements() is True
    
    def test_check_requirements_when_unavailable(self):
        """Test that check_requirements returns False when pypdf is not available."""
        with patch("tools.pdf_parser_tool.PYPDF_AVAILABLE", False):
            from tools.pdf_parser_tool import check_pdf_requirements
            assert check_pdf_requirements() is False


class TestFileSizeValidation:
    """Test file size validation."""
    
    def test_check_file_size_valid_file(self, tmp_path):
        """Test that valid file passes size check."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content" * 100)
        
        from tools.pdf_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_check_file_size_nonexistent(self):
        """Test that nonexistent file fails."""
        from tools.pdf_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size("/nonexistent/path/file.pdf")
        
        assert is_valid is False
        assert "not found" in error_msg.lower()
    
    def test_check_file_size_too_large(self, tmp_path):
        """Test that oversized file fails."""
        test_file = tmp_path / "large.pdf"
        test_file.write_bytes(b"x" * (60 * 1024 * 1024))
        
        from tools.pdf_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is False
        assert "too large" in error_msg.lower()
    
    def test_check_file_size_empty(self, tmp_path):
        """Test that empty file fails."""
        test_file = tmp_path / "empty.pdf"
        test_file.write_bytes(b"")
        
        from tools.pdf_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is False
        assert "empty" in error_msg.lower()


class TestPDFMetadataExtraction:
    """Test PDF metadata extraction."""
    
    def test_metadata_extraction_format(self):
        """Test that metadata is extracted in correct format."""
        mock_metadata = {
            "/Title": "Test Document",
            "/Author": "Test Author",
            "/Subject": "Test Subject",
            "/Creator": "Test Creator",
            "/Producer": "Test Producer",
            "/CreationDate": "20240101000000",
            "/ModDate": "20240102000000",
        }
        
        from tools.pdf_parser_tool import parse_pdf_tool
        
        mock_reader = MagicMock()
        mock_reader.metadata = mock_metadata
        mock_reader.pages = [MagicMock(), MagicMock()]
        mock_reader.is_encrypted = False
        
        with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=True):
            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(parse_pdf_tool("/fake/path.pdf"))
        
        assert result["success"] is True
        assert "metadata" in result["data"]
        assert result["data"]["metadata"]["title"] == "Test Document"
        assert result["data"]["metadata"]["author"] == "Test Author"


class TestPDFContentExtraction:
    """Test PDF content extraction."""
    
    def test_text_extraction(self):
        """Test that text is extracted from PDF pages."""
        from tools.pdf_parser_tool import parse_pdf_tool
        
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader = MagicMock()
        mock_reader.metadata = None
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader.is_encrypted = False
        
        with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=True):
            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(parse_pdf_tool("/fake/path.pdf"))
        
        assert result["success"] is True
        assert "Page 1 content" in result["data"]["content"]
        assert "Page 2 content" in result["data"]["content"]
        assert "--- Page 1 ---" in result["data"]["content"]
    
    def test_max_pages_limit(self):
        """Test that max_pages limits pages read."""
        from tools.pdf_parser_tool import parse_pdf_tool
        
        mock_pages = [MagicMock() for _ in range(10)]
        for i, page in enumerate(mock_pages):
            page.extract_text.return_value = f"Page {i+1} content"
        
        mock_reader = MagicMock()
        mock_reader.metadata = None
        mock_reader.pages = mock_pages
        mock_reader.is_encrypted = False
        
        with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=True):
            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(parse_pdf_tool("/fake/path.pdf", max_pages=3))
        
        assert result["success"] is True
        assert result["data"]["metadata"]["pages_read"] == 3
        assert result["data"]["metadata"]["truncated"] is True
    
    def test_empty_pages_handled(self):
        """Test that empty pages are handled gracefully."""
        from tools.pdf_parser_tool import parse_pdf_tool
        
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        
        mock_reader = MagicMock()
        mock_reader.metadata = None
        mock_reader.pages = [mock_page]
        mock_reader.is_encrypted = False
        
        with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=True):
            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(parse_pdf_tool("/fake/path.pdf"))
        
        assert result["success"] is True
        assert result["data"]["content"] == ""


class TestPDFErrorHandling:
    """Test error handling."""
    
    def test_missing_dependency(self):
        """Test that missing dependency returns proper error."""
        from tools.pdf_parser_tool import parse_pdf_tool
        
        with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
            with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=False):
                result = json.loads(parse_pdf_tool("/fake/path.pdf"))
        
        assert result["success"] is False
        assert result["error_code"] == "MISSING_DEPENDENCY"
        assert "pip install pypdf" in result["error"]
    
    def test_password_protected_pdf(self):
        """Test that password-protected PDF returns proper error."""
        from tools.pdf_parser_tool import parse_pdf_tool
        
        with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
            with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=True):
                with patch("pypdf.PdfReader") as mock_pdf_reader:
                    mock_pdf_reader.side_effect = Exception("password required")
                    
                    result = json.loads(parse_pdf_tool("/fake/path.pdf"))
        
        assert result["success"] is False
        assert result["error_code"] == "PASSWORD_PROTECTED"
    
    def test_encrypted_pdf(self):
        """Test that encrypted PDF returns proper error."""
        from tools.pdf_parser_tool import parse_pdf_tool
        
        with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
            with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=True):
                with patch("pypdf.PdfReader") as mock_pdf_reader:
                    mock_pdf_reader.side_effect = Exception("encrypted PDF")
                    
                    result = json.loads(parse_pdf_tool("/fake/path.pdf"))
        
        assert result["success"] is False
        assert result["error_code"] == "ENCRYPTED"


class TestGetPDFInfo:
    """Test get_pdf_info tool."""
    
    def test_get_pdf_info_success(self, tmp_path):
        """Test successful PDF info extraction."""
        from tools.pdf_parser_tool import get_pdf_info_tool
        
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")
        
        mock_metadata = {
            "/Title": "Test",
            "/Author": "Author",
            "/Subject": None,
            "/Creator": None,
            "/Producer": None,
        }
        
        mock_reader = MagicMock()
        mock_reader.metadata = mock_metadata
        mock_reader.pages = [MagicMock() for _ in range(5)]
        mock_reader.is_encrypted = False
        
        with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=True):
            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(get_pdf_info_tool(str(test_file)))
        
        assert result["success"] is True
        assert result["data"]["pages"] == 5
        assert result["data"]["file_name"] == "test.pdf"
        assert result["data"]["metadata"]["title"] == "Test"
        assert result["data"]["metadata"]["is_encrypted"] is False
    
    def test_get_pdf_info_returns_is_encrypted(self, tmp_path):
        """Test that is_encrypted field is properly returned."""
        from tools.pdf_parser_tool import get_pdf_info_tool
        
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")
        
        mock_reader = MagicMock()
        mock_reader.metadata = {}
        mock_reader.pages = []
        mock_reader.is_encrypted = True
        
        with patch("tools.pdf_parser_tool.check_pdf_requirements", return_value=True):
            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("tools.pdf_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(get_pdf_info_tool(str(test_file)))
        
        assert result["success"] is True
        assert result["data"]["metadata"]["is_encrypted"] is True


class TestPDFToolRegistry:
    """Test that tools are properly registered."""
    
    def test_parse_pdf_registered(self):
        """Test that parse_pdf is registered in the tool registry."""
        from tools import registry
        entry = registry.registry.get_entry("parse_pdf")
        assert entry is not None
        assert entry.toolset == "document"
        assert entry.name == "parse_pdf"
    
    def test_get_pdf_info_registered(self):
        """Test that get_pdf_info is registered in the tool registry."""
        from tools import registry
        entry = registry.registry.get_entry("get_pdf_info")
        assert entry is not None
        assert entry.toolset == "document"
        assert entry.name == "get_pdf_info"
    
    def test_parse_pdf_schema(self):
        """Test that parse_pdf has correct schema."""
        from tools import registry
        entry = registry.registry.get_entry("parse_pdf")
        
        schema = entry.schema
        assert "file_path" in schema["parameters"]["properties"]
        assert "max_pages" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["file_path"]
    
    def test_get_pdf_info_schema(self):
        """Test that get_pdf_info has correct schema."""
        from tools import registry
        entry = registry.registry.get_entry("get_pdf_info")
        
        schema = entry.schema
        assert "file_path" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["file_path"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
