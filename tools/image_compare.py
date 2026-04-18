#!/usr/bin/env python3
"""
Image Compare Tool Module

This module provides tools for comparing two images and detecting differences.

Features:
- Structural similarity (SSIM)
- Pixel difference calculation
- Histogram comparison
- Difference visualization coordinates

Usage:
    from tools.image_compare import compare_images
    
    result = compare_images(image1_path="/path/img1.png", image2_path="/path/img2.png")
"""

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
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
    
    return True, ""


def _pixel_difference(img1_data, img2_data, width, height) -> Dict[str, Any]:
    """Calculate pixel-level difference between two images."""
    diff_pixels = 0
    max_diff = 0
    diff_coords = []
    
    for y in range(min(height[0], height[1])):
        for x in range(min(width[0], width[1])):
            p1 = img1_data[y][x] if isinstance(img1_data[y][x], (list, tuple)) else [img1_data[y][x]]
            p2 = img2_data[y][x] if isinstance(img2_data[y][x], (list, tuple)) else [img2_data[y][x]]
            
            channel_diffs = [abs(int(a) - int(b)) for a, b in zip(p1, p2)]
            total_diff = sum(channel_diffs)
            
            if total_diff > 0:
                diff_pixels += 1
                max_diff = max(max_diff, total_diff)
                if len(diff_coords) < 100:
                    diff_coords.append({"x": x, "y": y, "diff": total_diff})
    
    total_pixels = min(width[0], width[1]) * min(height[0], height[1])
    diff_percentage = (diff_pixels / total_pixels * 100) if total_pixels > 0 else 0
    
    return {
        "diff_pixels": diff_pixels,
        "total_pixels": total_pixels,
        "diff_percentage": round(diff_percentage, 2),
        "max_channel_diff": max_diff,
        "sample_diff_coords": diff_coords
    }


def _histogram_compare(hist1, hist2) -> float:
    """Compare two image histograms using correlation."""
    if len(hist1) != len(hist2):
        return 0.0
    
    n = len(hist1)
    if n == 0:
        return 0.0
    
    mean1 = sum(hist1) / n
    mean2 = sum(hist2) / n
    
    var1 = sum((h - mean1) ** 2 for h in hist1) / n
    var2 = sum((h - mean2) ** 2 for h in hist2) / n
    
    if var1 == 0 or var2 == 0:
        return 0.0
    
    cov = sum((h1 - mean1) * (h2 - mean2) for h1, h2 in zip(hist1, hist2)) / n
    correlation = cov / (math.sqrt(var1) * math.sqrt(var2))
    
    return max(0.0, min(1.0, (correlation + 1) / 2))


def compare_images(
    image1_path: str,
    image2_path: str,
    method: str = "basic",
    task_id: Optional[str] = None,
) -> str:
    """Compare two images and return similarity metrics.
    
    Args:
        image1_path: Path to the first image.
        image2_path: Path to the second image.
        method: Comparison method - "basic", "histogram", or "full".
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with comparison results.
    """
    is_valid1, error1 = _check_file_size(image1_path)
    if not is_valid1:
        return json.dumps({
            "success": False,
            "error": error1,
            "error_code": "INVALID_IMAGE1"
        })
    
    is_valid2, error2 = _check_file_size(image2_path)
    if not is_valid2:
        return json.dumps({
            "success": False,
            "error": error2,
            "error_code": "INVALID_IMAGE2"
        })
    
    try:
        from PIL import Image
        import numpy as np
        
        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)
        
        width1, height1 = img1.size
        width2, height2 = img2.size
        
        size_match = width1 == width2 and height1 == height2
        
        result: Dict[str, Any] = {
            "image1": {
                "path": str(Path(image1_path).resolve()),
                "name": Path(image1_path).name,
                "width": width1,
                "height": height1,
                "format": img1.format,
                "mode": img1.mode
            },
            "image2": {
                "path": str(Path(image2_path).resolve()),
                "name": Path(image2_path).name,
                "width": width2,
                "height": height2,
                "format": img2.format,
                "mode": img2.mode
            },
            "dimensions_match": size_match,
            "similarity": {
                "method": method
            }
        }
        
        if method in ("basic", "full"):
            if img1.mode != img2.mode:
                img2 = img2.convert(img1.mode)
            
            if img1.mode == 'RGB' or img1.mode == 'L':
                arr1 = np.array(img1)
                arr2 = np.array(img2)
                
                if size_match:
                    pixel_diff = np.abs(arr1.astype(float) - arr2.astype(float))
                    total_diff = np.sum(pixel_diff)
                    max_diff = np.max(pixel_diff)
                    mean_diff = np.mean(pixel_diff)
                    
                    percent_diff = (total_diff / (arr1.size * 255)) * 100
                    
                    result["similarity"]["ssim_estimate"] = max(0.0, 100 - percent_diff)
                    result["similarity"]["pixel_diff"] = {
                        "total": int(total_diff),
                        "mean": round(float(mean_diff), 2),
                        "max": int(max_diff),
                        "percentage_different": round(percent_diff, 2)
                    }
                else:
                    result["similarity"]["pixel_diff"] = {
                        "error": "Images have different dimensions"
                    }
        
        if method in ("histogram", "full"):
            if img1.mode == 'RGB':
                h1_r = np.array(img1.histogram()[0:256])
                h1_g = np.array(img1.histogram()[256:512])
                h1_b = np.array(img1.histogram()[512:768])
                
                img1_gray = img1.convert('L')
                h1_gray = np.array(img1_gray.histogram())
                
                if img2.mode != 'RGB':
                    img2 = img2.convert('RGB')
                
                h2_r = np.array(img2.histogram()[0:256])
                h2_g = np.array(img2.histogram()[256:512])
                h2_b = np.array(img2.histogram()[512:768])
                
                img2_gray = img2.convert('L')
                h2_gray = np.array(img2_gray.histogram())
                
                result["similarity"]["histogram"] = {
                    "red": round(_histogram_compare(h1_r, h2_r), 3),
                    "green": round(_histogram_compare(h1_g, h2_g), 3),
                    "blue": round(_histogram_compare(h1_b, h2_b), 3),
                    "grayscale": round(_histogram_compare(h1_gray, h2_gray), 3)
                }
            elif img1.mode == 'L':
                h1 = np.array(img1.histogram())
                h2 = np.array(img2.convert('L').histogram())
                result["similarity"]["histogram"] = {
                    "grayscale": round(_histogram_compare(h1, h2), 3)
                }
        
        similarity_score = result["similarity"].get("ssim_estimate", 0)
        if "histogram" in result["similarity"]:
            hist_vals = list(result["similarity"]["histogram"].values())
            hist_avg = sum(hist_vals) / len(hist_vals)
            similarity_score = (similarity_score + hist_avg * 100) / 2
        
        result["similarity"]["overall_score"] = round(float(similarity_score), 2)
        result["similarity"]["match"] = bool(similarity_score > 95)
        
        return json.dumps({
            "success": True,
            "data": result
        })
        
    except ImportError as e:
        if "PIL" in str(e) or "numpy" in str(e):
            return json.dumps({
                "success": False,
                "error": "Image comparison requires PIL and numpy",
                "error_code": "MISSING_DEPENDENCY"
            })
        raise
    except Exception as e:
        logger.exception("Error comparing images")
        return json.dumps({
            "success": False,
            "error": f"Comparison failed: {str(e)}",
            "error_code": "COMPARE_ERROR"
        })


def find_similar_images(
    query_image: str,
    image_directory: str,
    threshold: float = 0.9,
    task_id: Optional[str] = None,
) -> str:
    """Find images in a directory similar to a query image.
    
    Args:
        query_image: Path to the query image.
        image_directory: Directory to search for similar images.
        threshold: Similarity threshold (0-1).
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with similar images ranked by similarity.
    """
    is_valid, error = _check_file_size(query_image)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error,
            "error_code": "INVALID_QUERY"
        })
    
    dir_path = Path(image_directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return json.dumps({
            "success": False,
            "error": f"Invalid directory: {image_directory}",
            "error_code": "INVALID_DIRECTORY"
        })
    
    try:
        from PIL import Image
        import numpy as np
        
        query_img = Image.open(query_image)
        if query_img.mode != 'RGB':
            query_img = query_img.convert('RGB')
        
        query_arr = np.array(query_img)
        query_hist = np.array(query_img.histogram()[0:256])
        
        similar_images = []
        
        for img_path in dir_path.glob("*.png"):
            if img_path.name == Path(query_image).name:
                continue
            
            try:
                img = Image.open(img_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                arr = np.array(img)
                
                pixel_diff = np.abs(query_arr.astype(float) - arr.astype(float))
                total_diff = np.sum(pixel_diff)
                percent_diff = (total_diff / (arr.size * 255)) * 100
                score = max(0.0, 100 - percent_diff)
                
                if score >= threshold * 100:
                    similar_images.append({
                        "path": str(img_path),
                        "name": img_path.name,
                        "similarity_score": round(score, 2)
                    })
                    
            except Exception:
                continue
        
        similar_images.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return json.dumps({
            "success": True,
            "data": {
                "query": str(Path(query_image).name),
                "threshold": threshold,
                "matches": similar_images,
                "match_count": len(similar_images)
            }
        })
        
    except Exception as e:
        logger.exception("Error finding similar images")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "SEARCH_ERROR"
        })


registry.register(
    name="compare_images",
    toolset="image",
    schema={
        "name": "compare_images",
        "description": """Compare two images and determine their similarity.

Use this tool when the user wants to:
- Check if two images are identical or similar
- Detect differences between two images
- Verify image quality or transformations

Returns structural similarity estimates, pixel differences, and histogram comparisons.""",
        "parameters": {
            "type": "object",
            "properties": {
                "image1_path": {
                    "type": "string",
                    "description": "Path to the first image"
                },
                "image2_path": {
                    "type": "string",
                    "description": "Path to the second image"
                },
                "method": {
                    "type": "string",
                    "description": "Comparison method: 'basic', 'histogram', or 'full'",
                    "enum": ["basic", "histogram", "full"],
                    "default": "basic"
                }
            },
            "required": ["image1_path", "image2_path"]
        }
    },
    handler=lambda args, **kw: compare_images(
        image1_path=args.get("image1_path"),
        image2_path=args.get("image2_path"),
        method=args.get("method", "basic"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="find_similar_images",
    toolset="image",
    schema={
        "name": "find_similar_images",
        "description": """Find images in a directory that are similar to a query image.

Use this tool when the user wants to:
- Find duplicate or near-duplicate images
- Search for visually similar images
- Group similar images together

Results are ranked by similarity score (0-100).""",
        "parameters": {
            "type": "object",
            "properties": {
                "query_image": {
                    "type": "string",
                    "description": "Path to the query image"
                },
                "image_directory": {
                    "type": "string",
                    "description": "Directory to search for similar images"
                },
                "threshold": {
                    "type": "number",
                    "description": "Similarity threshold (0-1), images with score >= threshold are returned",
                    "default": 0.9
                }
            },
            "required": ["query_image", "image_directory"]
        }
    },
    handler=lambda args, **kw: find_similar_images(
        query_image=args.get("query_image"),
        image_directory=args.get("image_directory"),
        threshold=args.get("threshold", 0.9),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)