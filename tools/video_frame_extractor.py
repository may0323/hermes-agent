#!/usr/bin/env python3
"""
Video Frame Extractor Tool Module

This module provides tools for extracting frames from video files.

Features:
- Extract single or multiple frames from videos
- Support for common video formats
- Frame timestamp metadata
- Configurable output format

Usage:
    from tools.video_frame_extractor import extract_frame_tool
    
    result = extract_frame_tool(video_path="/path/to/video.mp4", timestamp=5.0)
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}


def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available on the system."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _check_file_size(file_path: str) -> tuple[bool, str]:
    """Check if file size is within limits."""
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}"
    if not path.is_file():
        return False, f"Not a file: {file_path}"
    
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        return False, f"Unsupported format: {suffix}. Supported: {', '.join(SUPPORTED_FORMATS)}"
    
    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File too large: {size / (1024*1024):.1f}MB (max: {MAX_FILE_SIZE_MB}MB)"
    
    return True, ""


def _get_video_info(video_path: str) -> Dict[str, Any]:
    """Get video metadata using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Error getting video info: {e}")
        return {}


def extract_frame_tool(
    video_path: str,
    timestamp: float = 0.0,
    output_path: Optional[str] = None,
    format: str = "png",
    task_id: Optional[str] = None,
) -> str:
    """Extract a single frame from a video at a specific timestamp.
    
    Args:
        video_path: Path to the video file.
        timestamp: Timestamp in seconds where to extract the frame.
        output_path: Optional path to save the extracted frame. If not provided, returns base64.
        format: Output format (png, jpg).
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and frame data.
    """
    is_valid, error_msg = _check_file_size(video_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not check_ffmpeg_available():
        return json.dumps({
            "success": False,
            "error": "FFmpeg is not installed. Please install FFmpeg to use this tool.",
            "error_code": "FFMPEG_NOT_AVAILABLE"
        })
    
    try:
        if output_path is None:
            output_path = f"/tmp/frame_{Path(video_path).stem}_{timestamp}.{format}"
        
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            output_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "error": f"Failed to extract frame: {result.stderr}",
                "error_code": "EXTRACTION_FAILED"
            })
        
        output_path_obj = Path(output_path)
        if not output_path_obj.exists():
            return json.dumps({
                "success": False,
                "error": "Frame file was not created",
                "error_code": "FILE_NOT_CREATED"
            })
        
        video_info = _get_video_info(video_path)
        duration = 0
        if video_info.get('format', {}).get('duration'):
            duration = float(video_info['format']['duration'])
        
        return json.dumps({
            "success": True,
            "data": {
                "frame_path": str(output_path),
                "timestamp": timestamp,
                "format": format,
                "video_duration": duration,
                "file_size_bytes": output_path_obj.stat().st_size
            }
        })
        
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Frame extraction timed out",
            "error_code": "TIMEOUT"
        })
    except Exception as e:
        logger.exception(f"Error extracting frame from: {video_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "EXTRACTION_ERROR"
        })


def extract_multiple_frames_tool(
    video_path: str,
    timestamps: List[float],
    output_dir: Optional[str] = None,
    format: str = "png",
    task_id: Optional[str] = None,
) -> str:
    """Extract multiple frames from a video at specific timestamps.
    
    Args:
        video_path: Path to the video file.
        timestamps: List of timestamps in seconds.
        output_dir: Directory to save extracted frames.
        format: Output format (png, jpg).
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with success status and frame data for each timestamp.
    """
    is_valid, error_msg = _check_file_size(video_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    if not check_ffmpeg_available():
        return json.dumps({
            "success": False,
            "error": "FFmpeg is not installed",
            "error_code": "FFMPEG_NOT_AVAILABLE"
        })
    
    if not timestamps:
        return json.dumps({
            "success": False,
            "error": "No timestamps provided",
            "error_code": "EMPTY_INPUT"
        })
    
    if len(timestamps) > 20:
        return json.dumps({
            "success": False,
            "error": "Cannot extract more than 20 frames at once",
            "error_code": "TOO_MANY_FRAMES"
        })
    
    try:
        if output_dir is None:
            output_dir = f"/tmp/frames_{Path(video_path).stem}"
        
        output_path_obj = Path(output_dir)
        output_path_obj.mkdir(parents=True, exist_ok=True)
        
        video_info = _get_video_info(video_path)
        duration = 0
        if video_info.get('format', {}).get('duration'):
            duration = float(video_info['format']['duration'])
        
        frames = []
        successful = 0
        failed = 0
        
        for ts in timestamps:
            frame_path = output_path_obj / f"frame_{ts}.{format}"
            
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(ts),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                str(frame_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and frame_path.exists():
                frames.append({
                    "timestamp": ts,
                    "frame_path": str(frame_path),
                    "success": True
                })
                successful += 1
            else:
                frames.append({
                    "timestamp": ts,
                    "success": False,
                    "error": result.stderr[:200] if result.stderr else "Unknown error"
                })
                failed += 1
        
        return json.dumps({
            "success": True,
            "data": {
                "frames": frames,
                "total": len(timestamps),
                "successful": successful,
                "failed": failed,
                "video_duration": duration
            }
        })
        
    except Exception as e:
        logger.exception(f"Error extracting frames from: {video_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "EXTRACTION_ERROR"
        })


def get_video_info_tool(
    video_path: str,
    task_id: Optional[str] = None,
) -> str:
    """Get information about a video file.
    
    Args:
        video_path: Path to the video file.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with video metadata.
    """
    is_valid, error_msg = _check_file_size(video_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    try:
        video_info = _get_video_info(video_path)
        
        if not video_info:
            return json.dumps({
                "success": False,
                "error": "Could not read video info",
                "error_code": "INFO_ERROR"
            })
        
        format_info = video_info.get('format', {})
        video_stream = None
        audio_stream = None
        
        for stream in video_info.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
            elif stream.get('codec_type') == 'audio':
                audio_stream = stream
        
        result = {
            "file_name": Path(video_path).name,
            "file_path": str(Path(video_path).resolve()),
            "file_size_bytes": Path(video_path).stat().st_size,
            "duration": float(format_info.get('duration', 0)),
            "format": format_info.get('format_name', 'unknown')
        }
        
        if video_stream:
            result["video"] = {
                "codec": video_stream.get('codec_name', 'unknown'),
                "width": video_stream.get('width', 0),
                "height": video_stream.get('height', 0),
                "fps": eval(video_stream.get('r_frame_rate', '0/1')) if video_stream.get('r_frame_rate') else 0,
                "bitrate": int(video_stream.get('bit_rate', 0))
            }
        
        if audio_stream:
            result["audio"] = {
                "codec": audio_stream.get('codec_name', 'unknown'),
                "sample_rate": int(audio_stream.get('sample_rate', 0)),
                "channels": audio_stream.get('channels', 0)
            }
        
        return json.dumps({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.exception(f"Error getting video info: {video_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "INFO_ERROR"
        })


registry.register(
    name="extract_video_frame",
    toolset="video",
    schema={
        "name": "extract_video_frame",
        "description": """Extract a single frame from a video at a specific timestamp.

Use this tool when the user wants to:
- Capture a screenshot from a video at a specific time
- Extract a frame for analysis or thumbnail
- Get a snapshot from a specific moment

Requires FFmpeg to be installed on the system.""",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file"
                },
                "timestamp": {
                    "type": "number",
                    "description": "Timestamp in seconds where to extract the frame",
                    "default": 0.0
                },
                "output_path": {
                    "type": "string",
                    "description": "Optional path to save the extracted frame",
                    "default": None
                },
                "format": {
                    "type": "string",
                    "description": "Output format (png or jpg)",
                    "default": "png"
                }
            },
            "required": ["video_path"]
        }
    },
    handler=lambda args, **kw: extract_frame_tool(
        video_path=args.get("video_path"),
        timestamp=args.get("timestamp", 0.0),
        output_path=args.get("output_path"),
        format=args.get("format", "png"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ffmpeg_available,
    requires_env=["FFmpeg"],
)


registry.register(
    name="extract_multiple_video_frames",
    toolset="video",
    schema={
        "name": "extract_multiple_video_frames",
        "description": """Extract multiple frames from a video at specific timestamps.

Use this tool when the user wants to:
- Extract several key frames from a video
- Create a storyboard or preview sequence
- Capture multiple moments for analysis

Maximum 20 frames per request. Requires FFmpeg.""",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file"
                },
                "timestamps": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "List of timestamps in seconds"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Directory to save extracted frames",
                    "default": None
                },
                "format": {
                    "type": "string",
                    "description": "Output format (png or jpg)",
                    "default": "png"
                }
            },
            "required": ["video_path", "timestamps"]
        }
    },
    handler=lambda args, **kw: extract_multiple_frames_tool(
        video_path=args.get("video_path"),
        timestamps=args.get("timestamps", []),
        output_dir=args.get("output_dir"),
        format=args.get("format", "png"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ffmpeg_available,
    requires_env=["FFmpeg"],
)


registry.register(
    name="get_video_info",
    toolset="video",
    schema={
        "name": "get_video_info",
        "description": """Get information and metadata about a video file.

Use this tool when you need to:
- Get video duration, resolution, codec
- Check video format and bitrate
- Verify video file is valid before processing

Returns detailed stream information including video and audio codecs.""",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file"
                }
            },
            "required": ["video_path"]
        }
    },
    handler=lambda args, **kw: get_video_info_tool(
        video_path=args.get("video_path"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)