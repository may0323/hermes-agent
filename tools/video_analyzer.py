#!/usr/bin/env python3
"""
Video Analyzer Tool Module

This module provides tools for analyzing video content and generating summaries.

Features:
- Video content summarization
- Scene detection
- Motion analysis
- Text/subtitle extraction

Usage:
    from tools.video_analyzer import analyze_video_tool
    
    result = analyze_video_tool(video_path="/path/to/video.mp4")
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}


def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available."""
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
        return False, f"Unsupported format: {suffix}"
    
    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File too large: {size / (1024*1024):.1f}MB"
    
    return True, ""


def _get_video_metadata(video_path: str) -> Dict[str, Any]:
    """Get basic video metadata."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception:
        return {}


def analyze_video_tool(
    video_path: str,
    extract_scenes: bool = True,
    max_scenes: int = 10,
    task_id: Optional[str] = None,
) -> str:
    """Analyze a video and provide a summary.
    
    Args:
        video_path: Path to the video file.
        extract_scenes: Whether to detect scene changes.
        max_scenes: Maximum number of scenes to detect.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with video analysis results.
    """
    is_valid, error_msg = _check_file_size(video_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    try:
        video_info = _get_video_metadata(video_path)
        
        if not video_info:
            return json.dumps({
                "success": False,
                "error": "Could not analyze video",
                "error_code": "ANALYSIS_ERROR"
            })
        
        format_info = video_info.get('format', {})
        duration = float(format_info.get('duration', 0))
        file_size = int(format_info.get('size', 0))
        
        video_stream = None
        audio_stream = None
        for stream in video_info.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
            elif stream.get('codec_type') == 'audio':
                audio_stream = stream
        
        result: Dict[str, Any] = {
            "summary": {
                "duration_seconds": round(duration, 2),
                "duration_formatted": _format_duration(duration),
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "format": format_info.get('format_name', 'unknown')
            }
        }
        
        if video_stream:
            fps = video_stream.get('r_frame_rate', '0/1')
            fps_val = eval(fps) if fps else 0
            
            result["video"] = {
                "codec": video_stream.get('codec_name', 'unknown'),
                "resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                "width": video_stream.get('width', 0),
                "height": video_stream.get('height', 0),
                "fps": round(fps_val, 2) if fps_val else 0,
                "bitrate": int(video_stream.get('bit_rate', 0)),
                "pixel_format": video_stream.get('pix_fmt', 'unknown')
            }
            
            aspect_ratio = video_stream.get('display_aspect_ratio', '0:0')
            if aspect_ratio and aspect_ratio != '0:0':
                result["video"]["aspect_ratio"] = aspect_ratio
        
        if audio_stream:
            result["audio"] = {
                "codec": audio_stream.get('codec_name', 'unknown'),
                "sample_rate": int(audio_stream.get('sample_rate', 0)),
                "channels": audio_stream.get('channels', 0),
                "bitrate": int(audio_stream.get('bit_rate', 0))
            }
        
        if extract_scenes and duration > 0:
            scenes = _detect_scenes(video_path, max_scenes)
            result["scenes"] = scenes
        
        return json.dumps({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.exception(f"Error analyzing video: {video_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "ANALYSIS_ERROR"
        })


def _format_duration(seconds: float) -> str:
    """Format duration as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _detect_scenes(video_path: str, max_scenes: int) -> List[Dict[str, Any]]:
    """Detect scene changes in a video using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-select_scenes', '1',
            '-scene_list', '-',
            '-i', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            scenes = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        timestamp = float(parts[0])
                        scenes.append({
                            "timestamp": round(timestamp, 2),
                            "time_formatted": _format_duration(timestamp)
                        })
                        if len(scenes) >= max_scenes:
                            break
            return scenes
    except Exception as e:
        logger.warning(f"Scene detection failed: {e}")
    
    return []


def generate_video_thumbnail_tool(
    video_path: str,
    output_path: Optional[str] = None,
    timestamp: float = 1.0,
    task_id: Optional[str] = None,
) -> str:
    """Generate a thumbnail from a video.
    
    Args:
        video_path: Path to the video file.
        output_path: Path to save the thumbnail.
        timestamp: Timestamp in seconds to capture thumbnail.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with thumbnail path and info.
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
    
    try:
        if output_path is None:
            stem = Path(video_path).stem
            output_path = f"/tmp/{stem}_thumb.jpg"
        
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-s', '320x240',
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
                "error": f"Failed to generate thumbnail: {result.stderr}",
                "error_code": "THUMBNAIL_ERROR"
            })
        
        output_path_obj = Path(output_path)
        if not output_path_obj.exists():
            return json.dumps({
                "success": False,
                "error": "Thumbnail file was not created",
                "error_code": "FILE_NOT_CREATED"
            })
        
        video_info = _get_video_metadata(video_path)
        duration = 0
        if video_info.get('format', {}).get('duration'):
            duration = float(video_info['format']['duration'])
        
        return json.dumps({
            "success": True,
            "data": {
                "thumbnail_path": str(output_path),
                "timestamp": timestamp,
                "video_duration": duration,
                "file_size_bytes": output_path_obj.stat().st_size
            }
        })
        
    except Exception as e:
        logger.exception(f"Error generating thumbnail: {video_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "THUMBNAIL_ERROR"
        })


def extract_video_audio_tool(
    video_path: str,
    output_path: Optional[str] = None,
    format: str = "mp3",
    task_id: Optional[str] = None,
) -> str:
    """Extract audio from a video file.
    
    Args:
        video_path: Path to the video file.
        output_path: Path to save the audio.
        format: Audio format (mp3, wav, ogg).
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with audio extraction results.
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
    
    try:
        if output_path is None:
            stem = Path(video_path).stem
            output_path = f"/tmp/{stem}.{format}"
        
        audio_codecs = {
            "mp3": "libmp3lame",
            "wav": "pcm_s16le",
            "ogg": "libvorbis",
            "aac": "aac"
        }
        
        codec = audio_codecs.get(format.lower(), "copy")
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vn',
            '-acodec', codec,
            '-q:a', '2',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "error": f"Failed to extract audio: {result.stderr}",
                "error_code": "EXTRACTION_ERROR"
            })
        
        output_path_obj = Path(output_path)
        if not output_path_obj.exists():
            return json.dumps({
                "success": False,
                "error": "Audio file was not created",
                "error_code": "FILE_NOT_CREATED"
            })
        
        video_info = _get_video_metadata(video_path)
        duration = 0
        if video_info.get('format', {}).get('duration'):
            duration = float(video_info['format']['duration'])
        
        return json.dumps({
            "success": True,
            "data": {
                "audio_path": str(output_path),
                "format": format,
                "video_duration": duration,
                "file_size_bytes": output_path_obj.stat().st_size
            }
        })
        
    except Exception as e:
        logger.exception(f"Error extracting audio: {video_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "EXTRACTION_ERROR"
        })


registry.register(
    name="analyze_video",
    toolset="video",
    schema={
        "name": "analyze_video",
        "description": """Analyze a video and provide a comprehensive summary.

Use this tool when you need to:
- Get video metadata (duration, resolution, codec)
- Understand video structure and content
- Detect scene changes in a video
- Prepare for further video processing

Returns detailed information about video and audio streams.""",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file"
                },
                "extract_scenes": {
                    "type": "boolean",
                    "description": "Whether to detect scene changes",
                    "default": True
                },
                "max_scenes": {
                    "type": "integer",
                    "description": "Maximum number of scenes to detect",
                    "default": 10
                }
            },
            "required": ["video_path"]
        }
    },
    handler=lambda args, **kw: analyze_video_tool(
        video_path=args.get("video_path"),
        extract_scenes=args.get("extract_scenes", True),
        max_scenes=args.get("max_scenes", 10),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="generate_video_thumbnail",
    toolset="video",
    schema={
        "name": "generate_video_thumbnail",
        "description": """Generate a thumbnail image from a video.

Use this tool when you need to:
- Create a preview image from a video
- Generate a thumbnail for a video player UI
- Capture a snapshot at a specific timestamp

Output is a JPEG image at 320x240 resolution.""",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file"
                },
                "output_path": {
                    "type": "string",
                    "description": "Path to save the thumbnail",
                    "default": None
                },
                "timestamp": {
                    "type": "number",
                    "description": "Timestamp in seconds to capture thumbnail",
                    "default": 1.0
                }
            },
            "required": ["video_path"]
        }
    },
    handler=lambda args, **kw: generate_video_thumbnail_tool(
        video_path=args.get("video_path"),
        output_path=args.get("output_path"),
        timestamp=args.get("timestamp", 1.0),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ffmpeg_available,
    requires_env=["FFmpeg"],
)


registry.register(
    name="extract_video_audio",
    toolset="video",
    schema={
        "name": "extract_video_audio",
        "description": """Extract audio from a video file.

Use this tool when you need to:
- Convert video audio to a separate audio file
- Extract audio for transcription
- Create an audio-only version of a video

Supports MP3, WAV, OGG, and AAC formats.""",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file"
                },
                "output_path": {
                    "type": "string",
                    "description": "Path to save the audio file",
                    "default": None
                },
                "format": {
                    "type": "string",
                    "description": "Audio format (mp3, wav, ogg, aac)",
                    "default": "mp3"
                }
            },
            "required": ["video_path"]
        }
    },
    handler=lambda args, **kw: extract_video_audio_tool(
        video_path=args.get("video_path"),
        output_path=args.get("output_path"),
        format=args.get("format", "mp3"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ffmpeg_available,
    requires_env=["FFmpeg"],
)