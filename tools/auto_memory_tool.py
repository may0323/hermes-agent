#!/usr/bin/env python3
"""
Auto Memory Tool Module

This module provides tools for automatic memory management and pattern detection.

Features:
- Automatic context summarization
- Pattern detection in conversations
- Memory persistence across sessions
- Key information extraction

Usage:
    from tools.auto_memory_tool import auto_summarize_tool
    
    result = auto_summarize_tool(context="conversation text...")
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from tools.registry import registry

logger = logging.getLogger(__name__)


def auto_summarize_tool(
    context: str,
    max_length: int = 500,
    task_id: Optional[str] = None,
) -> str:
    """Automatically summarize a conversation or text context.
    
    Args:
        context: The text context to summarize.
        max_length: Maximum length of the summary in characters.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with the summary.
    """
    if not context or not context.strip():
        return json.dumps({
            "success": False,
            "error": "Context cannot be empty",
            "error_code": "EMPTY_CONTEXT"
        })
    
    try:
        lines = context.strip().split('\n')
        
        key_points = []
        decisions = []
        action_items = []
        
        action_keywords = ['will', 'should', 'must', 'need to', 'going to', 'plan to', 'decided', 'agreed']
        question_words = ['how', 'what', 'why', 'when', 'where', 'who', 'which']
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if any(kw in line_lower for kw in action_keywords):
                if any(punct in line for punct in ['.', '!', '?']):
                    decisions.append(line.strip())
            
            if line.strip().endswith('?'):
                key_points.append(f"Q: {line.strip()}")
            
            if len(line) > 50 and len(key_points) < 5:
                words = line.split()
                if len(words) > 10:
                    key_points.append(line.strip()[:100] + "..." if len(line) > 100 else line.strip())
        
        summary_parts = []
        
        if decisions:
            summary_parts.append(f"**Decisions/Commitments ({len(decisions)}):**")
            for d in decisions[:3]:
                summary_parts.append(f"- {d[:80]}")
        
        if key_points:
            summary_parts.append(f"\n**Key Points ({len(key_points)}):**")
            for p in key_points[:5]:
                summary_parts.append(f"- {p[:100]}")
        
        summary = "\n".join(summary_parts) if summary_parts else context[:max_length]
        
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return json.dumps({
            "success": True,
            "data": {
                "summary": summary,
                "summary_length": len(summary),
                "original_length": len(context),
                "decisions_count": len(decisions),
                "key_points_count": len(key_points),
                "generated_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.exception("Error generating summary")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "SUMMARY_ERROR"
        })


def extract_entities_tool(
    context: str,
    task_id: Optional[str] = None,
) -> str:
    """Extract named entities and key information from context.
    
    Args:
        context: The text context to analyze.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with extracted entities.
    """
    if not context or not context.strip():
        return json.dumps({
            "success": False,
            "error": "Context cannot be empty",
            "error_code": "EMPTY_CONTEXT"
        })
    
    try:
        words = context.split()
        unique_words = set(w.lower().strip('.,!?;:"\'') for w in words if len(w) > 3)
        
        potential_entities = []
        for i, word in enumerate(words):
            cleaned = word.strip('.,!?;:"\'')
            if cleaned and cleaned[0].isupper() and len(cleaned) > 2:
                if i == 0 or not words[i-1].endswith(('.', '!', '?', ':')):
                    potential_entities.append(cleaned)
        
        entity_counts: Dict[str, int] = {}
        for entity in potential_entities:
            key = entity.lower()
            entity_counts[key] = entity_counts.get(key, 0) + 1
        
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)
        
        mentioned_files = []
        mentioned_paths = []
        
        for word in words:
            if '.' in word and any(word.endswith(ext) for ext in ['.py', '.js', '.ts', '.md', '.json', '.yaml', '.yml', '.txt', '.csv']):
                mentioned_files.append(word.strip('.,!?;:"\''))
            if '/' in word or '\\' in word:
                mentioned_paths.append(word.strip('.,!?;:"\''))
        
        return json.dumps({
            "success": True,
            "data": {
                "entities": [{"name": name, "count": count} for name, count in sorted_entities[:20]],
                "mentioned_files": list(set(mentioned_files))[:10],
                "mentioned_paths": list(set(mentioned_paths))[:10],
                "total_unique_entities": len(sorted_entities),
                "analyzed_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.exception("Error extracting entities")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "EXTRACTION_ERROR"
        })


def detect_patterns_tool(
    context: str,
    task_id: Optional[str] = None,
) -> str:
    """Detect patterns in conversation such as questions, decisions, actions.
    
    Args:
        context: The text context to analyze.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with detected patterns.
    """
    if not context or not context.strip():
        return json.dumps({
            "success": False,
            "error": "Context cannot be empty",
            "error_code": "EMPTY_CONTEXT"
        })
    
    try:
        lines = context.strip().split('\n')
        
        patterns = {
            "questions": [],
            "decisions": [],
            "actions": [],
            "agreements": [],
            "disagreements": []
        }
        
        question_count = 0
        decision_count = 0
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            if line_stripped.endswith('?'):
                patterns["questions"].append(line_stripped)
                question_count += 1
            
            if any(word in line_stripped.lower() for word in ['agreed', 'decided', 'will', 'should', 'must']):
                if any(punct in line_stripped for punct in ['.', '!', '?']):
                    patterns["decisions"].append(line_stripped[:100])
                    decision_count += 1
            
            if 'agreed' in line_stripped.lower():
                patterns["agreements"].append(line_stripped[:100])
            
            if any(word in line_stripped.lower() for word in ['disagree', 'objection', 'reject', 'refuse']):
                patterns["disagreements"].append(line_stripped[:100])
        
        return json.dumps({
            "success": True,
            "data": {
                "patterns": patterns,
                "summary": {
                    "total_questions": question_count,
                    "total_decisions": decision_count,
                    "total_agreements": len(patterns["agreements"]),
                    "total_disagreements": len(patterns["disagreements"])
                },
                "detected_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.exception("Error detecting patterns")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "PATTERN_ERROR"
        })


def memory_search_tool(
    query: str,
    memory_context: str,
    task_id: Optional[str] = None,
) -> str:
    """Search within memory context for relevant information.
    
    Args:
        query: The search query.
        memory_context: The memory context to search within.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with search results.
    """
    if not query or not query.strip():
        return json.dumps({
            "success": False,
            "error": "Query cannot be empty",
            "error_code": "EMPTY_QUERY"
        })
    
    if not memory_context or not memory_context.strip():
        return json.dumps({
            "success": False,
            "error": "Memory context cannot be empty",
            "error_code": "EMPTY_CONTEXT"
        })
    
    try:
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        lines = memory_context.strip().split('\n')
        scored_lines = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            line_words = set(line_lower.split())
            
            query_matches = len(query_words & line_words)
            exact_match_bonus = 100 if query_lower in line_lower else 0
            partial_match_bonus = len(query_words & line_words) * 10
            
            score = query_matches + exact_match_bonus + partial_match_bonus
            
            if score > 0:
                scored_lines.append({
                    "line_number": i + 1,
                    "content": line.strip(),
                    "score": score,
                    "context": lines[max(0, i-1):min(len(lines), i+2)]
                })
        
        scored_lines.sort(key=lambda x: x["score"], reverse=True)
        
        results = scored_lines[:10]
        
        for result in results:
            result.pop("context", None)
        
        return json.dumps({
            "success": True,
            "data": {
                "query": query,
                "results": results,
                "total_matches": len(scored_lines),
                "searched_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.exception("Error searching memory")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "SEARCH_ERROR"
        })


registry.register(
    name="auto_summarize",
    toolset="memory",
    schema={
        "name": "auto_summarize",
        "description": """Automatically summarize a conversation or text context.

Use this tool when you need to:
- Condense a long conversation into key points
- Extract decisions and commitments
- Create a quick overview of a discussion

The summary focuses on decisions, commitments, and key points.""",
        "parameters": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "The text context to summarize"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length of the summary in characters",
                    "default": 500
                }
            },
            "required": ["context"]
        }
    },
    handler=lambda args, **kw: auto_summarize_tool(
        context=args.get("context"),
        max_length=args.get("max_length", 500),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="extract_entities",
    toolset="memory",
    schema={
        "name": "extract_entities",
        "description": """Extract named entities and key information from context.

Use this tool when you need to:
- Identify people, places, organizations mentioned
- Find mentioned files and paths
- Build a knowledge graph from conversation

Returns entities sorted by frequency of mention.""",
        "parameters": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "The text context to analyze"
                }
            },
            "required": ["context"]
        }
    },
    handler=lambda args, **kw: extract_entities_tool(
        context=args.get("context"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="detect_patterns",
    toolset="memory",
    schema={
        "name": "detect_patterns",
        "description": """Detect patterns in conversation such as questions, decisions, and actions.

Use this tool when you need to:
- Identify decision points in a conversation
- Find unanswered questions
- Track agreements and disagreements
- Analyze conversation structure

Returns categorized patterns with counts.""",
        "parameters": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "The text context to analyze"
                }
            },
            "required": ["context"]
        }
    },
    handler=lambda args, **kw: detect_patterns_tool(
        context=args.get("context"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="memory_search",
    toolset="memory",
    schema={
        "name": "memory_search",
        "description": """Search within memory context for relevant information.

Use this tool when you need to:
- Find specific information in past conversations
- Search for mentions of specific topics
- Retrieve relevant context from memory

Returns ranked results based on relevance.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "memory_context": {
                    "type": "string",
                    "description": "The memory context to search within"
                }
            },
            "required": ["query", "memory_context"]
        }
    },
    handler=lambda args, **kw: memory_search_tool(
        query=args.get("query"),
        memory_context=args.get("memory_context"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)