"""Data models for Claude Memory System."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def generate_observation_id() -> str:
    """Generate a unique observation ID."""
    return f"obs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


@dataclass
class CompressedObservation:
    """A compressed observation from tool use."""
    id: str = field(default_factory=generate_observation_id)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: str = ""
    compression: str = "ai"  # "ai" or "heuristic"
    ratio: str = "1:1"
    summary: str = ""
    entities: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    importance: str = "medium"  # "low", "medium", "high"
    original_tokens: int = 0
    compressed_tokens: int = 0
    tool_name: str = ""
    tool_args: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CompressedObservation:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Transcript:
    """Full transcript of a session for archiving."""
    session_id: str
    start_time: str
    end_time: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Transcript:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SearchResult:
    """A search result from memory search."""
    id: str
    score: float
    preview: str
    timestamp: str
    importance: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineEntry:
    """A timeline entry for memory context."""
    id: str
    timestamp: str
    session_id: str
    context: str
    importance: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryStats:
    """Memory system statistics."""
    working_count: int = 0
    working_tokens: int = 0
    archive_count: int = 0
    compression_ratio: str = "1:1"
    last_updated: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionSummary:
    """Summary of a session for CLAUDE.md updates."""
    session_id: str
    date: str
    tools_used: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    key_outcomes: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
