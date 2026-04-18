#!/usr/bin/env python3
"""
DOCX Parser Tool Module

This module provides tools for extracting text content from Word (.docx) files.

Features:
- Text extraction from DOCX documents
- Paragraph and table extraction
- Metadata extraction (title, author, etc.)
- Error handling with user-friendly messages

Usage:
    from tools.docx_parser_tool import parse_docx_tool
    
    result = parse_docx_tool(file_path="/path/to/document.docx")
    if result["success"]:
        print(result["data"]["content"])
"""

import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

PYTHON_DOCX_AVAILABLE = importlib.util.find_spec("docx") is not None

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def check_docx_requirements() -> bool:
    """Check if the required dependencies for DOCX parsing are available."""
    if not PYTHON_DOCX_AVAILABLE:
        return False
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


def _get_docx():
    """Lazily import docx."""
    if not PYTHON_DOCX_AVAILABLE:
        raise ImportError(
            "python-docx is required for DOCX parsing. Install with: pip install python-docx"
        )
    from docx import Document
    return Document


def parse_docx_tool(
    file_path: str,
    extract_tables: bool = True,
    task_id: Optional[str] = None,
) -> str:
    """Parse a DOCX file and extract text content.
    
    Args:
        file_path: Path to the DOCX file to parse.
        extract_tables: Whether to extract table content.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and extracted content.
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not check_docx_requirements():
        return json.dumps({
            "success": False,
            "error": "DOCX parsing requires the python-docx library. Install with: pip install python-docx",
            "error_code": "MISSING_DEPENDENCY"
        })
    
    try:
        Document = _get_docx()
        doc = Document(file_path)
        
        paragraphs = []
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():
                paragraphs.append({
                    "index": i,
                    "text": para.text,
                    "style": para.style.name if para.style else None
                })
        
        text_parts = [f"--- Paragraph {p['index'] + 1} ---\n{p['text']}" for p in paragraphs]
        
        tables_data = []
        if extract_tables:
            for i, table in enumerate(doc.tables):
                table_rows = []
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells]
                    table_rows.append(row_cells)
                tables_data.append({
                    "index": i,
                    "rows": len(table.rows),
                    "columns": len(table.columns) if table.rows else 0,
                    "data": table_rows
                })
        
        core_props = None
        try:
            import docx.opc.constants
            core_props = docx.opc.constants
        except:
            pass
        
        return json.dumps({
            "success": True,
            "data": {
                "content": "\n\n".join(text_parts) if text_parts else "",
                "paragraphs": len(paragraphs),
                "tables": len(tables_data),
                "metadata": {
                    "paragraph_count": len(paragraphs),
                    "table_count": len(tables_data),
                }
            },
            "tables": tables_data if extract_tables else []
        })
        
    except Exception as e:
        logger.exception(f"Error parsing DOCX: {file_path}")
        error_str = str(e)
        
        if "password" in error_str.lower():
            return json.dumps({
                "success": False,
                "error": "DOCX is password-protected. Please provide an unprotected document.",
                "error_code": "PASSWORD_PROTECTED"
            })
        
        if "corrupt" in error_str.lower() or "invalid" in error_str.lower():
            return json.dumps({
                "success": False,
                "error": "DOCX file appears to be corrupt or invalid.",
                "error_code": "CORRUPT_FILE"
            })
        
        return json.dumps({
            "success": False,
            "error": f"Failed to parse DOCX: {error_str}",
            "error_code": "PARSE_ERROR"
        })


def get_docx_info_tool(
    file_path: str,
    task_id: Optional[str] = None,
) -> str:
    """Get basic information about a DOCX file without extracting full content.
    
    Args:
        file_path: Path to the DOCX file.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with DOCX metadata and structure info.
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not check_docx_requirements():
        return json.dumps({
            "success": False,
            "error": "DOCX parsing requires the python-docx library. Install with: pip install python-docx",
            "error_code": "MISSING_DEPENDENCY"
        })
    
    try:
        Document = _get_docx()
        doc = Document(file_path)
        
        paragraph_count = sum(1 for p in doc.paragraphs if p.text.strip())
        table_count = len(doc.tables)
        
        return json.dumps({
            "success": True,
            "data": {
                "file_name": Path(file_path).name,
                "file_path": str(Path(file_path).resolve()),
                "file_size_bytes": Path(file_path).stat().st_size,
                "paragraph_count": paragraph_count,
                "table_count": table_count,
                "paragraphs": paragraph_count,
                "tables": table_count,
            }
        })
        
    except Exception as e:
        logger.exception(f"Error getting DOCX info: {file_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "INFO_ERROR"
        })


registry.register(
    name="parse_docx",
    toolset="document",
    schema={
        "name": "parse_docx",
        "description": """Parse and extract text content from Word (.docx) files.

Use this tool when the user uploads a Word document and wants to:
- Extract text content for analysis
- Search for specific information in a document
- Summarize the document content
- Extract table data from the document

The tool returns the text content organized by paragraph, along with table data.""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the DOCX file to parse"
                },
                "extract_tables": {
                    "type": "boolean",
                    "description": "Whether to extract table content.",
                    "default": True
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: parse_docx_tool(
        file_path=args.get("file_path"),
        extract_tables=args.get("extract_tables", True),
        task_id=kw.get("task_id")
    ),
    check_fn=check_docx_requirements,
    requires_env=[],
)


registry.register(
    name="get_docx_info",
    toolset="document",
    schema={
        "name": "get_docx_info",
        "description": """Get basic information about a Word (.docx) file without extracting full content.

Use this tool when you need to:
- Check the number of paragraphs in a document
- Get document structure info
- Verify a DOCX file is valid
- Quick preview before full extraction""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the DOCX file to get info from"
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: get_docx_info_tool(
        file_path=args.get("file_path"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_docx_requirements,
    requires_env=[],
)