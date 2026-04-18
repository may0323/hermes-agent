#!/usr/bin/env python3
"""
Spreadsheet Parser Tool Module

This module provides tools for extracting data from spreadsheet files (CSV, Excel).

Features:
- CSV text extraction
- Excel (.xlsx) text extraction
- Header detection
- Data type information
- Error handling with user-friendly messages

Usage:
    from tools.spreadsheet_parser_tool import parse_spreadsheet_tool
    
    result = parse_spreadsheet_tool(file_path="/path/to/spreadsheet.csv")
    if result["success"]:
        print(result["data"]["content"])
"""

import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from tools.registry import registry

logger = logging.getLogger(__name__)

CSV_AVAILABLE = True
OPENPYXL_AVAILABLE = importlib.util.find_spec("openpyxl") is not None

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def check_spreadsheet_requirements() -> bool:
    """Check if the required dependencies for spreadsheet parsing are available."""
    return True


def _check_file_size(file_path: str) -> tuple[bool, str]:
    """Check if file size is within limits.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}"
    
    if not path.is_file():
        return False, f"Not a file: {file_path}"
    
    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File too large: {size / (1024*1024):.1f}MB (max: {MAX_FILE_SIZE_MB}MB)"
    
    if size == 0:
        return False, "File is empty"
    
    return True, ""


def _get_csv_reader():
    """Lazily import csv reader."""
    import csv
    return csv


def _get_openpyxl():
    """Lazily import openpyxl."""
    if not OPENPYXL_AVAILABLE:
        raise ImportError(
            "openpyxl is required for Excel parsing. Install with: pip install openpyxl"
        )
    from openpyxl import load_workbook
    return load_workbook


def parse_csv_tool(
    file_path: str,
    max_rows: Optional[int] = None,
    task_id: Optional[str] = None,
) -> str:
    """Parse a CSV file and extract data.
    
    Args:
        file_path: Path to the CSV file to parse.
        max_rows: Maximum number of rows to parse. If None, all rows are parsed.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and extracted data.
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    try:
        csv = _get_csv_reader()
        
        rows = []
        headers = []
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if max_rows and i >= max_rows:
                    break
                if i == 0:
                    headers = row
                rows.append(row)
        
        content_lines = []
        for i, row in enumerate(rows):
            content_lines.append(f"Row {i+1}: {' | '.join(row)}")
        
        return json.dumps({
            "success": True,
            "data": {
                "content": "\n".join(content_lines),
                "row_count": len(rows),
                "column_count": len(headers) if headers else 0,
                "headers": headers,
                "content_type": "csv"
            }
        })
        
    except Exception as e:
        logger.exception(f"Error parsing CSV: {file_path}")
        return json.dumps({
            "success": False,
            "error": f"Failed to parse CSV: {str(e)}",
            "error_code": "PARSE_ERROR"
        })


def parse_excel_tool(
    file_path: str,
    sheet_name: Optional[str] = None,
    max_rows: Optional[int] = None,
    task_id: Optional[str] = None,
) -> str:
    """Parse an Excel file and extract data.
    
    Args:
        file_path: Path to the Excel file to parse.
        sheet_name: Name of the sheet to parse. If None, first sheet is used.
        max_rows: Maximum number of rows to parse per sheet.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and extracted data.
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not OPENPYXL_AVAILABLE:
        return json.dumps({
            "success": False,
            "error": "Excel parsing requires the openpyxl library. Install with: pip install openpyxl",
            "error_code": "MISSING_DEPENDENCY"
        })
    
    try:
        load_workbook = _get_openpyxl()
        wb = load_workbook(filename=file_path, read_only=True, data_only=True)
        
        if sheet_name and sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
        else:
            ws = wb.active
        
        headers = []
        rows_data = []
        
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if max_rows and i >= max_rows:
                break
            
            row_values = [str(cell) if cell is not None else "" for cell in row]
            
            if i == 0:
                headers = row_values
            rows_data.append(row_values)
        
        content_lines = []
        for i, row in enumerate(rows_data):
            content_lines.append(f"Row {i+1}: {' | '.join(row)}")
        
        sheet_names = wb.sheetnames
        
        return json.dumps({
            "success": True,
            "data": {
                "content": "\n".join(content_lines),
                "row_count": len(rows_data),
                "column_count": len(headers) if headers else 0,
                "headers": headers,
                "sheet_name": ws.title,
                "content_type": "excel"
            },
            "sheets": sheet_names
        })
        
    except Exception as e:
        logger.exception(f"Error parsing Excel: {file_path}")
        error_str = str(e)
        
        if "password" in error_str.lower():
            return json.dumps({
                "success": False,
                "error": "Excel file is password-protected.",
                "error_code": "PASSWORD_PROTECTED"
            })
        
        if "corrupt" in error_str.lower() or "invalid" in error_str.lower():
            return json.dumps({
                "success": False,
                "error": "Excel file appears to be corrupt or invalid.",
                "error_code": "CORRUPT_FILE"
            })
        
        return json.dumps({
            "success": False,
            "error": f"Failed to parse Excel: {error_str}",
            "error_code": "PARSE_ERROR"
        })


def parse_spreadsheet_tool(
    file_path: str,
    max_rows: Optional[int] = None,
    task_id: Optional[str] = None,
) -> str:
    """Parse a spreadsheet file (CSV or Excel) and extract data.
    
    Auto-detects file type based on extension.
    
    Args:
        file_path: Path to the spreadsheet file to parse.
        max_rows: Maximum number of rows to parse.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and extracted data.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    if suffix == '.csv':
        return parse_csv_tool(file_path, max_rows, task_id)
    elif suffix in ['.xlsx', '.xlsm', '.xls']:
        return parse_excel_tool(file_path, None, max_rows, task_id)
    else:
        return json.dumps({
            "success": False,
            "error": f"Unsupported file format: {suffix}. Supported formats: .csv, .xlsx, .xlsm, .xls",
            "error_code": "UNSUPPORTED_FORMAT"
        })


def get_spreadsheet_info_tool(
    file_path: str,
    task_id: Optional[str] = None,
) -> str:
    """Get basic information about a spreadsheet file.
    
    Args:
        file_path: Path to the spreadsheet file.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with spreadsheet metadata.
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    if suffix == '.csv':
        try:
            csv = _get_csv_reader()
            row_count = 0
            column_count = 0
            headers = []
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i == 0:
                        headers = row
                        column_count = len(row)
                    row_count += 1
            
            return json.dumps({
                "success": True,
                "data": {
                    "file_name": path.name,
                    "file_path": str(path.resolve()),
                    "file_size_bytes": path.stat().st_size,
                    "row_count": row_count,
                    "column_count": column_count,
                    "headers": headers,
                    "format": "csv"
                }
            })
        except Exception as e:
            logger.exception(f"Error getting CSV info: {file_path}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "error_code": "INFO_ERROR"
            })
    
    elif suffix in ['.xlsx', '.xlsm', '.xls']:
        if not OPENPYXL_AVAILABLE:
            return json.dumps({
                "success": False,
                "error": "Excel parsing requires the openpyxl library.",
                "error_code": "MISSING_DEPENDENCY"
            })
        
        try:
            load_workbook = _get_openpyxl()
            wb = load_workbook(filename=file_path, read_only=True, data_only=True)
            
            info = {
                "file_name": path.name,
                "file_path": str(path.resolve()),
                "file_size_bytes": path.stat().st_size,
                "sheet_count": len(wb.sheetnames),
                "sheets": wb.sheetnames,
                "format": "excel"
            }
            
            return json.dumps({
                "success": True,
                "data": info
            })
        except Exception as e:
            logger.exception(f"Error getting Excel info: {file_path}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "error_code": "INFO_ERROR"
            })
    else:
        return json.dumps({
            "success": False,
            "error": f"Unsupported file format: {suffix}",
            "error_code": "UNSUPPORTED_FORMAT"
        })


registry.register(
    name="parse_spreadsheet",
    toolset="document",
    schema={
        "name": "parse_spreadsheet",
        "description": """Parse and extract data from spreadsheet files (CSV, Excel).

Use this tool when the user uploads a spreadsheet and wants to:
- Extract tabular data for analysis
- Search for specific values in a spreadsheet
- Summarize spreadsheet content
- Get row/column counts and headers

Supports CSV, XLSX, XLSM, and XLS formats. Automatically detects format based on file extension.""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the spreadsheet file to parse"
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum number of rows to parse. If not specified, all rows are parsed.",
                    "default": None
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: parse_spreadsheet_tool(
        file_path=args.get("file_path"),
        max_rows=args.get("max_rows"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_spreadsheet_requirements,
    requires_env=[],
)


registry.register(
    name="get_spreadsheet_info",
    toolset="document",
    schema={
        "name": "get_spreadsheet_info",
        "description": """Get basic information about a spreadsheet file without extracting full content.

Use this tool when you need to:
- Check the number of rows and columns
- Get sheet names (for Excel files)
- Get headers
- Verify a spreadsheet file is valid""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the spreadsheet file to get info from"
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: get_spreadsheet_info_tool(
        file_path=args.get("file_path"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_spreadsheet_requirements,
    requires_env=[],
)