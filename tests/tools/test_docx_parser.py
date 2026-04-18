#!/usr/bin/env python3
"""
Tests for DOCX Parser Tool

Covers:
- DOCX text extraction
- Table extraction
- Error handling
- File validation
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestDOCXRequirements:
    """Test python-docx availability check."""
    
    def test_check_requirements_when_available(self):
        """Test that check_requirements returns True when python-docx is available."""
        with patch("tools.docx_parser_tool.PYTHON_DOCX_AVAILABLE", True):
            from tools.docx_parser_tool import check_docx_requirements
            assert check_docx_requirements() is True
    
    def test_check_requirements_when_unavailable(self):
        """Test that check_requirements returns False when python-docx is not available."""
        with patch("tools.docx_parser_tool.PYTHON_DOCX_AVAILABLE", False):
            from tools.docx_parser_tool import check_docx_requirements
            assert check_docx_requirements() is False


class TestFileSizeValidation:
    """Test file size validation."""
    
    def test_check_file_size_valid_file(self, tmp_path):
        """Test that valid file passes size check."""
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"fake docx content" * 100)
        
        from tools.docx_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_check_file_size_nonexistent(self):
        """Test that nonexistent file fails."""
        from tools.docx_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size("/nonexistent/path/file.docx")
        
        assert is_valid is False
        assert "not found" in error_msg.lower()
    
    def test_check_file_size_too_large(self, tmp_path):
        """Test that oversized file fails."""
        test_file = tmp_path / "large.docx"
        test_file.write_bytes(b"x" * (60 * 1024 * 1024))
        
        from tools.docx_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is False
        assert "too large" in error_msg.lower()
    
    def test_check_file_size_empty(self, tmp_path):
        """Test that empty file fails."""
        test_file = tmp_path / "empty.docx"
        test_file.write_bytes(b"")
        
        from tools.docx_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is False
        assert "empty" in error_msg.lower()


class TestDOCXContentExtraction:
    """Test DOCX content extraction."""
    
    def test_paragraph_extraction(self):
        """Test that paragraphs are extracted correctly."""
        from tools.docx_parser_tool import parse_docx_tool
        
        mock_para1 = MagicMock()
        mock_para1.text = "First paragraph content"
        mock_para1.style = MagicMock()
        mock_para1.style.name = "Normal"
        
        mock_para2 = MagicMock()
        mock_para2.text = "Second paragraph content"
        mock_para2.style = MagicMock()
        mock_para2.style.name = "Heading 1"
        
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_doc.tables = []
        
        with patch("tools.docx_parser_tool.check_docx_requirements", return_value=True):
            with patch("docx.Document", return_value=mock_doc):
                with patch("tools.docx_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(parse_docx_tool("/fake/path.docx"))
        
        assert result["success"] is True
        assert "First paragraph content" in result["data"]["content"]
        assert "Second paragraph content" in result["data"]["content"]
        assert result["data"]["paragraphs"] == 2
    
    def test_table_extraction(self):
        """Test that tables are extracted correctly."""
        from tools.docx_parser_tool import parse_docx_tool
        
        mock_cell1 = MagicMock()
        mock_cell1.text = "Cell 1"
        
        mock_cell2 = MagicMock()
        mock_cell2.text = "Cell 2"
        
        mock_row = MagicMock()
        mock_row.cells = [mock_cell1, mock_cell2]
        
        mock_table = MagicMock()
        mock_table.rows = [mock_row]
        mock_table.columns = [MagicMock(), MagicMock()]
        
        mock_para = MagicMock()
        mock_para.text = ""
        
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]
        mock_doc.tables = [mock_table]
        
        with patch("tools.docx_parser_tool.check_docx_requirements", return_value=True):
            with patch("docx.Document", return_value=mock_doc):
                with patch("tools.docx_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(parse_docx_tool("/fake/path.docx", extract_tables=True))
        
        assert result["success"] is True
        assert result["data"]["tables"] == 1
        assert len(result.get("tables", [])) == 1
        assert result["tables"][0]["rows"] == 1
    
    def test_empty_document(self):
        """Test that empty document is handled gracefully."""
        from tools.docx_parser_tool import parse_docx_tool
        
        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc.tables = []
        
        with patch("tools.docx_parser_tool.check_docx_requirements", return_value=True):
            with patch("docx.Document", return_value=mock_doc):
                with patch("tools.docx_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(parse_docx_tool("/fake/path.docx"))
        
        assert result["success"] is True
        assert result["data"]["content"] == ""
        assert result["data"]["paragraphs"] == 0


class TestDOCXErrorHandling:
    """Test error handling."""
    
    def test_missing_dependency(self):
        """Test that missing dependency returns proper error."""
        from tools.docx_parser_tool import parse_docx_tool
        
        with patch("tools.docx_parser_tool._check_file_size", return_value=(True, "")):
            with patch("tools.docx_parser_tool.check_docx_requirements", return_value=False):
                result = json.loads(parse_docx_tool("/fake/path.docx"))
        
        assert result["success"] is False
        assert result["error_code"] == "MISSING_DEPENDENCY"
        assert "pip install python-docx" in result["error"]
    
    def test_corrupt_file(self):
        """Test that corrupt file returns proper error."""
        from tools.docx_parser_tool import parse_docx_tool
        
        with patch("tools.docx_parser_tool._check_file_size", return_value=(True, "")):
            with patch("tools.docx_parser_tool.check_docx_requirements", return_value=True):
                with patch("docx.Document", side_effect=Exception("invalid archive")):
                    result = json.loads(parse_docx_tool("/fake/path.docx"))
        
        assert result["success"] is False
        assert result["error_code"] == "CORRUPT_FILE"
    
    def test_password_protected(self):
        """Test that password-protected file returns proper error."""
        from tools.docx_parser_tool import parse_docx_tool
        
        with patch("tools.docx_parser_tool._check_file_size", return_value=(True, "")):
            with patch("tools.docx_parser_tool.check_docx_requirements", return_value=True):
                with patch("docx.Document", side_effect=Exception("password")):
                    result = json.loads(parse_docx_tool("/fake/path.docx"))
        
        assert result["success"] is False
        assert result["error_code"] == "PASSWORD_PROTECTED"


class TestGetDOCXInfo:
    """Test get_docx_info tool."""
    
    def test_get_docx_info_success(self, tmp_path):
        """Test successful DOCX info extraction."""
        from tools.docx_parser_tool import get_docx_info_tool
        
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"fake docx content")
        
        mock_para1 = MagicMock()
        mock_para1.text = "Para 1"
        mock_para2 = MagicMock()
        mock_para2.text = "Para 2"
        mock_para3 = MagicMock()
        mock_para3.text = ""
        
        mock_table = MagicMock()
        
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]
        mock_doc.tables = [mock_table]
        
        with patch("tools.docx_parser_tool.check_docx_requirements", return_value=True):
            with patch("docx.Document", return_value=mock_doc):
                with patch("tools.docx_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(get_docx_info_tool(str(test_file)))
        
        assert result["success"] is True
        assert result["data"]["paragraph_count"] == 2
        assert result["data"]["table_count"] == 1
        assert result["data"]["file_name"] == "test.docx"


class TestDOCXToolRegistry:
    """Test that tools are properly registered."""
    
    def test_parse_docx_registered(self):
        """Test that parse_docx is registered in the tool registry."""
        from tools import registry
        entry = registry.registry.get_entry("parse_docx")
        assert entry is not None
        assert entry.toolset == "document"
        assert entry.name == "parse_docx"
    
    def test_get_docx_info_registered(self):
        """Test that get_docx_info is registered in the tool registry."""
        from tools import registry
        entry = registry.registry.get_entry("get_docx_info")
        assert entry is not None
        assert entry.toolset == "document"
        assert entry.name == "get_docx_info"
    
    def test_parse_docx_schema(self):
        """Test that parse_docx has correct schema."""
        from tools import registry
        entry = registry.registry.get_entry("parse_docx")
        
        schema = entry.schema
        assert "file_path" in schema["parameters"]["properties"]
        assert "extract_tables" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["file_path"]
    
    def test_get_docx_info_schema(self):
        """Test that get_docx_info has correct schema."""
        from tools import registry
        entry = registry.registry.get_entry("get_docx_info")
        
        schema = entry.schema
        assert "file_path" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["file_path"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])