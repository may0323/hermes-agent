#!/usr/bin/env python3
"""
PDF Parser Tool Module

This module provides tools for extracting text content and metadata from PDF files.

Features:
- Text extraction from PDF documents
- Metadata extraction (title, author, pages, etc.)
- Support for password-protected PDFs
- Configurable page limits
- Error handling with user-friendly messages

Usage:
    from tools.pdf_parser_tool import parse_pdf_tool
    
    result = parse_pdf_tool(file_path="/path/to/document.pdf")
    if result["success"]:
        print(result["data"]["content"])
"""

import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

PYPDF_AVAILABLE = importlib.util.find_spec("pypdf") is not None

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def check_pdf_requirements() -> bool:
    """Check if the required dependencies for PDF parsing are available."""
    if not PYPDF_AVAILABLE:
        return False
    return True


def _get_pypdf():
    """Lazily import pypdf."""
    if not PYPDF_AVAILABLE:
        raise ImportError(
            "pypdf is required for PDF parsing. Install with: pip install pypdf"
        )
    from pypdf import PdfReader
    return PdfReader


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


def parse_pdf_tool(
    file_path: str,
    max_pages: Optional[int] = None,
    extract_metadata: bool = True,
    task_id: Optional[str] = None,
) -> str:
    """Parse a PDF file and extract text content.
    
    Args:
        file_path: Path to the PDF file to parse.
        max_pages: Maximum number of pages to parse. If None, all pages are parsed.
        extract_metadata: Whether to extract metadata (title, author, etc.).
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and extracted content.
    
    Example:
        >>> result = parse_pdf_tool("/path/to/document.pdf")
        >>> data = json.loads(result)
        >>> if data["success"]:
        ...     print(data["data"]["content"])
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not check_pdf_requirements():
        return json.dumps({
            "success": False,
            "error": "PDF parsing requires the pypdf library. Install with: pip install pypdf",
            "error_code": "MISSING_DEPENDENCY"
        })
    
    try:
        PdfReader = _get_pypdf()
        reader = PdfReader(file_path)
        
        result_data: Dict[str, Any] = {
            "content": "",
            "metadata": {},
            "content_type": "text"
        }
        
        if extract_metadata:
            metadata = reader.metadata
            if metadata:
                result_data["metadata"] = {
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "subject": metadata.get("/Subject", ""),
                    "creator": metadata.get("/Creator", ""),
                    "producer": metadata.get("/Producer", ""),
                    "creation_date": str(metadata.get("/CreationDate", "")),
                    "modification_date": str(metadata.get("/ModDate", "")),
                }
        
        num_pages = len(reader.pages)
        result_data["metadata"]["pages"] = num_pages
        result_data["metadata"]["page_count"] = num_pages
        
        pages_to_read = min(max_pages, num_pages) if max_pages else num_pages
        
        PARALLEL_PAGE_THRESHOLD = 10
        if pages_to_read >= PARALLEL_PAGE_THRESHOLD:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def extract_page(i):
                page = reader.pages[i]
                text = page.extract_text()
                return (i, text)
            
            text_parts = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(extract_page, i) for i in range(pages_to_read)]
                for future in as_completed(futures):
                    idx, text = future.result()
                    if text:
                        text_parts.append(f"--- Page {idx+1} ---\n{text}")
            
            text_parts.sort(key=lambda x: int(x.split("--- Page ")[1].split(" ")[0]) - 1)
        else:
            text_parts = []
            for i in range(pages_to_read):
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    text_parts.append(f"--- Page {i+1} ---\n{text}")
        
        result_data["content"] = "\n\n".join(text_parts)
        result_data["metadata"]["pages_read"] = pages_to_read
        
        if max_pages and num_pages > max_pages:
            result_data["metadata"]["truncated"] = True
            result_data["metadata"]["total_pages"] = num_pages
        
        return json.dumps({
            "success": True,
            "data": result_data
        })
        
    except Exception as e:
        logger.exception(f"Error parsing PDF: {file_path}")
        error_str = str(e)
        
        if "password" in error_str.lower():
            return json.dumps({
                "success": False,
                "error": "PDF is password-protected. Please provide an unprotected PDF.",
                "error_code": "PASSWORD_PROTECTED"
            })
        
        if "encrypted" in error_str.lower():
            return json.dumps({
                "success": False,
                "error": "PDF is encrypted. Please provide an unencrypted PDF.",
                "error_code": "ENCRYPTED"
            })
        
        return json.dumps({
            "success": False,
            "error": f"Failed to parse PDF: {error_str}",
            "error_code": "PARSE_ERROR"
        })


def get_pdf_info_tool(
    file_path: str,
    task_id: Optional[str] = None,
) -> str:
    """Get basic information about a PDF file without extracting full content.
    
    Args:
        file_path: Path to the PDF file.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with PDF metadata and page count.
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not check_pdf_requirements():
        return json.dumps({
            "success": False,
            "error": "PDF parsing requires the pypdf library. Install with: pip install pypdf",
            "error_code": "MISSING_DEPENDENCY"
        })
    
    try:
        PdfReader = _get_pypdf()
        reader = PdfReader(file_path)
        
        metadata = reader.metadata or {}
        
        return json.dumps({
            "success": True,
            "data": {
                "file_name": Path(file_path).name,
                "file_path": str(Path(file_path).resolve()),
                "file_size_bytes": Path(file_path).stat().st_size,
                "pages": len(reader.pages),
                "metadata": {
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "subject": metadata.get("/Subject", ""),
                    "creator": metadata.get("/Creator", ""),
                    "producer": metadata.get("/Producer", ""),
                    "is_encrypted": reader.is_encrypted,
                }
            }
        })
        
    except Exception as e:
        logger.exception(f"Error getting PDF info: {file_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "INFO_ERROR"
        })


registry.register(
    name="parse_pdf",
    toolset="document",
    schema={
        "name": "parse_pdf",
        "description": """Parse and extract text content from PDF files.

Use this tool when the user uploads a PDF document and wants to:
- Extract text content for analysis
- Search for specific information in a PDF
- Summarize the PDF content
- Extract metadata (title, author, pages)

The tool returns the full text content organized by page, along with metadata.
If the PDF is password-protected or encrypted, an error will be returned.""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file to parse"
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum number of pages to parse. If not specified, all pages are parsed.",
                    "default": None
                },
                "extract_metadata": {
                    "type": "boolean",
                    "description": "Whether to extract metadata (title, author, etc.).",
                    "default": True
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: parse_pdf_tool(
        file_path=args.get("file_path"),
        max_pages=args.get("max_pages"),
        extract_metadata=args.get("extract_metadata", True),
        task_id=kw.get("task_id")
    ),
    check_fn=check_pdf_requirements,
    requires_env=[],
)


registry.register(
    name="get_pdf_info",
    toolset="document",
    schema={
        "name": "get_pdf_info",
        "description": """Get basic information about a PDF file without extracting full content.

Use this tool when you need to:
- Check the number of pages in a PDF
- Get PDF metadata (title, author, etc.)
- Verify a PDF file is valid
- Check if a PDF is encrypted

This tool is faster than parse_pdf as it doesn't extract the full text content.""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file to get info from"
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: get_pdf_info_tool(
        file_path=args.get("file_path"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_pdf_requirements,
    requires_env=[],
)
