"""MCP Memory Tools for Hermes Agent.

This module provides MCP-compatible memory search tools following
the three-layer pattern: Search -> Timeline -> Get Observations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry
from tools.memory import (
    CompressedObservation,
    MemoryStats,
    SearchResult,
    TimelineEntry,
    TwoTierMemory,
)

logger = logging.getLogger(__name__)


_memory_instance: Optional[TwoTierMemory] = None


def get_memory() -> TwoTierMemory:
    """Get or create the TwoTierMemory singleton."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = TwoTierMemory()
    return _memory_instance


async def memory_search_tool(query: str, limit: int = 5) -> str:
    """Search working memory (Layer 1).
    
    Returns a compact index of matching observations with IDs and scores.
    Use memory_timeline_tool to get context around specific results.
    
    Args:
        query: Search query string.
        limit: Maximum number of results (default 5).
    
    Returns:
        JSON string with search results.
    """
    try:
        memory = get_memory()
        results = await memory.search(query=query, limit=limit)
        
        output = {
            "success": True,
            "query": query,
            "count": len(results),
            "results": [
                {
                    "id": r.id,
                    "score": round(r.score, 3),
                    "preview": r.preview[:100] + "..." if len(r.preview) > 100 else r.preview,
                    "timestamp": r.timestamp,
                    "importance": r.importance,
                }
                for r in results
            ],
        }
        
        return json.dumps(output, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"memory_search error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "SEARCH_ERROR",
        }, ensure_ascii=False)


async def memory_timeline_tool(ids: List[str]) -> str:
    """Get timeline context for observations (Layer 2).
    
    Given observation IDs from memory_search, returns timeline entries
    with timestamps and context. Use memory_get_tool to retrieve
    full observation details.
    
    Args:
        ids: List of observation IDs.
    
    Returns:
        JSON string with timeline entries.
    """
    try:
        memory = get_memory()
        timelines = await memory.get_timeline(ids=ids)
        
        output = {
            "success": True,
            "count": len(timelines),
            "timelines": [
                {
                    "id": t.id,
                    "timestamp": t.timestamp,
                    "session_id": t.session_id,
                    "context": t.context,
                    "importance": t.importance,
                }
                for t in timelines
            ],
        }
        
        return json.dumps(output, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"memory_timeline error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "TIMELINE_ERROR",
        }, ensure_ascii=False)


async def memory_get_tool(ids: List[str]) -> str:
    """Get full observations by IDs (Layer 3).
    
    Given observation IDs, returns complete compressed observations
    including summary, entities, patterns, and metadata.
    This is the most detailed view of a memory.
    
    Args:
        ids: List of observation IDs.
    
    Returns:
        JSON string with full observations.
    """
    try:
        memory = get_memory()
        observations = await memory.get_observations(ids=ids)
        
        output = {
            "success": True,
            "count": len(observations),
            "observations": [
                {
                    "id": o.id,
                    "timestamp": o.timestamp,
                    "session_id": o.session_id,
                    "compression": o.compression,
                    "ratio": o.ratio,
                    "summary": o.summary,
                    "entities": o.entities,
                    "patterns": o.patterns,
                    "importance": o.importance,
                    "original_tokens": o.original_tokens,
                    "compressed_tokens": o.compressed_tokens,
                    "tool_name": o.tool_name,
                }
                for o in observations
            ],
        }
        
        return json.dumps(output, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"memory_get error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "GET_ERROR",
        }, ensure_ascii=False)


async def memory_stats_tool() -> str:
    """Get memory system statistics.
    
    Returns statistics about the memory system including
    working memory count, tokens, archive count, and
    compression ratio.
    
    Returns:
        JSON string with memory statistics.
    """
    try:
        memory = get_memory()
        stats = await memory.get_stats()
        
        output = {
            "success": True,
            "working_count": stats.working_count,
            "working_tokens": stats.working_tokens,
            "archive_count": stats.archive_count,
            "compression_ratio": stats.compression_ratio,
            "last_updated": stats.last_updated,
        }
        
        return json.dumps(output, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"memory_stats error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "STATS_ERROR",
        }, ensure_ascii=False)


def _check_memory_requirements() -> bool:
    """Check if memory system is available."""
    return True


registry.register(
    name="memory_search",
    toolset="memory",
    schema={
        "name": "memory_search",
        "description": "Search working memory (Layer 1). Returns compact search results with IDs and scores. Use memory_timeline to get context, memory_get for full details.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string. Can include keywords in any language.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    handler=lambda args, **kw: memory_search_tool(
        query=args.get("query", ""),
        limit=args.get("limit", 5),
    ),
    check_fn=_check_memory_requirements,
    requires_env=[],
)

registry.register(
    name="memory_timeline",
    toolset="memory",
    schema={
        "name": "memory_timeline",
        "description": "Get timeline context for memory observations (Layer 2). Use IDs from memory_search results.",
        "parameters": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of observation IDs from memory_search",
                },
            },
            "required": ["ids"],
        },
    },
    handler=lambda args, **kw: memory_timeline_tool(
        ids=args.get("ids", []),
    ),
    check_fn=_check_memory_requirements,
    requires_env=[],
)

registry.register(
    name="memory_get",
    toolset="memory",
    schema={
        "name": "memory_get",
        "description": "Get full observation details (Layer 3). Returns complete compressed observations with summary, entities, and patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of observation IDs",
                },
            },
            "required": ["ids"],
        },
    },
    handler=lambda args, **kw: memory_get_tool(
        ids=args.get("ids", []),
    ),
    check_fn=_check_memory_requirements,
    requires_env=[],
)

registry.register(
    name="memory_stats",
    toolset="memory",
    schema={
        "name": "memory_stats",
        "description": "Get memory system statistics including working memory count, tokens, archive count, and compression ratio.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    handler=lambda args, **kw: memory_stats_tool(),
    check_fn=_check_memory_requirements,
    requires_env=[],
)
