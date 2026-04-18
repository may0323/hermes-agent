#!/usr/bin/env python3
"""
Audio Processing Tool Module

This module provides tools for processing and analyzing audio files.

Features:
- Audio format conversion
- Audio metadata extraction
- Basic audio analysis (duration, sample rate, etc.)

Usage:
    from tools.audio_processing import process_audio_tool
    
    result = process_audio_tool(audio_path="/path/to/audio.wav")
"""

import importlib.util
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

PYAV_AVAILABLE = importlib.util.find_spec("av") is not None

MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
SUPPORTED_FORMATS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma'}


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


def _get_audio_metadata(audio_path: str) -> Dict[str, Any]:
    """Get audio metadata using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Error getting audio metadata: {e}")
        return {}


def get_audio_info_tool(
    audio_path: str,
    task_id: Optional[str] = None,
) -> str:
    """Get information about an audio file.
    
    Args:
        audio_path: Path to the audio file.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with audio metadata.
    """
    is_valid, error_msg = _check_file_size(audio_path)
    if not is_valid:
        return json.dumps({
            "success": False,
            "error": error_msg,
            "error_code": "INVALID_FILE"
        })
    
    try:
        audio_info = _get_audio_metadata(audio_path)
        
        if not audio_info:
            return json.dumps({
                "success": False,
                "error": "Could not read audio info",
                "error_code": "INFO_ERROR"
            })
        
        format_info = audio_info.get('format', {})
        audio_stream = None
        
        for stream in audio_info.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break
        
        result: Dict[str, Any] = {
            "file_name": Path(audio_path).name,
            "file_path": str(Path(audio_path).resolve()),
            "file_size_bytes": Path(audio_path).stat().st_size,
            "duration": float(format_info.get('duration', 0)),
            "format": format_info.get('format_name', 'unknown')
        }
        
        if audio_stream:
            result["audio"] = {
                "codec": audio_stream.get('codec_name', 'unknown'),
                "sample_rate": int(audio_stream.get('sample_rate', 0)),
                "channels": audio_stream.get('channels', 0),
                "bitrate": int(format_info.get('bit_rate', 0)),
                "bits_per_sample": audio_stream.get('bits_per_sample', 0)
            }
        
        return json.dumps({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.exception(f"Error getting audio info: {audio_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "INFO_ERROR"
        })


def convert_audio_tool(
    audio_path: str,
    output_format: str = "mp3",
    output_path: Optional[str] = None,
    bitrate: str = "192k",
    task_id: Optional[str] = None,
) -> str:
    """Convert audio from one format to another.
    
    Args:
        audio_path: Path to the source audio file.
        output_format: Target format (mp3, wav, ogg, flac).
        output_path: Optional path for the output file.
        bitrate: Target bitrate (e.g., "192k", "320k").
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with conversion results.
    """
    is_valid, error_msg = _check_file_size(audio_path)
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
    
    valid_formats = {"mp3", "wav", "ogg", "flac", "m4a", "aac"}
    if output_format.lower() not in valid_formats:
        return json.dumps({
            "success": False,
            "error": f"Unsupported output format: {output_format}",
            "error_code": "UNSUPPORTED_FORMAT"
        })
    
    try:
        if output_path is None:
            stem = Path(audio_path).stem
            output_path = f"/tmp/{stem}.{output_format}"
        
        codec_map = {
            "mp3": "libmp3lame",
            "wav": "pcm_s16le",
            "ogg": "libvorbis",
            "flac": "flac",
            "m4a": "aac",
            "aac": "aac"
        }
        
        codec = codec_map.get(output_format.lower(), "copy")
        
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-acodec', codec,
            '-b:a', bitrate,
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
                "error": f"Conversion failed: {result.stderr}",
                "error_code": "CONVERSION_ERROR"
            })
        
        output_path_obj = Path(output_path)
        if not output_path_obj.exists():
            return json.dumps({
                "success": False,
                "error": "Output file was not created",
                "error_code": "FILE_NOT_CREATED"
            })
        
        return json.dumps({
            "success": True,
            "data": {
                "output_path": str(output_path),
                "format": output_format,
                "file_size_bytes": output_path_obj.stat().st_size
            }
        })
        
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Conversion timed out",
            "error_code": "TIMEOUT"
        })
    except Exception as e:
        logger.exception(f"Error converting audio: {audio_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "CONVERSION_ERROR"
        })


def trim_audio_tool(
    audio_path: str,
    start_time: float = 0.0,
    duration: Optional[float] = None,
    output_path: Optional[str] = None,
    task_id: Optional[str] = None,
) -> str:
    """Trim audio to a specific segment.
    
    Args:
        audio_path: Path to the source audio file.
        start_time: Start time in seconds.
        duration: Duration of the segment in seconds. If None, trim to end.
        output_path: Optional path for the output file.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with trim results.
    """
    is_valid, error_msg = _check_file_size(audio_path)
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
            stem = Path(audio_path).stem
            output_path = f"/tmp/{stem}_trimmed.wav"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-ss', str(start_time)
        ]
        
        if duration is not None:
            cmd.extend(['-t', str(duration)])
        
        cmd.append(output_path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "error": f"Trim failed: {result.stderr}",
                "error_code": "TRIM_ERROR"
            })
        
        output_path_obj = Path(output_path)
        if not output_path_obj.exists():
            return json.dumps({
                "success": False,
                "error": "Output file was not created",
                "error_code": "FILE_NOT_CREATED"
            })
        
        return json.dumps({
            "success": True,
            "data": {
                "output_path": str(output_path),
                "start_time": start_time,
                "duration": duration,
                "file_size_bytes": output_path_obj.stat().st_size
            }
        })
        
    except Exception as e:
        logger.exception(f"Error trimming audio: {audio_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "TRIM_ERROR"
        })


def adjust_audio_volume_tool(
    audio_path: str,
    volume_factor: float = 1.0,
    output_path: Optional[str] = None,
    task_id: Optional[str] = None,
) -> str:
    """Adjust the volume of an audio file.
    
    Args:
        audio_path: Path to the source audio file.
        volume_factor: Volume multiplier (0.5 = half, 2.0 = double).
        output_path: Optional path for the output file.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with volume adjustment results.
    """
    is_valid, error_msg = _check_file_size(audio_path)
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
    
    if volume_factor <= 0 or volume_factor > 10:
        return json.dumps({
            "success": False,
            "error": "Volume factor must be between 0 and 10",
            "error_code": "INVALID_PARAMETER"
        })
    
    try:
        if output_path is None:
            stem = Path(audio_path).stem
            output_path = f"/tmp/{stem}_volume.wav"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-af', f'volume={volume_factor}',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "error": f"Volume adjustment failed: {result.stderr}",
                "error_code": "VOLUME_ERROR"
            })
        
        output_path_obj = Path(output_path)
        if not output_path_obj.exists():
            return json.dumps({
                "success": False,
                "error": "Output file was not created",
                "error_code": "FILE_NOT_CREATED"
            })
        
        return json.dumps({
            "success": True,
            "data": {
                "output_path": str(output_path),
                "volume_factor": volume_factor,
                "file_size_bytes": output_path_obj.stat().st_size
            }
        })
        
    except Exception as e:
        logger.exception(f"Error adjusting audio volume: {audio_path}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "VOLUME_ERROR"
        })


registry.register(
    name="get_audio_info",
    toolset="voice",
    schema={
        "name": "get_audio_info",
        "description": """Get information and metadata about an audio file.

Use this tool when you need to:
- Get audio duration, sample rate, channels
- Check audio format and bitrate
- Verify audio file is valid before processing

Returns detailed audio stream information.""",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to the audio file"
                }
            },
            "required": ["audio_path"]
        }
    },
    handler=lambda args, **kw: get_audio_info_tool(
        audio_path=args.get("audio_path"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="convert_audio",
    toolset="voice",
    schema={
        "name": "convert_audio",
        "description": """Convert audio from one format to another.

Use this tool when you need to:
- Convert audio files between formats (MP3, WAV, OGG, FLAC, etc.)
- Change audio bitrate
- Prepare audio for specific use cases

Requires FFmpeg to be installed.""",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to the source audio file"
                },
                "output_format": {
                    "type": "string",
                    "description": "Target format (mp3, wav, ogg, flac, m4a, aac)",
                    "default": "mp3"
                },
                "output_path": {
                    "type": "string",
                    "description": "Optional path for the output file",
                    "default": None
                },
                "bitrate": {
                    "type": "string",
                    "description": "Target bitrate (e.g., 192k, 320k)",
                    "default": "192k"
                }
            },
            "required": ["audio_path"]
        }
    },
    handler=lambda args, **kw: convert_audio_tool(
        audio_path=args.get("audio_path"),
        output_format=args.get("output_format", "mp3"),
        output_path=args.get("output_path"),
        bitrate=args.get("bitrate", "192k"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ffmpeg_available,
    requires_env=["FFmpeg"],
)


registry.register(
    name="trim_audio",
    toolset="voice",
    schema={
        "name": "trim_audio",
        "description": """Trim audio to a specific segment.

Use this tool when you need to:
- Extract a portion of an audio file
- Create a clip from a longer recording
- Remove unwanted sections from audio

Requires FFmpeg to be installed.""",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to the source audio file"
                },
                "start_time": {
                    "type": "number",
                    "description": "Start time in seconds",
                    "default": 0.0
                },
                "duration": {
                    "type": "number",
                    "description": "Duration in seconds (if None, trim to end)",
                    "default": None
                },
                "output_path": {
                    "type": "string",
                    "description": "Optional path for the output file",
                    "default": None
                }
            },
            "required": ["audio_path"]
        }
    },
    handler=lambda args, **kw: trim_audio_tool(
        audio_path=args.get("audio_path"),
        start_time=args.get("start_time", 0.0),
        duration=args.get("duration"),
        output_path=args.get("output_path"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ffmpeg_available,
    requires_env=["FFmpeg"],
)


registry.register(
    name="adjust_audio_volume",
    toolset="voice",
    schema={
        "name": "adjust_audio_volume",
        "description": """Adjust the volume of an audio file.

Use this tool when you need to:
- Increase or decrease audio volume
- Normalize audio levels
- Create a louder or quieter version of audio

Volume factor: 0.5 = half volume, 1.0 = original, 2.0 = double.
Requires FFmpeg to be installed.""",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to the source audio file"
                },
                "volume_factor": {
                    "type": "number",
                    "description": "Volume multiplier (0.5 = half, 2.0 = double)",
                    "default": 1.0
                },
                "output_path": {
                    "type": "string",
                    "description": "Optional path for the output file",
                    "default": None
                }
            },
            "required": ["audio_path"]
        }
    },
    handler=lambda args, **kw: adjust_audio_volume_tool(
        audio_path=args.get("audio_path"),
        volume_factor=args.get("volume_factor", 1.0),
        output_path=args.get("output_path"),
        task_id=kw.get("task_id")
    ),
    check_fn=check_ffmpeg_available,
    requires_env=["FFmpeg"],
)