"""CLAUDE.md Auto-Writer for Hermes Memory System.

This module provides automatic CLAUDE.md file generation and updates,
extracting project knowledge from session activities.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.memory.models import SessionSummary

logger = logging.getLogger(__name__)

try:
    from agent.codebase_analyzer import CodebaseAnalyzer
    CODEBASE_ANALYZER_AVAILABLE = True
except ImportError:
    CODEBASE_ANALYZER_AVAILABLE = False
    CodebaseAnalyzer = None


DEFAULT_CLAUDE_md_TEMPLATE = """# 项目上下文

{project_overview}

## 项目结构

{project_structure}

## 代码规范

{coding_standards}

## 最近活动

{recent_activities}

## 技术决策

{technical_decisions}

---
*此文件由 Claude Memory System 自动生成*
"""


class ClaudeMDWriter:
    """Automatically generates and updates CLAUDE.md files.
    
    This class extracts project knowledge from sessions and maintains
    a CLAUDE.md file in the project root with relevant context.
    """
    
    def __init__(self, project_paths: Optional[List[Path]] = None):
        """Initialize ClaudeMDWriter.
        
        Args:
            project_paths: List of project paths to monitor. If None, auto-detect.
        """
        self.project_paths = project_paths or []
        self._cache: Dict[Path, Dict[str, Any]] = {}
    
    def add_project_path(self, path: Path) -> None:
        """Add a project path to monitor.
        
        Args:
            path: Project root path.
        """
        if path not in self.project_paths:
            self.project_paths.append(path)
    
    def find_project_root(self, start_path: Path) -> Optional[Path]:
        """Find project root by looking for git/.git directory.
        
        Args:
            start_path: Starting path for search.
        
        Returns:
            Project root path or None if not found.
        """
        current = start_path.resolve()
        
        while current != current.parent:
            if (current / ".git").exists() or (current / ".hg").exists():
                return current
            current = current.parent
        
        return None
    
    def read_claude_md(self, project_path: Path) -> Tuple[str, bool]:
        """Read existing CLAUDE.md content.
        
        Args:
            project_path: Project root path.
        
        Returns:
            Tuple of (content, exists).
        """
        claude_md = project_path / "CLAUDE.md"
        
        if not claude_md.exists():
            return "", False
        
        try:
            content = claude_md.read_text(encoding="utf-8")
            return content, True
        except IOError as e:
            logger.warning(f"Failed to read CLAUDE.md: {e}")
            return "", False
    
    def _parse_existing_claude_md(self, content: str) -> Dict[str, Any]:
        """Parse existing CLAUDE.md into sections.
        
        Args:
            content: CLAUDE.md content.
        
        Returns:
            Dict mapping section names to content.
        """
        sections: Dict[str, Any] = {
            "project_overview": "",
            "project_structure": "",
            "coding_standards": "",
            "recent_activities": [],
            "technical_decisions": [],
        }
        
        current_section = None
        lines = content.split("\n")
        
        for line in lines:
            header_match = re.match(r"^## (.+)$", line)
            if header_match:
                section_name = header_match.group(1).strip().lower().replace(" ", "_")
                if section_name in sections:
                    current_section = section_name
                continue
            
            if current_section == "recent_activities" and line.strip():
                sections["recent_activities"].append(line.strip())
            elif current_section == "technical_decisions" and line.strip():
                sections["technical_decisions"].append(line.strip())
            elif current_section and sections.get(current_section, "") == "":
                sections[current_section] = line.strip()
        
        return sections
    
    def _generate_activity_entry(self, summary: SessionSummary) -> str:
        """Generate a CLAUDE.md activity entry.
        
        Args:
            summary: Session summary.
        
        Returns:
            Formatted activity entry.
        """
        date = datetime.fromisoformat(summary.date.replace("Z", "+00:00"))
        date_str = date.strftime("%Y-%m-%d")
        
        parts = [f"- {date_str}:"]
        
        if summary.tools_used:
            tools = ", ".join(summary.tools_used[:5])
            parts.append(f"  使用工具: {tools}")
        
        if summary.files_modified:
            files = ", ".join(summary.files_modified[:3])
            if len(summary.files_modified) > 3:
                files += f" 等{len(summary.files_modified)}个文件"
            parts.append(f"  修改文件: {files}")
        
        if summary.key_outcomes:
            outcome = summary.key_outcomes[0]
            parts.append(f"  {outcome}")
        
        return "\n".join(parts)
    
    def _update_section(
        self,
        existing_content: str,
        section_name: str,
        new_entries: List[str],
        max_entries: int = 20,
    ) -> str:
        """Update a section in CLAUDE.md with new entries.
        
        Args:
            existing_content: Current CLAUDE.md content.
            section_name: Name of section to update.
            new_entries: New entries to add.
            max_entries: Maximum entries to keep.
        
        Returns:
            Updated content.
        """
        lines = existing_content.split("\n")
        
        section_start = -1
        section_end = -1
        
        for i, line in enumerate(lines):
            if re.match(rf"^## {section_name.replace('_', ' ').title()}$", line, re.IGNORECASE):
                section_start = i
            elif section_start >= 0 and section_end < 0 and line.startswith("## "):
                section_end = i
                break
        
        if section_start < 0:
            return existing_content
        
        if section_end < 0:
            section_end = len(lines)
        
        new_section_lines = []
        for entry in new_entries[:max_entries]:
            new_section_lines.append(entry)
        
        new_content = "\n".join([
            "\n".join(lines[:section_start]),
            f"## {section_name.replace('_', ' ').title()}",
            *new_section_lines,
            "\n".join(lines[section_end:]),
        ])
        
        return new_content
    
    async def learn_from_session(self, summary: SessionSummary) -> List[Path]:
        """Learn from a session and update CLAUDE.md files.
        
        Args:
            summary: Session summary.
        
        Returns:
            List of updated project paths.
        """
        updated_paths = []
        
        for project_path in self.project_paths:
            try:
                await self.update_claude_md(project_path, summary)
                updated_paths.append(project_path)
            except Exception as e:
                logger.error(f"Failed to update CLAUDE.md for {project_path}: {e}")
        
        return updated_paths
    
    async def update_claude_md(
        self,
        project_path: Path,
        summary: SessionSummary,
    ) -> None:
        """Update CLAUDE.md with session information.
        
        Args:
            project_path: Project root path.
            summary: Session summary.
        """
        claude_md_path = project_path / "CLAUDE.md"
        
        existing_content, exists = self.read_claude_md(project_path)
        
        if not exists:
            content = self._generate_initial_claude_md(summary)
        else:
            content = self._update_claude_md_with_summary(existing_content, summary)
        
        try:
            claude_md_path.write_text(content, encoding="utf-8")
            logger.info(f"Updated CLAUDE.md at {claude_md_path}")
        except IOError as e:
            logger.error(f"Failed to write CLAUDE.md: {e}")
            raise
    
    def _generate_initial_claude_md(self, summary: SessionSummary) -> str:
        """Generate initial CLAUDE.md content.
        
        Args:
            summary: First session summary.
        
        Returns:
            CLAUDE.md content.
        """
        date = datetime.fromisoformat(summary.date.replace("Z", "+00:00"))
        date_str = date.strftime("%Y-%m-%d")
        
        activity = self._generate_activity_entry(summary)
        
        return DEFAULT_CLAUDE_md_TEMPLATE.format(
            project_overview="基于 Claude Memory System 的项目",
            project_structure="项目结构待补充",
            coding_standards="编码规范待补充",
            recent_activities=f"{activity}\n- {date_str}: 会话开始",
            technical_decisions="技术决策待补充",
        )
    
    def _update_claude_md_with_summary(
        self,
        existing_content: str,
        summary: SessionSummary,
    ) -> str:
        """Update existing CLAUDE.md with session summary.
        
        Args:
            existing_content: Current CLAUDE.md content.
            summary: Session summary.
        
        Returns:
            Updated content.
        """
        new_entry = self._generate_activity_entry(summary)
        
        content = self._update_section(
            existing_content,
            "recent_activities",
            [new_entry],
            max_entries=20,
        )
        
        return content
    
    def detect_claude_md_locations(self, start_path: Path) -> List[Path]:
        """Detect all CLAUDE.md locations from a starting path.
        
        Args:
            start_path: Starting path for search.
        
        Returns:
            List of paths with CLAUDE.md files.
        """
        locations = []
        current = start_path.resolve()
        
        while current != current.parent:
            claude_md = current / "CLAUDE.md"
            if claude_md.exists():
                locations.append(current)
            
            vendor_or_dep = (
                current / "node_modules"
            ).exists() or (current / "vendor").exists()
            
            if vendor_or_dep:
                break
            
            current = current.parent
        
        return locations
    
    def extract_project_info(self, project_path: Path) -> Dict[str, Any]:
        """Extract project information from files.
        
        Args:
            project_path: Project root path.
        
        Returns:
            Dict with project info.
        """
        info: Dict[str, Any] = {
            "name": project_path.name,
            "languages": [],
            "frameworks": [],
            "has_tests": False,
            "has_docs": False,
        }
        
        if (project_path / "package.json").exists():
            info["languages"].append("JavaScript/TypeScript")
            try:
                import json
                pkg = json.loads((project_path / "package.json").read_text())
                deps = pkg.get("dependencies", {})
                for dep in deps:
                    if "react" in dep.lower():
                        info["frameworks"].append("React")
                    elif "vue" in dep.lower():
                        info["frameworks"].append("Vue")
                    elif "next" in dep.lower():
                        info["frameworks"].append("Next.js")
            except Exception:
                pass
        
        if (project_path / "Cargo.toml").exists():
            info["languages"].append("Rust")
        
        if (project_path / "requirements.txt").exists() or (project_path / "pyproject.toml").exists():
            info["languages"].append("Python")
        
        info["has_tests"] = any([
            (project_path / "tests").exists(),
            (project_path / "test").exists(),
            list(project_path.glob("*_test.py")),
            list(project_path.glob("*.test.js")),
        ])
        
        info["has_docs"] = any([
            (project_path / "docs").exists(),
            (project_path / "doc").exists(),
            (project_path / "README.md").exists(),
        ])
        
        return info
    
    def analyze_and_update_structure(self, project_path: Path) -> Optional[str]:
        """Analyze project structure and update CLAUDE.md.
        
        Uses CodebaseAnalyzer to automatically detect project languages,
        frameworks, and structure, then updates the project_structure
        section in CLAUDE.md.
        
        Args:
            project_path: Project root path.
        
        Returns:
            Updated project structure content or None if update failed.
        """
        if not CODEBASE_ANALYZER_AVAILABLE:
            logger.warning("CodebaseAnalyzer not available")
            return None
        
        try:
            analyzer = CodebaseAnalyzer(str(project_path))
            structure_content = analyzer.format_for_claude_md()
            
            existing_content, exists = self.read_claude_md(project_path)
            
            if not exists:
                return None
            
            lines = existing_content.split("\n")
            
            section_start = -1
            section_end = -1
            section_name = "project_structure"
            
            for i, line in enumerate(lines):
                if re.match(r"^## 项目结构$", line, re.IGNORECASE):
                    section_start = i
                elif section_start >= 0 and section_end < 0 and line.startswith("## "):
                    section_end = i
                    break
            
            if section_start < 0:
                return None
            
            if section_end < 0:
                section_end = len(lines)
            
            new_lines = lines[:section_start + 1]
            new_lines.append(structure_content)
            new_lines.append("")
            new_lines.extend(lines[section_end:])
            
            new_content = "\n".join(new_lines)
            
            claude_md_path = project_path / "CLAUDE.md"
            claude_md_path.write_text(new_content, encoding="utf-8")
            logger.info(f"Updated CLAUDE.md project structure at {claude_md_path}")
            
            return structure_content
            
        except Exception as e:
            logger.error(f"Failed to analyze and update structure: {e}")
            return None
