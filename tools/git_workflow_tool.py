"""Git Workflow Tools for Hermes Agent.

This module provides structured Git operations for branch management,
commits, and repository state inspection.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)


def _run_git_command(args: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
    """Execute a git command and return parsed result.

    Args:
        args: Git command arguments (e.g., ['status', '--porcelain'])
        cwd: Working directory for the command

    Returns:
        Dict with success, stdout, stderr, returncode
    """
    if cwd is None:
        cwd = os.getcwd()

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Git command timed out after 30 seconds",
            "returncode": -1,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Git command not found. Is Git installed?",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


def _is_git_repository(cwd: Optional[str] = None) -> bool:
    """Check if the current directory is inside a git repository."""
    result = _run_git_command(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
    return result.get("stdout", "").lower() == "true"


def _check_dangerous_operation(operation: str, args: List[str]) -> Dict[str, Any]:
    """Check for potentially dangerous git operations.

    Returns dict with 'safe' (bool) and 'reason' (str).
    """
    dangerous_patterns = [
        (r"git\s+reset\s+--hard", "hard reset discards uncommitted changes"),
        (r"git\s+clean\s+-f", "clean removes untracked files"),
        (r"git\s+rebase\s+--onto", "rebasing can rewrite history"),
        (r"git\s+push\s+--force", "force push overwrites remote history"),
        (r"git\s+branch\s+-D", "deleting a branch permanently removes commits"),
        (r"git\s+push\s+--delete", "deleting a remote branch is irreversible"),
    ]

    full_cmd = " ".join(args)
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, full_cmd, re.IGNORECASE):
            return {"safe": False, "reason": reason, "operation": operation}

    return {"safe": True, "reason": "", "operation": operation}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def git_status_tool(task_id: str = None) -> str:
    """Get the current git status of the repository.

    Returns a formatted summary of:
    - Current branch
    - Staged changes
    - Unstaged changes
    - Untracked files
    """
    try:
        if not _is_git_repository():
            return json.dumps({
                "success": False,
                "error": "Not inside a git repository",
                "error_code": "NOT_A_REPO",
            })

        cwd = os.getcwd()

        status_result = _run_git_command(["status", "--porcelain", "-b"], cwd=cwd)
        if not status_result["success"]:
            return json.dumps({
                "success": False,
                "error": status_result["stderr"],
                "error_code": "STATUS_ERROR",
            })

        branch_result = _run_git_command(["branch", "--show-current"], cwd=cwd)
        current_branch = branch_result["stdout"] if branch_result["success"] else "(detached)"

        untracked_files = []
        staged_files = []
        unstaged_files = []

        for line in status_result["stdout"].strip().split("\n"):
            if not line:
                continue
            if len(line) < 3:
                continue
            status_code = line[:2]
            filename = line[3:].strip()

            if status_code == "##":
                continue

            if status_code == "??":
                untracked_files.append(filename)
            elif status_code[0] != " ":
                staged_files.append({"file": filename, "status": status_code})
            elif status_code[1] != " ":
                unstaged_files.append({"file": filename, "status": status_code})

        return json.dumps({
            "success": True,
            "branch": current_branch,
            "staged": staged_files,
            "unstaged": unstaged_files,
            "untracked": untracked_files,
            "is_dirty": bool(staged_files or unstaged_files or untracked_files),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"git_status_tool error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "UNKNOWN_ERROR",
        })


def git_branch_list_tool(remote: bool = False, task_id: str = None) -> str:
    """List all local (and optionally remote) git branches.

    Args:
        remote: Include remote branches (default: False)
    """
    try:
        if not _is_git_repository():
            return json.dumps({
                "success": False,
                "error": "Not inside a git repository",
                "error_code": "NOT_A_REPO",
            })

        cwd = os.getcwd()

        local_result = _run_git_command(["branch", "--format=%(refname:short)"], cwd=cwd)
        if not local_result["success"]:
            return json.dumps({
                "success": False,
                "error": local_result["stderr"],
                "error_code": "BRANCH_LIST_ERROR",
            })

        branches = [b.strip() for b in local_result["stdout"].split("\n") if b.strip()]

        current_branch_result = _run_git_command(["branch", "--show-current"], cwd=cwd)
        current = current_branch_result["stdout"].strip() if current_branch_result["success"] else ""

        remote_branches = []
        if remote:
            remote_result = _run_git_command(["branch", "-r", "--format=%(refname:short)"], cwd=cwd)
            if remote_result["success"]:
                remote_branches = [b.strip() for b in remote_result["stdout"].split("\n") if b.strip() and "/" in b]

        return json.dumps({
            "success": True,
            "current_branch": current,
            "local_branches": branches,
            "remote_branches": remote_branches,
            "count": len(branches),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"git_branch_list_tool error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "UNKNOWN_ERROR",
        })


def git_branch_create_tool(name: str, switch: bool = True, task_id: str = None) -> str:
    """Create a new git branch.

    Args:
        name: Name of the branch to create
        switch: Switch to the new branch immediately (default: True)
    """
    try:
        if not _is_git_repository():
            return json.dumps({
                "success": False,
                "error": "Not inside a git repository",
                "error_code": "NOT_A_REPO",
            })

        if not name or len(name.strip()) == 0:
            return json.dumps({
                "success": False,
                "error": "Branch name cannot be empty",
                "error_code": "INVALID_NAME",
            })

        sanitized_name = re.sub(r"[^a-zA-Z0-9_\-/]", "-", name.strip())

        if sanitized_name.startswith("-") or sanitized_name.startswith("/"):
            sanitized_name = sanitized_name.lstrip("-/")

        cwd = os.getcwd()

        check_result = _run_git_command(["rev-parse", "--verify", f"refs/heads/{sanitized_name}"], cwd=cwd)
        if check_result["success"]:
            return json.dumps({
                "success": False,
                "error": f"Branch '{sanitized_name}' already exists",
                "error_code": "BRANCH_EXISTS",
            })

        create_result = _run_git_command(["branch", sanitized_name], cwd=cwd)
        if not create_result["success"]:
            return json.dumps({
                "success": False,
                "error": create_result["stderr"],
                "error_code": "BRANCH_CREATE_ERROR",
            })

        if switch:
            switch_result = _run_git_command(["checkout", sanitized_name], cwd=cwd)
            if not switch_result["success"]:
                return json.dumps({
                    "success": True,
                    "warning": f"Branch created but switch failed: {switch_result['stderr']}",
                    "branch": sanitized_name,
                    "switched": False,
                })

        return json.dumps({
            "success": True,
            "branch": sanitized_name,
            "switched": switch,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"git_branch_create_tool error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "UNKNOWN_ERROR",
        })


def git_branch_delete_tool(name: str, force: bool = False, task_id: str = None) -> str:
    """Delete a git branch.

    Args:
        name: Name of the branch to delete
        force: Force delete even if branch has unmerged changes (default: False)
    """
    try:
        if not _is_git_repository():
            return json.dumps({
                "success": False,
                "error": "Not inside a git repository",
                "error_code": "NOT_A_REPO",
            })

        if not name:
            return json.dumps({
                "success": False,
                "error": "Branch name cannot be empty",
                "error_code": "INVALID_NAME",
            })

        cwd = os.getcwd()

        current_result = _run_git_command(["branch", "--show-current"], cwd=cwd)
        current_branch = current_result["stdout"].strip() if current_result["success"] else ""

        if current_branch == name:
            return json.dumps({
                "success": False,
                "error": f"Cannot delete the current branch '{name}'",
                "error_code": "DELETE_CURRENT_BRANCH",
            })

        args = ["branch"]
        if force:
            args.append("-D")
        else:
            args.append("-d")
        args.append(name)

        delete_result = _run_git_command(args, cwd=cwd)

        if not delete_result["success"]:
            return json.dumps({
                "success": False,
                "error": delete_result["stderr"],
                "error_code": "BRANCH_DELETE_ERROR",
            })

        return json.dumps({
            "success": True,
            "branch": name,
            "deleted": True,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"git_branch_delete_tool error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "UNKNOWN_ERROR",
        })


def git_commit_tool(message: str, files: List[str] = None, all: bool = False, task_id: str = None) -> str:
    """Create a git commit with the specified files.

    Args:
        message: Commit message
        files: List of files to commit (default: all staged files)
        all: Stage all modified files automatically (default: False)
    """
    try:
        if not _is_git_repository():
            return json.dumps({
                "success": False,
                "error": "Not inside a git repository",
                "error_code": "NOT_A_REPO",
            })

        if not message or len(message.strip()) == 0:
            return json.dumps({
                "success": False,
                "error": "Commit message cannot be empty",
                "error_code": "EMPTY_MESSAGE",
            })

        cwd = os.getcwd()

        if all:
            stage_result = _run_git_command(["add", "-A"], cwd=cwd)
            if not stage_result["success"]:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to stage files: {stage_result['stderr']}",
                    "error_code": "STAGE_ERROR",
                })
        elif files:
            for f in files:
                stage_result = _run_git_command(["add", f], cwd=cwd)
                if not stage_result["success"]:
                    return json.dumps({
                        "success": False,
                        "error": f"Failed to stage {f}: {stage_result['stderr']}",
                        "error_code": "STAGE_ERROR",
                    })

        commit_result = _run_git_command(["commit", "-m", message], cwd=cwd)

        if not commit_result["success"]:
            return json.dumps({
                "success": False,
                "error": commit_result["stderr"],
                "error_code": "COMMIT_ERROR",
            })

        commit_hash_result = _run_git_command(["rev-parse", "HEAD"], cwd=cwd)
        commit_hash = commit_hash_result["stdout"][:7] if commit_hash_result["success"] else ""

        return json.dumps({
            "success": True,
            "message": message,
            "commit_hash": commit_hash,
            "files": files or ["(all staged)"],
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"git_commit_tool error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "UNKNOWN_ERROR",
        })


def git_log_tool(limit: int = 10, path: str = None, task_id: str = None) -> str:
    """Get recent git commit history.

    Args:
        limit: Maximum number of commits to return (default: 10)
        path: Optional path to filter commits for a specific file/directory
    """
    try:
        if not _is_git_repository():
            return json.dumps({
                "success": False,
                "error": "Not inside a git repository",
                "error_code": "NOT_A_REPO",
            })

        cwd = os.getcwd()

        args = ["log", f"--max-count={limit}", "--format=%H|%s|%an|%ad|%ae"]
        if path:
            args.append("--")
            args.append(path)

        log_result = _run_git_command(args, cwd=cwd)

        if not log_result["success"]:
            return json.dumps({
                "success": False,
                "error": log_result["stderr"],
                "error_code": "LOG_ERROR",
            })

        commits = []
        for line in log_result["stdout"].strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0][:7],
                    "full_hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3] if len(parts) > 3 else "",
                    "email": parts[4] if len(parts) > 4 else "",
                })

        return json.dumps({
            "success": True,
            "count": len(commits),
            "commits": commits,
            "limit": limit,
            "path": path,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"git_log_tool error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "UNKNOWN_ERROR",
        })


def git_diff_tool(path: str = None, staged: bool = False, task_id: str = None) -> str:
    """Get git diff for the repository or a specific file.

    Args:
        path: Optional file path to get diff for
        staged: Show staged changes (default: False)
    """
    try:
        if not _is_git_repository():
            return json.dumps({
                "success": False,
                "error": "Not inside a git repository",
                "error_code": "NOT_A_REPO",
            })

        cwd = os.getcwd()

        args = ["diff"]
        if staged:
            args.append("--cached")
        if path:
            args.append("--")
            args.append(path)

        diff_result = _run_git_command(args, cwd=cwd)

        if not diff_result["success"]:
            return json.dumps({
                "success": False,
                "error": diff_result["stderr"],
                "error_code": "DIFF_ERROR",
            })

        return json.dumps({
            "success": True,
            "diff": diff_result["stdout"],
            "has_changes": bool(diff_result["stdout"].strip()),
            "staged": staged,
            "path": path,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"git_diff_tool error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "UNKNOWN_ERROR",
        })


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

registry.register(
    name="git_status",
    toolset="git_workflow",
    schema={
        "name": "git_status",
        "description": "Get the current git status including branch, staged/unstaged changes, and untracked files.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    handler=lambda args, **kw: git_status_tool(task_id=kw.get("task_id")),
)

registry.register(
    name="git_branch_list",
    toolset="git_workflow",
    schema={
        "name": "git_branch_list",
        "description": "List all local git branches. Optionally include remote branches.",
        "parameters": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "boolean",
                    "description": "Include remote branches (default: False)",
                    "default": False,
                },
            },
        },
    },
    handler=lambda args, **kw: git_branch_list_tool(
        remote=args.get("remote", False),
        task_id=kw.get("task_id"),
    ),
)

registry.register(
    name="git_branch_create",
    toolset="git_workflow",
    schema={
        "name": "git_branch_create",
        "description": "Create a new git branch and optionally switch to it.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the branch to create",
                },
                "switch": {
                    "type": "boolean",
                    "description": "Switch to the new branch immediately (default: True)",
                    "default": True,
                },
            },
            "required": ["name"],
        },
    },
    handler=lambda args, **kw: git_branch_create_tool(
        name=args.get("name", ""),
        switch=args.get("switch", True),
        task_id=kw.get("task_id"),
    ),
)

registry.register(
    name="git_branch_delete",
    toolset="git_workflow",
    schema={
        "name": "git_branch_delete",
        "description": "Delete a local git branch.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the branch to delete",
                },
                "force": {
                    "type": "boolean",
                    "description": "Force delete even if branch has unmerged changes (default: False)",
                    "default": False,
                },
            },
            "required": ["name"],
        },
    },
    handler=lambda args, **kw: git_branch_delete_tool(
        name=args.get("name", ""),
        force=args.get("force", False),
        task_id=kw.get("task_id"),
    ),
)

registry.register(
    name="git_commit",
    toolset="git_workflow",
    schema={
        "name": "git_commit",
        "description": "Create a git commit with the specified files or all staged changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message describing the changes",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of files to commit (default: all staged files)",
                },
                "all": {
                    "type": "boolean",
                    "description": "Stage all modified files automatically (default: False)",
                    "default": False,
                },
            },
            "required": ["message"],
        },
    },
    handler=lambda args, **kw: git_commit_tool(
        message=args.get("message", ""),
        files=args.get("files"),
        all=args.get("all", False),
        task_id=kw.get("task_id"),
    ),
)

registry.register(
    name="git_log",
    toolset="git_workflow",
    schema={
        "name": "git_log",
        "description": "Get recent git commit history with author, date, and message.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of commits to return (default: 10)",
                    "default": 10,
                },
                "path": {
                    "type": "string",
                    "description": "Optional path to filter commits for a specific file or directory",
                },
            },
        },
    },
    handler=lambda args, **kw: git_log_tool(
        limit=args.get("limit", 10),
        path=args.get("path"),
        task_id=kw.get("task_id"),
    ),
)

registry.register(
    name="git_diff",
    toolset="git_workflow",
    schema={
        "name": "git_diff",
        "description": "Get git diff showing changes in the repository or a specific file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Optional file path to get diff for",
                },
                "staged": {
                    "type": "boolean",
                    "description": "Show staged changes instead of unstaged (default: False)",
                    "default": False,
                },
            },
        },
    },
    handler=lambda args, **kw: git_diff_tool(
        path=args.get("path"),
        staged=args.get("staged", False),
        task_id=kw.get("task_id"),
    ),
)
