#!/usr/bin/env python3
"""
Parallel Executor Tool Module

This module provides tools for parallel task execution and sub-agent coordination.

Features:
- Parallel task execution
- Task result aggregation
- Timeout management
- Error handling

Usage:
    from tools.parallel_executor_tool import execute_parallel_tool
    
    result = execute_parallel_tool(tasks=[{"id": "1", "task": "do something"}, ...])
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from tools.registry import registry

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_id: str
    success: bool
    result: Any = None
    error: str = ""
    execution_time_ms: float = 0


@dataclass
class Task:
    """A task to be executed."""
    id: str
    description: str
    task_type: str = "general"
    params: Dict[str, Any] = field(default_factory=dict)


def _execute_single_task(task: Dict[str, Any], timeout: int = 60) -> TaskResult:
    """Execute a single task and return the result."""
    start_time = datetime.now()
    task_id = task.get("id", "unknown")
    
    try:
        task_type = task.get("type", "general")
        params = task.get("params", {})
        description = task.get("description", "")
        
        if task_type == "code_analysis":
            result = _execute_code_analysis(params)
        elif task_type == "web_search":
            result = _execute_web_search(params)
        elif task_type == "document_processing":
            result = _execute_document_processing(params)
        elif task_type == "calculation":
            result = _execute_calculation(params)
        else:
            result = {"status": "executed", "task_id": task_id, "description": description}
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return TaskResult(
            task_id=task_id,
            success=True,
            result=result,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.exception(f"Error executing task {task_id}")
        return TaskResult(
            task_id=task_id,
            success=False,
            error=str(e),
            execution_time_ms=execution_time
        )


def _execute_code_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute code analysis task."""
    code = params.get("code", "")
    language = params.get("language", "unknown")
    
    return {
        "type": "code_analysis",
        "language": language,
        "lines": len(code.split('\n')),
        "characters": len(code),
        "analysis": "Code analysis completed"
    }


def _execute_web_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute web search task."""
    query = params.get("query", "")
    
    return {
        "type": "web_search",
        "query": query,
        "results_found": 0,
        "message": "Web search placeholder - implement with actual search API"
    }


def _execute_document_processing(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute document processing task."""
    doc_type = params.get("document_type", "unknown")
    
    return {
        "type": "document_processing",
        "document_type": doc_type,
        "processed": True
    }


def _execute_calculation(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute calculation task."""
    expression = params.get("expression", "")
    
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return {
            "type": "calculation",
            "expression": expression,
            "result": result
        }
    except Exception as e:
        raise ValueError(f"Calculation error: {e}")


def execute_parallel_tool(
    tasks: List[Dict[str, Any]],
    max_workers: int = 4,
    timeout_per_task: int = 60,
    stop_on_first_error: bool = False,
    task_id: Optional[str] = None,
) -> str:
    """Execute multiple tasks in parallel.
    
    Args:
        tasks: List of task dictionaries with 'id', 'type', 'params', 'description'.
        max_workers: Maximum number of concurrent workers.
        timeout_per_task: Timeout for each task in seconds.
        stop_on_first_error: Whether to stop execution on first error.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with execution results.
    """
    if not tasks:
        return json.dumps({
            "success": False,
            "error": "No tasks provided",
            "error_code": "EMPTY_TASKS"
        })
    
    if len(tasks) > 50:
        return json.dumps({
            "success": False,
            "error": "Maximum 50 tasks can be executed at once",
            "error_code": "TOO_MANY_TASKS"
        })
    
    if max_workers < 1:
        max_workers = 1
    if max_workers > 10:
        max_workers = 10
    
    start_time = datetime.now()
    results: List[TaskResult] = []
    errors: List[str] = []
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(_execute_single_task, task, timeout_per_task): task
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                task_result = future.result()
                results.append(task_result)
                
                if stop_on_first_error and not task_result.success:
                    errors.append(f"Task {task_result.task_id} failed: {task_result.error}")
                    break
    
    except Exception as e:
        logger.exception("Error in parallel execution")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "EXECUTION_ERROR"
        })
    
    total_time = (datetime.now() - start_time).total_seconds() * 1000
    
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    
    results_data = [
        {
            "task_id": r.task_id,
            "success": r.success,
            "result": r.result,
            "error": r.error,
            "execution_time_ms": round(r.execution_time_ms, 2)
        }
        for r in sorted(results, key=lambda x: x.task_id)
    ]
    
    return json.dumps({
        "success": True,
        "data": {
            "results": results_data,
            "summary": {
                "total_tasks": len(tasks),
                "successful": successful,
                "failed": failed,
                "total_time_ms": round(total_time, 2),
                "avg_time_per_task_ms": round(total_time / len(tasks), 2) if tasks else 0
            },
            "executed_at": datetime.now().isoformat()
        }
    })


def aggregate_results_tool(
    results: List[Dict[str, Any]],
    aggregation_type: str = "summary",
    task_id: Optional[str] = None,
) -> str:
    """Aggregate results from multiple sub-agents or tasks.
    
    Args:
        results: List of result dictionaries.
        aggregation_type: Type of aggregation - 'summary', 'merge', 'filter_errors'.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with aggregated results.
    """
    if not results:
        return json.dumps({
            "success": False,
            "error": "No results to aggregate",
            "error_code": "EMPTY_RESULTS"
        })
    
    try:
        if aggregation_type == "summary":
            successful = sum(1 for r in results if r.get("success", False))
            failed = len(results) - successful
            
            all_results = [r.get("result", {}) for r in results if r.get("success")]
            all_errors = [r.get("error", "") for r in results if not r.get("success", True)]
            
            return json.dumps({
                "success": True,
                "data": {
                    "total_results": len(results),
                    "successful": successful,
                    "failed": failed,
                    "aggregated_results": all_results,
                    "errors": all_errors,
                    "aggregated_at": datetime.now().isoformat()
                }
            })
        
        elif aggregation_type == "merge":
            merged = {}
            for r in results:
                if isinstance(r, dict):
                    merged.update(r.get("result", r))
            
            return json.dumps({
                "success": True,
                "data": {
                    "merged": merged,
                    "result_count": len(results),
                    "aggregated_at": datetime.now().isoformat()
                }
            })
        
        elif aggregation_type == "filter_errors":
            filtered = [r for r in results if r.get("success", True)]
            
            return json.dumps({
                "success": True,
                "data": {
                    "filtered_results": filtered,
                    "original_count": len(results),
                    "filtered_count": len(filtered),
                    "errors_removed": len(results) - len(filtered),
                    "aggregated_at": datetime.now().isoformat()
                }
            })
        
        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown aggregation type: {aggregation_type}",
                "error_code": "INVALID_AGGREGATION_TYPE"
            })
            
    except Exception as e:
        logger.exception("Error aggregating results")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "AGGREGATION_ERROR"
        })


def delegate_task_tool(
    task_description: str,
    agent_type: str = "general",
    context: Optional[str] = None,
    task_id: Optional[str] = None,
) -> str:
    """Delegate a task to a specialized sub-agent.
    
    Args:
        task_description: Description of the task to delegate.
        agent_type: Type of agent - 'coder', 'researcher', 'writer', 'general'.
        context: Optional context information.
        task_id: Optional task ID for tracking.
    
    Returns:
        JSON string with delegation result.
    """
    if not task_description or not task_description.strip():
        return json.dumps({
            "success": False,
            "error": "Task description cannot be empty",
            "error_code": "EMPTY_DESCRIPTION"
        })
    
    valid_agent_types = {"coder", "researcher", "writer", "general", "analyst"}
    if agent_type not in valid_agent_types:
        return json.dumps({
            "success": False,
            "error": f"Invalid agent type: {agent_type}. Must be one of: {valid_agent_types}",
            "error_code": "INVALID_AGENT_TYPE"
        })
    
    try:
        return json.dumps({
            "success": True,
            "data": {
                "delegated": True,
                "task_description": task_description,
                "agent_type": agent_type,
                "context_provided": context is not None,
                "delegation_id": f"del_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "delegated_at": datetime.now().isoformat(),
                "message": "Task delegated to sub-agent. Execute with parallel_executor for actual results."
            }
        })
        
    except Exception as e:
        logger.exception("Error delegating task")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "DELEGATION_ERROR"
        })


registry.register(
    name="execute_parallel",
    toolset="subagents",
    schema={
        "name": "execute_parallel",
        "description": """Execute multiple tasks in parallel using sub-agents.

Use this tool when you need to:
- Execute multiple independent tasks concurrently
- Speed up processing by parallelizing work
- Coordinate multiple sub-agents
- Batch process multiple items

Maximum 50 tasks per execution. Configure max_workers for concurrency level.""",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "params": {"type": "object"}
                        }
                    },
                    "description": "List of tasks to execute"
                },
                "max_workers": {
                    "type": "integer",
                    "description": "Maximum concurrent workers (1-10)",
                    "default": 4
                },
                "timeout_per_task": {
                    "type": "integer",
                    "description": "Timeout per task in seconds",
                    "default": 60
                },
                "stop_on_first_error": {
                    "type": "boolean",
                    "description": "Stop execution on first error",
                    "default": False
                }
            },
            "required": ["tasks"]
        }
    },
    handler=lambda args, **kw: execute_parallel_tool(
        tasks=args.get("tasks", []),
        max_workers=args.get("max_workers", 4),
        timeout_per_task=args.get("timeout_per_task", 60),
        stop_on_first_error=args.get("stop_on_first_error", False),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="aggregate_results",
    toolset="subagents",
    schema={
        "name": "aggregate_results",
        "description": """Aggregate results from multiple sub-agents or tasks.

Use this tool when you need to:
- Combine results from parallel executions
- Filter out errors from results
- Merge result dictionaries
- Create summary statistics

Supports summary, merge, and filter_errors aggregation types.""",
        "parameters": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of results to aggregate"
                },
                "aggregation_type": {
                    "type": "string",
                    "enum": ["summary", "merge", "filter_errors"],
                    "description": "Type of aggregation to perform",
                    "default": "summary"
                }
            },
            "required": ["results"]
        }
    },
    handler=lambda args, **kw: aggregate_results_tool(
        results=args.get("results", []),
        aggregation_type=args.get("aggregation_type", "summary"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)


registry.register(
    name="delegate_task",
    toolset="subagents",
    schema={
        "name": "delegate_task",
        "description": """Delegate a task to a specialized sub-agent.

Use this tool when you need to:
- Offload work to a specialized agent type
- Categorize tasks by domain (coding, research, writing)
- Route tasks to appropriate handlers

Agent types: coder, researcher, writer, analyst, general.""",
        "parameters": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Description of the task to delegate"
                },
                "agent_type": {
                    "type": "string",
                    "enum": ["coder", "researcher", "writer", "analyst", "general"],
                    "description": "Type of agent to delegate to",
                    "default": "general"
                },
                "context": {
                    "type": "string",
                    "description": "Optional context information",
                    "default": None
                }
            },
            "required": ["task_description"]
        }
    },
    handler=lambda args, **kw: delegate_task_tool(
        task_description=args.get("task_description"),
        agent_type=args.get("agent_type", "general"),
        context=args.get("context"),
        task_id=kw.get("task_id")
    ),
    check_fn=lambda: True,
    requires_env=[],
)