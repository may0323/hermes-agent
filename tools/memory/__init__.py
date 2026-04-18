"""Claude Memory System for Hermes Agent.

This module provides:
- Two-tier memory storage (Working + Archive)
- AI-powered compression of observations
- CLAUDE.md auto-writing
- MCP memory search tools
"""

from tools.memory.models import (
    CompressedObservation,
    MemoryStats,
    SearchResult,
    SessionSummary,
    TimelineEntry,
    Transcript,
    generate_observation_id,
)

from tools.memory.two_tier_memory import TwoTierMemory
from tools.memory.compression_observer import CompressionObserver, CompressionResult
from tools.memory.claude_md_writer import ClaudeMDWriter

__all__ = [
    "CompressedObservation",
    "MemoryStats",
    "SearchResult",
    "SessionSummary",
    "TimelineEntry",
    "Transcript",
    "generate_observation_id",
    "TwoTierMemory",
    "CompressionObserver",
    "CompressionResult",
    "ClaudeMDWriter",
]
