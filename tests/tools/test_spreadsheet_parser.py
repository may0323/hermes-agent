#!/usr/bin/env python3
"""
Tests for Spreadsheet Parser Tool

Covers:
- CSV text extraction
- Excel text extraction
- Error handling
- File validation
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestSpreadsheetRequirements:
    """Test spreadsheet availability check."""
    
    def test_check_requirements_always_available(self):
        """Test that check_requirements always returns True (uses stdlib csv)."""
        from tools.spreadsheet_parser_tool import check_spreadsheet_requirements
        assert check_spreadsheet_requirements() is True


class TestFileSizeValidation:
    """Test file size validation."""
    
    def test_check_file_size_valid_file(self, tmp_path):
        """Test that valid file passes size check."""
        test_file = tmp_path / "test.csv"
        test_file.write_bytes(b"col1,col2\nval1,val2" * 100)
        
        from tools.spreadsheet_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_check_file_size_nonexistent(self):
        """Test that nonexistent file fails."""
        from tools.spreadsheet_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size("/nonexistent/path/file.csv")
        
        assert is_valid is False
        assert "not found" in error_msg.lower()
    
    def test_check_file_size_too_large(self, tmp_path):
        """Test that oversized file fails."""
        test_file = tmp_path / "large.csv"
        test_file.write_bytes(b"x" * (60 * 1024 * 1024))
        
        from tools.spreadsheet_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is False
        assert "too large" in error_msg.lower()
    
    def test_check_file_size_empty(self, tmp_path):
        """Test that empty file fails."""
        test_file = tmp_path / "empty.csv"
        test_file.write_bytes(b"")
        
        from tools.spreadsheet_parser_tool import _check_file_size
        is_valid, error_msg = _check_file_size(str(test_file))
        
        assert is_valid is False
        assert "empty" in error_msg.lower()


class TestCSVContentExtraction:
    """Test CSV content extraction."""
    
    def test_csv_basic_extraction(self, tmp_path):
        """Test basic CSV extraction."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA", encoding='utf-8')
        
        from tools.spreadsheet_parser_tool import parse_csv_tool
        result = json.loads(parse_csv_tool(str(test_file)))
        
        assert result["success"] is True
        assert result["data"]["row_count"] == 3
        assert result["data"]["column_count"] == 3
        assert result["data"]["headers"] == ["name", "age", "city"]
        assert "Alice" in result["data"]["content"]
    
    def test_csv_max_rows(self, tmp_path):
        """Test CSV with max_rows limit."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1\nrow1\nrow2\nrow3\nrow4\nrow5", encoding='utf-8')
        
        from tools.spreadsheet_parser_tool import parse_csv_tool
        result = json.loads(parse_csv_tool(str(test_file), max_rows=2))
        
        assert result["success"] is True
        assert result["data"]["row_count"] == 2
    
    def test_csv_empty_file(self, tmp_path):
        """Test CSV with empty content is rejected."""
        test_file = tmp_path / "empty.csv"
        test_file.write_text("", encoding='utf-8')
        
        from tools.spreadsheet_parser_tool import parse_csv_tool
        result = json.loads(parse_csv_tool(str(test_file)))
        
        assert result["success"] is False
        assert "empty" in result["error"].lower()


class TestExcelContentExtraction:
    """Test Excel content extraction."""
    
    def test_parse_excel_tool(self):
        """Test Excel parsing with mocking."""
        from tools.spreadsheet_parser_tool import parse_excel_tool
        
        mock_cell1 = MagicMock()
        mock_cell1.value = "Header1"
        
        mock_cell2 = MagicMock()
        mock_cell2.value = "Data1"
        
        mock_row1 = MagicMock()
        mock_row1.values = ["Header1", "Header2"]
        
        mock_row2 = MagicMock()
        mock_row2.values = ["Data1", "Data2"]
        
        mock_ws = MagicMock()
        mock_ws.title = "Sheet1"
        mock_ws.iter_rows.return_value = [mock_row1, mock_row2]
        
        mock_wb = MagicMock()
        mock_wb.active = mock_ws
        mock_wb.sheetnames = ["Sheet1"]
        mock_wb.__getitem__.return_value = mock_ws
        
        with patch("tools.spreadsheet_parser_tool.OPENPYXL_AVAILABLE", True):
            with patch("tools.spreadsheet_parser_tool._get_openpyxl", return_value=lambda **kw: mock_wb):
                with patch("tools.spreadsheet_parser_tool._check_file_size", return_value=(True, "")):
                    result = json.loads(parse_excel_tool("/fake/path.xlsx"))
        
        assert result["success"] is True
        assert result["data"]["content_type"] == "excel"
    
    def test_parse_excel_missing_dependency(self):
        """Test Excel parsing when openpyxl is not available."""
        from tools.spreadsheet_parser_tool import parse_excel_tool
        
        with patch("tools.spreadsheet_parser_tool.OPENPYXL_AVAILABLE", False):
            with patch("tools.spreadsheet_parser_tool._check_file_size", return_value=(True, "")):
                result = json.loads(parse_excel_tool("/fake/path.xlsx"))
        
        assert result["success"] is False
        assert result["error_code"] == "MISSING_DEPENDENCY"


class TestSpreadsheetParsing:
    """Test general spreadsheet parsing functions."""
    
    def test_parse_spreadsheet_csv(self, tmp_path):
        """Test parse_spreadsheet with CSV file."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2", encoding='utf-8')
        
        from tools.spreadsheet_parser_tool import parse_spreadsheet_tool
        result = json.loads(parse_spreadsheet_tool(str(test_file)))
        
        assert result["success"] is True
        assert result["data"]["content_type"] == "csv"
    
    def test_parse_spreadsheet_unsupported_format(self):
        """Test parse_spreadsheet with unsupported format."""
        from tools.spreadsheet_parser_tool import parse_spreadsheet_tool
        result = json.loads(parse_spreadsheet_tool("/fake/path.txt"))
        
        assert result["success"] is False
        assert result["error_code"] == "UNSUPPORTED_FORMAT"


class TestGetSpreadsheetInfo:
    """Test get_spreadsheet_info tool."""
    
    def test_get_csv_info(self, tmp_path):
        """Test getting info from CSV file."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("name,age\nAlice,30\nBob,25", encoding='utf-8')
        
        from tools.spreadsheet_parser_tool import get_spreadsheet_info_tool
        result = json.loads(get_spreadsheet_info_tool(str(test_file)))
        
        assert result["success"] is True
        assert result["data"]["row_count"] == 3
        assert result["data"]["column_count"] == 2
        assert result["data"]["headers"] == ["name", "age"]
        assert result["data"]["format"] == "csv"
    
    def test_get_spreadsheet_info_unsupported(self, tmp_path):
        """Test get_spreadsheet_info with unsupported format."""
        test_file = tmp_path / "test.xyz"
        test_file.write_bytes(b"some content")
        
        from tools.spreadsheet_parser_tool import get_spreadsheet_info_tool
        result = json.loads(get_spreadsheet_info_tool(str(test_file)))
        
        assert result["success"] is False
        assert result["error_code"] == "UNSUPPORTED_FORMAT"


class TestSpreadsheetToolRegistry:
    """Test that tools are properly registered."""
    
    def test_parse_spreadsheet_registered(self):
        """Test that parse_spreadsheet is registered in the tool registry."""
        from tools import registry
        entry = registry.registry.get_entry("parse_spreadsheet")
        assert entry is not None
        assert entry.toolset == "document"
        assert entry.name == "parse_spreadsheet"
    
    def test_get_spreadsheet_info_registered(self):
        """Test that get_spreadsheet_info is registered in the tool registry."""
        from tools import registry
        entry = registry.registry.get_entry("get_spreadsheet_info")
        assert entry is not None
        assert entry.toolset == "document"
        assert entry.name == "get_spreadsheet_info"
    
    def test_parse_spreadsheet_schema(self):
        """Test that parse_spreadsheet has correct schema."""
        from tools import registry
        entry = registry.registry.get_entry("parse_spreadsheet")
        
        schema = entry.schema
        assert "file_path" in schema["parameters"]["properties"]
        assert "max_rows" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["file_path"]
    
    def test_get_spreadsheet_info_schema(self):
        """Test that get_spreadsheet_info has correct schema."""
        from tools import registry
        entry = registry.registry.get_entry("get_spreadsheet_info")
        
        schema = entry.schema
        assert "file_path" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["file_path"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])