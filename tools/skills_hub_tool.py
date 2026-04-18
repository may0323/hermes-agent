#!/usr/bin/env python3
"""
Skills Management Tool Module

This module provides tools for managing and discovering skills in the Skills Hub.

Features:
- List available skills
- Search skills by functionality
- Get skill details
- Skill compatibility checking

Usage:
    from tools.skills_hub_tool import list_skills_tool
    
    result = list_skills_tool()
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)


SKILLS_CATEGORIES = {
    "coding": ["code_analysis", "code_generation", "code_review", "debugging"],
    "research": ["web_search", "documentation", "data_analysis", "report_generation"],
    "creative": ["writing", "image_generation", "video_editing", "content_creation"],
    "automation": ["task_automation", "workflow", "integration", "scheduling"],
    "communication": ["email", "messaging", "documentation", "summarization"]
}


def list_skills_tool(
    category: Optional[str] = None,
    task_id: Optional[str] = None,
) -> str:
    """List all available skills or skills in a specific category.
    
    Args:
        category: Optional category to filter by (coding, research, creative, automation, communication).
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with list of skills.
    """
    try:
        if category:
            category_lower = category.lower()
            if category_lower not in SKILLS_CATEGORIES:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown category: {category}. Available: {list(SKILLS_CATEGORIES.keys())}",
                    "error_code": "INVALID_CATEGORY"
                })
            
            skills = SKILLS_CATEGORIES[category_lower]
            return json.dumps({
                "success": True,
                "data": {
                    "category": category_lower,
                    "skills": [{"name": s, "category": category_lower} for s in skills],
                    "count": len(skills)
                }
            })
        
        all_skills = []
        for cat, skills in SKILLS_CATEGORIES.items():
            for skill in skills:
                all_skills.append({
                    "name": skill,
                    "category": cat
                })
        
        return json.dumps({
            "success": True,
            "data": {
                "skills": all_skills,
                "categories": list(SKILLS_CATEGORIES.keys()),
                "total_count": len(all_skills)
            }
        })
        
    except Exception as e:
        logger.exception("Error listing skills")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "LIST_ERROR"
        })


def search_skills_tool(
    query: str,
    task_id: Optional[str] = None,
) -> str:
    """Search skills by functionality keywords.
    
    Args:
        query: Search query to match against skill names and descriptions.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with matching skills.
    """
    if not query or not query.strip():
        return json.dumps({
            "success": False,
            "error": "Search query cannot be empty",
            "error_code": "EMPTY_QUERY"
        })
    
    try:
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        matched_skills = []
        
        skill_descriptions = {
            "code_analysis": "Analyze code structure, patterns, and quality",
            "code_generation": "Generate code from specifications or descriptions",
            "code_review": "Review code for bugs, security issues, and best practices",
            "debugging": "Find and fix bugs in code",
            "web_search": "Search the web for information",
            "documentation": "Generate and maintain documentation",
            "data_analysis": "Analyze and interpret data",
            "report_generation": "Generate structured reports",
            "writing": "Write content, articles, or creative text",
            "image_generation": "Generate images from descriptions",
            "video_editing": "Edit and process video content",
            "content_creation": "Create various types of content",
            "task_automation": "Automate repetitive tasks",
            "workflow": "Create and manage workflows",
            "integration": "Connect different systems and APIs",
            "scheduling": "Schedule and coordinate tasks",
            "email": "Send and manage emails",
            "messaging": "Send messages via various platforms",
            "summarization": "Summarize long content into concise form"
        }
        
        for category, skills in SKILLS_CATEGORIES.items():
            for skill in skills:
                skill_words = set(skill.lower().replace("_", " ").split())
                description_words = set(skill_descriptions.get(skill, "").lower().split())
                
                query_matches = len(query_words & skill_words)
                desc_matches = len(query_words & description_words)
                
                if query_matches > 0 or desc_matches > 0:
                    score = query_matches * 2 + desc_matches
                    matched_skills.append({
                        "name": skill,
                        "category": category,
                        "description": skill_descriptions.get(skill, ""),
                        "score": score
                    })
        
        matched_skills.sort(key=lambda x: x["score"], reverse=True)
        
        return json.dumps({
            "success": True,
            "data": {
                "query": query,
                "matches": matched_skills[:10],
                "total_matches": len(matched_skills)
            }
        })
        
    except Exception as e:
        logger.exception("Error searching skills")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "SEARCH_ERROR"
        })


def get_skill_details_tool(
    skill_name: str,
    task_id: Optional[str] = None,
) -> str:
    """Get detailed information about a specific skill.
    
    Args:
        skill_name: Name of the skill to get details for.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with skill details.
    """
    if not skill_name or not skill_name.strip():
        return json.dumps({
            "success": False,
            "error": "Skill name cannot be empty",
            "error_code": "EMPTY_SKILL_NAME"
        })
    
    try:
        skill_name_lower = skill_name.lower().replace(" ", "_")
        
        skill_info = {
            "code_analysis": {
                "description": "Analyze code structure, patterns, and quality metrics",
                "capabilities": ["Parse code syntax", "Detect patterns", "Measure complexity", "Identify issues"],
                "use_cases": ["Code review", "Quality assessment", "Pattern detection"],
                "category": "coding"
            },
            "code_generation": {
                "description": "Generate code from specifications or natural language descriptions",
                "capabilities": ["Write functions", "Create classes", "Generate tests", "Scaffold projects"],
                "use_cases": ["Rapid prototyping", "Boilerplate generation", "Test writing"],
                "category": "coding"
            },
            "code_review": {
                "description": "Review code for bugs, security issues, and best practices",
                "capabilities": ["Find bugs", "Security scanning", "Style checking", "Best practice validation"],
                "use_cases": ["Pre-commit review", "Security audits", "Code quality checks"],
                "category": "coding"
            },
            "debugging": {
                "description": "Find and fix bugs in code with detailed explanations",
                "capabilities": ["Error diagnosis", "Root cause analysis", "Fix suggestions", "Code tracing"],
                "use_cases": ["Bug fixes", "Error resolution", "Issue investigation"],
                "category": "coding"
            },
            "web_search": {
                "description": "Search the web for information, documentation, and resources",
                "capabilities": ["Web search", "Documentation lookup", "API reference", "Tutorial finding"],
                "use_cases": ["Research", "Documentation lookup", "Troubleshooting"],
                "category": "research"
            },
            "documentation": {
                "description": "Generate and maintain technical documentation",
                "capabilities": ["Generate docs", "Update docs", "Format markdown", "Create examples"],
                "use_cases": ["API documentation", "README files", "User guides"],
                "category": "research"
            },
            "data_analysis": {
                "description": "Analyze and interpret data to extract insights",
                "capabilities": ["Statistical analysis", "Data visualization", "Trend detection", "Pattern recognition"],
                "use_cases": ["Business intelligence", "Research analysis", "Data exploration"],
                "category": "research"
            },
            "report_generation": {
                "description": "Generate structured reports from data or analysis",
                "capabilities": ["Structure content", "Format tables", "Add charts", "Create summaries"],
                "use_cases": ["Status reports", "Analytics reports", "Research summaries"],
                "category": "research"
            }
        }
        
        if skill_name_lower in skill_info:
            info = skill_info[skill_name_lower]
            return json.dumps({
                "success": True,
                "data": {
                    "name": skill_name_lower,
                    **info
                }
            })
        
        for category, skills in SKILLS_CATEGORIES.items():
            if skill_name_lower in skills:
                return json.dumps({
                    "success": True,
                    "data": {
                        "name": skill_name_lower,
                        "category": category,
                        "description": f"{skill_name_lower.replace('_', ' ').title()} skill",
                        "capabilities": [],
                        "use_cases": []
                    }
                })
        
        return json.dumps({
            "success": False,
            "error": f"Skill not found: {skill_name}",
            "error_code": "SKILL_NOT_FOUND"
        })
        
    except Exception as e:
        logger.exception("Error getting skill details")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "DETAILS_ERROR"
        })


def check_skill_compatibility_tool(
    skill_name: str,
    context: str,
    task_id: Optional[str] = None,
) -> str:
    """Check if a skill is compatible with a given context.
    
    Args:
        skill_name: Name of the skill to check.
        context: Context description to check against.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with compatibility assessment.
    """
    if not skill_name or not skill_name.strip():
        return json.dumps({
            "success": False,
            "error": "Skill name cannot be empty",
            "error_code": "EMPTY_SKILL_NAME"
        })
    
    if not context or not context.strip():
        return json.dumps({
            "success": False,
            "error": "Context cannot be empty",
            "error_code": "EMPTY_CONTEXT"
        })
    
    try:
        skill_name_lower = skill_name.lower().replace(" ", "_")
        context_lower = context.lower()
        
        compatibility_keywords = {
            "code_analysis": ["code", "function", "class", "algorithm", "syntax", "programming"],
            "code_generation": ["generate", "create", "write", "build", "make", "implement"],
            "code_review": ["review", "check", "audit", "validate", "test"],
            "debugging": ["bug", "error", "fix", "issue", "problem", "crash", "exception"],
            "web_search": ["search", "find", "lookup", "research", "web", "internet"],
            "documentation": ["document", "readme", "guide", "manual", "specification"],
            "data_analysis": ["data", "analyze", "statistics", "chart", "graph", "trend"],
            "report_generation": ["report", "summary", "document", "present", "results"],
            "writing": ["write", "compose", "create", "content", "article", "text"],
            "image_generation": ["image", "picture", "photo", "generate", "create", "draw"],
            "video_editing": ["video", "clip", "edit", "cut", "transition", "render"],
            "content_creation": ["content", "create", "素材", "multimedia", "media"],
            "task_automation": ["automate", "schedule", "batch", "repeat", "routine"],
            "workflow": ["workflow", "pipeline", "process", "stage", "step"],
            "integration": ["integrate", "connect", "api", "service", "system"],
            "scheduling": ["schedule", "time", "cron", "periodic", "recurring"],
            "email": ["email", "mail", "send", "inbox", "smtp"],
            "messaging": ["message", "chat", "send", "notification", "slack", "discord"],
            "summarization": ["summarize", "summary", "concise", "brief", "shorten"]
        }
        
        keywords = compatibility_keywords.get(skill_name_lower, [])
        
        matches = sum(1 for kw in keywords if kw in context_lower)
        total_keywords = len(keywords)
        
        if total_keywords == 0:
            compatibility_score = 0.5
            recommendation = "neutral"
        else:
            compatibility_score = min(matches / total_keywords * 2, 1.0)
            if compatibility_score > 0.7:
                recommendation = "highly_recommended"
            elif compatibility_score > 0.4:
                recommendation = "recommended"
            elif compatibility_score > 0.2:
                recommendation = "may_work"
            else:
                recommendation = "not_recommended"
        
        return json.dumps({
            "success": True,
            "data": {
                "skill_name": skill_name_lower,
                "compatibility_score": round(compatibility_score, 2),
                "recommendation": recommendation,
                "keywords_matched": matches,
                "keywords_checked": total_keywords,
                "context_relevance": matches > 0
            }
        })
        
    except Exception as e:
        logger.exception("Error checking skill compatibility")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "COMPATIBILITY_ERROR"
        })


registry.register(
    name="list_skills",
    toolset="skills",
    schema={
        "name": "list_skills",
        "description": """List all available skills or filter by category.

Use this tool when you need to:
- See what skills are available
- Find skills in a specific domain
- Get an overview of the Skills Hub

Categories: coding, research, creative, automation, communication.""",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category to filter by",
                    "enum": ["coding", "research", "creative", "automation", "communication"]
                }
            }
        }
    },
    handler=lambda args, **kw: list_skills_tool(
        category=args.get("category"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="search_skills",
    toolset="skills",
    schema={
        "name": "search_skills",
        "description": """Search skills by functionality keywords.

Use this tool when you need to:
- Find skills matching a specific task
- Search for related skills
- Discover skills for a use case

Returns skills ranked by relevance to your query.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    },
    handler=lambda args, **kw: search_skills_tool(
        query=args.get("query"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="get_skill_details",
    toolset="skills",
    schema={
        "name": "get_skill_details",
        "description": """Get detailed information about a specific skill.

Use this tool when you need to:
- Learn what a skill can do
- Understand skill capabilities
- Get use case examples

Returns skill description, capabilities, and category.""",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to get details for"
                }
            },
            "required": ["skill_name"]
        }
    },
    handler=lambda args, **kw: get_skill_details_tool(
        skill_name=args.get("skill_name"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="check_skill_compatibility",
    toolset="skills",
    schema={
        "name": "check_skill_compatibility",
        "description": """Check if a skill is compatible with a given context.

Use this tool when you need to:
- Decide which skill to use
- Get recommendations for a task
- Match skills to requirements

Returns a compatibility score and recommendation.""",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to check"
                },
                "context": {
                    "type": "string",
                    "description": "Context description to check against"
                }
            },
            "required": ["skill_name", "context"]
        }
    },
    handler=lambda args, **kw: check_skill_compatibility_tool(
        skill_name=args.get("skill_name"),
        context=args.get("context"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)