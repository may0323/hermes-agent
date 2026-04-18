#!/usr/bin/env python3
"""
Batch Image Analyze Tool Module

This module provides tools for batch processing and analyzing multiple images.

Features:
- Batch image analysis
- Concurrent processing
- Result aggregation
- Progress tracking

Usage:
    from tools.image_batch_analyze import batch_analyze_images
    
    result = batch_analyze_images(file_paths=["/path/img1.png", "/path/img2.jpg"])
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from tools.registry import registry

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_BATCH_SIZE = 20
SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif', '.webp'}


def _check_file_size(file_path: str) -> tuple[bool, str]:
    """Check if file size is within limits."""
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}"
    if not path.is_file():
        return False, f"Not a file: {file_path}"
    
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        return False, f"Unsupported format: {suffix}"
    
    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File too large: {size / (1024*1024):.1f}MB"
    
    if size == 0:
        return False, "File is empty"
    
    return True, ""


def _analyze_single_image(file_path: str, task_id: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a single image and return result."""
    is_valid, error_msg = _check_file_size(file_path)
    if not is_valid:
        return {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "success": False,
            "error": error_msg
        }
    
    try:
        from PIL import Image
        
        img = Image.open(file_path)
        width, height = img.size
        format_name = img.format
        
        result = {
            "file_path": str(Path(file_path).resolve()),
            "file_name": Path(file_path).name,
            "success": True,
            "data": {
                "width": width,
                "height": height,
                "format": format_name or "UNKNOWN",
                "mode": img.mode,
                "size_bytes": Path(file_path).stat().st_size
            }
        }
        
        if img.mode == 'RGB':
            result["data"]["color_channels"] = 3
        elif img.mode == 'RGBA':
            result["data"]["color_channels"] = 4
        elif img.mode == 'L':
            result["data"]["color_channels"] = 1
        else:
            result["data"]["color_channels"] = len(img.getbands())
        
        return result
        
    except Exception as e:
        logger.exception(f"Error analyzing image: {file_path}")
        return {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "success": False,
            "error": str(e)
        }


def batch_analyze_images(
    file_paths: List[str],
    max_workers: Optional[int] = None,
    task_id: Optional[str] = None,
) -> str:
    """Analyze multiple images in batch.
    
    Args:
        file_paths: List of image file paths to analyze.
        max_workers: Maximum number of concurrent workers. Defaults to 4.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with batch analysis results.
    """
    if not file_paths:
        return json.dumps({
            "success": False,
            "error": "No file paths provided",
            "error_code": "EMPTY_INPUT"
        })
    
    if len(file_paths) > MAX_BATCH_SIZE:
        return json.dumps({
            "success": False,
            "error": f"Batch size exceeds maximum of {MAX_BATCH_SIZE} files",
            "error_code": "BATCH_TOO_LARGE"
        })
    
    max_workers = max_workers or 4
    
    results = []
    successful = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(_analyze_single_image, fp, task_id): fp 
            for fp in file_paths
        }
        
        for future in as_completed(future_to_path):
            result = future.result()
            if result["success"]:
                successful += 1
            else:
                failed += 1
            results.append(result)
    
    results.sort(key=lambda x: x["file_name"])
    
    return json.dumps({
        "success": True,
        "data": {
            "results": results,
            "total": len(file_paths),
            "successful": successful,
            "failed": failed,
            "summary": {
                "total_files": len(file_paths),
                "analyzed": successful,
                "failed": failed
            }
        }
    })


def batch_analyze_directory(
    directory: str,
    pattern: str = "*.png",
    recursive: bool = False,
    max_files: Optional[int] = None,
    task_id: Optional[str] = None,
) -> str:
    """Analyze all images in a directory that match a glob pattern.
    
    Args:
        directory: Path to the directory to scan.
        pattern: Glob pattern for matching files (e.g., "*.png", "*.jpg").
        recursive: Whether to search subdirectories recursively.
        max_files: Maximum number of files to process.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with batch analysis results.
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return json.dumps({
            "success": False,
            "error": f"Directory not found: {directory}",
            "error_code": "INVALID_PATH"
        })
    
    if not dir_path.is_dir():
        return json.dumps({
            "success": False,
            "error": f"Not a directory: {directory}",
            "error_code": "NOT_A_DIRECTORY"
        })
    
    glob_func = dir_path.rglob if recursive else dir_path.glob
    matching_files = list(glob_func(pattern))
    
    if not matching_files:
        return json.dumps({
            "success": False,
            "error": f"No files matching pattern '{pattern}' found in {directory}",
            "error_code": "NO_FILES_FOUND"
        })
    
    if max_files:
        matching_files = matching_files[:max_files]
    
    file_paths = [str(f) for f in matching_files]
    
    return batch_analyze_images(file_paths=file_paths, task_id=task_id)


registry.register(
    name="batch_analyze_images",
    toolset="image",
    schema={
        "name": "batch_analyze_images",
        "description": """Analyze multiple images in batch.

Use this tool when the user wants to:
- Get metadata (dimensions, format, size) for multiple images at once
- Process a batch of images concurrently
- Scan a directory for image files and analyze them

Results are returned sorted by filename for easy correlation.
Supports PNG, JPG, JPEG, TIFF, BMP, GIF, and WebP formats.""",
        "parameters": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of image file paths to analyze"
                },
                "max_workers": {
                    "type": "integer",
                    "description": "Maximum concurrent workers. Defaults to 4.",
                    "default": 4
                }
            },
            "required": ["file_paths"]
        }
    },
    handler=lambda args, **kw: batch_analyze_images(
        file_paths=args.get("file_paths", []),
        max_workers=args.get("max_workers"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="batch_analyze_directory",
    toolset="image",
    schema={
        "name": "batch_analyze_directory",
        "description": """Analyze all images in a directory that match a glob pattern.

Use this tool when the user wants to:
- Scan a folder for images and analyze them all
- Process images matching a specific pattern (e.g., "*.png")
- Recursively analyze images in subdirectories

Maximum batch size is 20 files per request.""",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the directory to scan"
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern for matching files",
                    "default": "*.png"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Search subdirectories recursively",
                    "default": False
                },
                "max_files": {
                    "type": "integer",
                    "description": "Maximum number of files to process",
                    "default": None
                }
            },
            "required": ["directory"]
        }
    },
    handler=lambda args, **kw: batch_analyze_directory(
        directory=args.get("directory"),
        pattern=args.get("pattern", "*.png"),
        recursive=args.get("recursive", False),
        max_files=args.get("max_files"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)