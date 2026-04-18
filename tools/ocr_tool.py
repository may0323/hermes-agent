#!/usr/bin/env python3
"""
OCR Tool Module

This module provides tools for optical character recognition (OCR) from images.

Features:
- Text extraction from images
- Multi-language support (English, Chinese, etc.)
- Layout preservation
- Confidence scores
- Bounding box extraction

Usage:
    from tools.ocr_tool import ocr_image_tool
    
    result = ocr_image_tool(file_path="/path/to/image.png")
    if result["success"]:
        print(result["data"]["text"])
"""

import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

PYTESSERACT_AVAILABLE = importlib.util.find_spec("pytesseract") is not None
PIL_AVAILABLE = importlib.util.find_spec("PIL") is not None or importlib.util.find_spec("pillow") is not None

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif', '.webp'}


def check_ocr_requirements() -> bool:
    """Check if the required dependencies for OCR are available."""
    if not PYTESSERACT_AVAILABLE:
        return False
    if not PIL_AVAILABLE:
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
    
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        return False, f"Unsupported image format: {suffix}. Supported: {', '.join(SUPPORTED_FORMATS)}"
    
    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File too large: {size / (1024*1024):.1f}MB (max: {MAX_FILE_SIZE_MB}MB)"
    
    if size == 0:
        return False, "File is empty"
    
    return True, ""


def _get_pytesseract():
    """Lazily import pytesseract."""
    if not PYTESSERACT_AVAILABLE:
        raise ImportError(
            "pytesseract is required for OCR. Install with: pip install pytesseract"
        )
    import pytesseract
    return pytesseract


def _get_pil_image():
    """Lazily import PIL Image."""
    from PIL import Image
    return Image


def ocr_image_tool(
    file_path: str,
    language: Optional[str] = None,
    preserve_layout: bool = True,
    get_confidence: bool = False,
    task_id: Optional[str] = None,
) -> str:
    """Extract text from an image using OCR.
    
    Args:
        file_path: Path to the image file to OCR.
        language: Language code for OCR (e.g., 'eng', 'chi_sim', 'jpn').
                  If None, uses default (English).
        preserve_layout: Whether to try to preserve the layout structure.
        get_confidence: Whether to include confidence scores.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and extracted text.
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not check_ocr_requirements():
        return json.dumps({
            "success": False,
            "error": "OCR requires pytesseract and PIL. Install with: pip install pytesseract pillow",
            "error_code": "MISSING_DEPENDENCY"
        })
    
    try:
        pytesseract = _get_pytesseract()
        Image = _get_pil_image()
        
        img = Image.open(file_path)
        
        config = ""
        if language:
            config = f"-l {language}"
        
        if preserve_layout:
            config += " --psm 6"
        else:
            config += " --psm 3"
        
        text = pytesseract.image_to_string(img, config=config.strip())
        
        result_data: Dict[str, Any] = {
            "text": text,
            "language": language or "eng",
            "layout_preserved": preserve_layout
        }
        
        if get_confidence:
            data = pytesseract.image_to_data(img, config=config.strip(), output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data.get('conf', []) if conf != '-1']
            if confidences:
                result_data["confidence"] = sum(confidences) / len(confidences)
                result_data["avg_confidence"] = round(sum(confidences) / len(confidences), 2)
            else:
                result_data["confidence"] = 0
                result_data["avg_confidence"] = 0.0
        
        return json.dumps({
            "success": True,
            "data": result_data
        })
        
    except Exception as e:
        logger.exception(f"Error performing OCR on: {file_path}")
        error_str = str(e)
        
        if "tesseract" in error_str.lower() and "not found" in error_str.lower():
            return json.dumps({
                "success": False,
                "error": "Tesseract OCR engine not found. Please install Tesseract on your system.",
                "error_code": "TESSERACT_NOT_INSTALLED"
            })
        
        if "language" in error_str.lower():
            return json.dumps({
                "success": False,
                "error": f"OCR language not supported: {language}",
                "error_code": "UNSUPPORTED_LANGUAGE"
            })
        
        return json.dumps({
            "success": False,
            "error": f"OCR failed: {error_str}",
            "error_code": "OCR_ERROR"
        })


def ocr_pdf_tool(
    file_path: str,
    language: Optional[str] = None,
    max_pages: Optional[int] = None,
    task_id: Optional[str] = None,
) -> str:
    """Extract text from a PDF using OCR (for scanned PDFs).
    
    Args:
        file_path: Path to the PDF file.
        language: Language code for OCR.
        max_pages: Maximum number of pages to OCR.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and extracted text.
    """
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not check_ocr_requirements():
        return json.dumps({
            "success": False,
            "error": "OCR requires pytesseract and PIL.",
            "error_code": "MISSING_DEPENDENCY"
        })
    
    try:
        pytesseract = _get_pytesseract()
        Image = _get_pil_image()
        
        import subprocess
        result = subprocess.run(
            ['pdftoppm', '-png', '-f', '1', '-l', str(max_pages or 100), file_path, '/tmp/ocr_pdf_page'],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "error": "Failed to convert PDF to images. Is pdftoppm installed?",
                "error_code": "PDF_CONVERSION_ERROR"
            })
        
        from glob import glob
        page_files = sorted(glob('/tmp/ocr_pdf_page-*.png'))
        
        if max_pages:
            page_files = page_files[:max_pages]
        
        pages_text = []
        for i, page_file in enumerate(page_files):
            img = Image.open(page_file)
            config = f"-l {language or 'eng'} --psm 6"
            text = pytesseract.image_to_string(img, config=config)
            pages_text.append({
                "page": i + 1,
                "text": text.strip()
            })
        
        return json.dumps({
            "success": True,
            "data": {
                "pages": pages_text,
                "page_count": len(pages_text),
                "language": language or "eng"
            }
        })
        
    except FileNotFoundError as e:
        if "pdftoppm" in str(e):
            return json.dumps({
                "success": False,
                "error": "pdftoppm not found. Install poppler-utils for PDF OCR.",
                "error_code": "MISSING_UTILITY"
            })
        raise
    except Exception as e:
        logger.exception(f"Error performing OCR on PDF: {file_path}")
        return json.dumps({
            "success": False,
            "error": f"PDF OCR failed: {str(e)}",
            "error_code": "OCR_ERROR"
        })


def get_ocr_languages_tool(
    task_id: Optional[str] = None,
) -> str:
    """Get list of available OCR languages.
    
    Returns:
        JSON string with list of available language codes.
    """
    if not PYTESSERACT_AVAILABLE:
        return json.dumps({
            "success": False,
            "error": "pytesseract not available",
            "error_code": "MISSING_DEPENDENCY"
        })
    
    try:
        pytesseract = _get_pytesseract()
        languages = pytesseract.get_languages()
        
        common_languages = {
            "eng": "English",
            "chi_sim": "Chinese (Simplified)",
            "chi_tra": "Chinese (Traditional)",
            "jpn": "Japanese",
            "kor": "Korean",
            "spa": "Spanish",
            "fra": "French",
            "deu": "German",
            "ita": "Italian",
            "por": "Portuguese",
            "rus": "Russian",
            "ara": "Arabic",
        }
        
        available = []
        for lang in languages:
            name = common_languages.get(lang, lang)
            available.append({"code": lang, "name": name})
        
        return json.dumps({
            "success": True,
            "data": {
                "languages": available,
                "count": len(available)
            }
        })
        
    except Exception as e:
        logger.exception("Error getting OCR languages")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "ERROR"
        })


registry.register(
    name="ocr_image",
    toolset="image",
    schema={
        "name": "ocr_image",
        "description": """Extract text from images using Optical Character Recognition (OCR).

Use this tool when the user uploads an image containing text and wants to:
- Extract printed or handwritten text from images
- Read text from screenshots
- Extract text from scanned documents (use ocr_pdf for scanned PDFs)
- Process multi-language images

Supports many languages including English, Chinese, Japanese, Korean, and more.
For best results, use clear, high-resolution images.""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the image file to OCR"
                },
                "language": {
                    "type": "string",
                    "description": "Language code for OCR (e.g., 'eng', 'chi_sim', 'jpn'). If not specified, defaults to English.",
                    "default": "eng"
                },
                "preserve_layout": {
                    "type": "boolean",
                    "description": "Whether to preserve the layout structure of the text.",
                    "default": True
                },
                "get_confidence": {
                    "type": "boolean",
                    "description": "Whether to include confidence scores in the result.",
                    "default": False
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: ocr_image_tool(
        file_path=args.get("file_path"),
        language=args.get("language", "eng"),
        preserve_layout=args.get("preserve_layout", True),
        get_confidence=args.get("get_confidence", False),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ocr_requirements,
    requires_env=[],
)


registry.register(
    name="ocr_pdf",
    toolset="image",
    schema={
        "name": "ocr_pdf",
        "description": """Extract text from scanned PDFs using OCR.

Use this tool when the user uploads a scanned PDF (no selectable text) and wants to:
- Extract text from scanned document pages
- Process multi-page scanned documents
- Get both page numbers and extracted text

Note: Requires pdftoppm (poppler-utils) to be installed on the system.""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file to OCR"
                },
                "language": {
                    "type": "string",
                    "description": "Language code for OCR.",
                    "default": "eng"
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum number of pages to OCR. If not specified, all pages are processed.",
                    "default": None
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: ocr_pdf_tool(
        file_path=args.get("file_path"),
        language=args.get("language", "eng"),
        max_pages=args.get("max_pages"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ocr_requirements,
    requires_env=["PATH with pdftoppm"],
)


registry.register(
    name="get_ocr_languages",
    toolset="image",
    schema={
        "name": "get_ocr_languages",
        "description": """Get the list of available OCR languages supported by Tesseract.

Use this tool to check which languages are available for OCR operations.
Returns language codes and their full names.""",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    handler=lambda args, **kw: get_ocr_languages_tool(
        task_id=kw.get("task_id")
    ),
    check_fn=check_ocr_requirements,
    requires_env=[],
)