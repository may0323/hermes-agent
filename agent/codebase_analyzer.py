"""Codebase Analyzer for Hermes Agent.

This module provides automatic project structure analysis and code pattern detection
to enhance the agent's understanding of the codebase it works in.

Features:
- Project structure analysis
- Programming language detection
- Framework and dependency detection
- Code convention extraction
- Entry point identification
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript (React)",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".r": "R",
    ".R": "R",
    ".m": "Objective-C/MATLAB",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".less": "LESS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
}

FRAMEWORK_PATTERNS = {
    "django": ["django", "settings.py", "manage.py", "wsgi.py", "asgi.py"],
    "flask": ["flask", "app.route", "@app.route", "Flask("],
    "fastapi": ["fastapi", "FastAPI(", "@app.get", "@app.post"],
    "pyramid": ["pyramid", "configurator"],
    "tornado": ["tornado", "tornado.web", "tornado.ioloop"],
    "bottle": ["bottle", "Bottle("],
    "cherrypy": ["cherrypy"],
    "web2py": ["web2py"],
    "react": ["react", "React", "create-react-app", "jsx", "tsx"],
    "vue": ["vue", "Vue", ".vue"],
    "angular": ["angular", "@angular/core", "ngModule", "angular.json"],
    "next": ["next", "next.js", "getServerSideProps", "getStaticProps"],
    "nuxt": ["nuxt", "nuxt.config"],
    "svelte": ["svelte", "Svelte"],
    "express": ["express", "express()", "app.get", "app.post"],
    "fastify": ["fastify", "Fastify("],
    "koa": ["koa", "Koa("],
    "hapi": ["hapi"],
    "sails": ["sails"],
    "nest": ["@nestjs/core", "nest"],
    "spring": ["org.springframework", "spring-boot", "@SpringBootApplication"],
    "play": ["playframework", "play"],
    "rails": ["rails", "Rails", "config/routes.rb", "config/application.rb"],
    "sinatra": ["sinatra", "Sinatra"],
    "laravel": ["laravel", "Illuminate", "artisan"],
    "symfony": ["symfony", "Symfony"],
    "django-rest": ["rest_framework", "DRF", "Serializers"],
    "next": ["next.js", "Next.js"],
    "gatsby": ["gatsby", "Gatsby"],
    "remix": ["remix", "Remix"],
    "astro": ["astro", "Astro"],
    "solid": ["solid-js", "Solid"],
    "qwik": ["qwik", "Qwik"],
}

CONFIG_FILES = {
    "package.json": "npm/Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python (Poetry)",
    "setup.py": "Python (Setuptools)",
    "setup.cfg": "Python (Setuptools)",
    "Pipfile": "Python (Pipenv)",
    "poetry.lock": "Python (Poetry)",
    "go.mod": "Go",
    "go.sum": "Go",
    "Cargo.toml": "Rust",
    "Cargo.lock": "Rust",
    "Gemfile": "Ruby",
    "Gemfile.lock": "Ruby",
    "composer.json": "PHP (Composer)",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java (Gradle)",
    "build.gradle.kts": "Kotlin/Gradle",
    "gradle.properties": "Gradle",
    "gradlew": "Gradle",
    "makefile": "Make",
    "CMakeLists.txt": "CMake",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    ".env.example": "Environment Variables",
    "tsconfig.json": "TypeScript",
    "jsconfig.json": "JavaScript",
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "webpack.config.js": "Webpack",
    "next.config.js": "Next.js",
    "next.config.ts": "Next.js",
    "nuxt.config.ts": "Nuxt",
    "svelte.config.js": "Svelte",
    "astro.config.mjs": "Astro",
    "rome.json": "Rome",
    ".eslintrc": "ESLint",
    ".eslintrc.js": "ESLint",
    "eslint.config.js": "ESLint",
    "prettierrc": "Prettier",
    "prettier.config.js": "Prettier",
    "pyrightconfig.json": "Pyright",
    "mypy.ini": "MyPy",
    ".browserslistrc": "Browserslist",
    "browserslist": "Browserslist",
    ".nvmrc": "Node Version Manager",
    ".node-version": "Node Version Manager",
    "rust-toolchain.toml": "Rust",
    ".tool-versions": "asdf",
}

IGNORE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "out",
    "target",
    "coverage",
    ".tox",
    ".nox",
    "venv",
    "env",
    ".env",
    ".venv",
    ".eggs",
    "*.egg-info",
    ".sass-cache",
    ".next",
    ".nuxt",
    ".output",
    ".cache",
    ".parcel-cache",
    "__pypackages__",
    "vendor",
    "bower_components",
    "jspm_packages",
    ".idea",
    ".vscode",
    ".settings",
    "*.swp",
    "*.swo",
    "*~",
}

ENTRY_POINT_PATTERNS = {
    "python": [
        (r"if\s+__name__\s*==\s*['\"]__main__['\"]", "main block"),
        (r"def\s+main\s*\(", "main() function"),
    ],
    "javascript": [
        (r"module\.exports\s*=", "module.exports"),
        (r"export\s+default\s+", "default export"),
        (r"export\s+{.*}\s+from", "named exports"),
    ],
    "go": [
        (r"func\s+main\s*\(", "main() function"),
    ],
    "rust": [
        (r"fn\s+main\s*\(", "main() function"),
    ],
}


class CodebaseAnalyzer:
    """Analyze project structure and extract code patterns.

    Usage:
        analyzer = CodebaseAnalyzer(project_path="/path/to/project")
        result = analyzer.analyze()
    """

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = Path(project_path or os.getcwd()).resolve()
        self._language_counts: Dict[str, int] = {}
        self._framework_matches: Dict[str, List[str]] = {}
        self._config_files: List[str] = []
        self._entry_points: List[Dict[str, str]] = []
        self._subdirs: List[str] = []
        self._readme_content: Optional[str] = None

    def analyze(self) -> Dict[str, Any]:
        """Perform full codebase analysis.

        Returns a dictionary with:
        - languages: detected programming languages
        - frameworks: detected frameworks
        - config: detected configuration files
        - entry_points: detected entry points
        - structure: directory structure summary
        - conventions: detected code conventions
        """
        self._scan_directory(self.project_path)

        return {
            "languages": self._detect_languages(),
            "frameworks": self._detect_frameworks(),
            "config_files": self._config_files,
            "entry_points": self._entry_points,
            "structure": self._summarize_structure(),
            "readme": self._readme_content,
        }

    def _scan_directory(self, directory: Path, depth: int = 0, max_depth: int = 3) -> None:
        """Recursively scan directory for language files and patterns."""
        if depth > max_depth:
            return

        try:
            entries = list(directory.iterdir())
        except (OSError, PermissionError):
            return

        for entry in entries:
            name = entry.name

            if entry.is_dir():
                if name in IGNORE_DIRS or name.startswith("."):
                    continue
                self._subdirs.append(str(entry.relative_to(self.project_path)))
                self._scan_directory(entry, depth + 1, max_depth)
                continue

            if entry.is_file():
                suffix = entry.suffix.lower()
                if suffix in LANGUAGE_EXTENSIONS:
                    self._language_counts[suffix] = self._language_counts.get(suffix, 0) + 1

                filename = name.lower()
                for config_name, config_type in CONFIG_FILES.items():
                    if filename == config_name.lower():
                        self._config_files.append(f"{config_type}: {name}")
                        self._analyze_config_file(entry)

                if suffix == ".py":
                    self._analyze_python_file(entry)
                elif suffix in (".js", ".ts", ".jsx", ".tsx"):
                    self._analyze_js_file(entry)

    def _analyze_config_file(self, path: Path) -> None:
        """Analyze a config file for framework hints."""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:5000]
            filename = path.name.lower()

            for framework, patterns in FRAMEWORK_PATTERNS.items():
                for pattern in patterns:
                    if pattern.lower() in content.lower():
                        if framework not in self._framework_matches:
                            self._framework_matches[framework] = []
                        if filename not in self._framework_matches[framework]:
                            self._framework_matches[framework].append(filename)

            if filename in ("readme.md", "readme.rst", "readme"):
                self._readme_content = content[:2000]
        except (OSError, UnicodeDecodeError):
            pass

    def _analyze_python_file(self, path: Path) -> None:
        """Analyze Python file for entry points and conventions."""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:3000]

            for pattern, description in ENTRY_POINT_PATTERNS.get("python", []):
                if re.search(pattern, content):
                    rel_path = str(path.relative_to(self.project_path))
                    self._entry_points.append({
                        "file": rel_path,
                        "type": "python",
                        "description": description,
                    })
                    break
        except (OSError, UnicodeDecodeError):
            pass

    def _analyze_js_file(self, path: Path) -> None:
        """Analyze JavaScript/TypeScript file for entry points."""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:3000]

            for pattern, description in ENTRY_POINT_PATTERNS.get("javascript", []):
                if re.search(pattern, content):
                    rel_path = str(path.relative_to(self.project_path))
                    self._entry_points.append({
                        "file": rel_path,
                        "type": "js/ts",
                        "description": description,
                    })
                    break
        except (OSError, UnicodeDecodeError):
            pass

    def _detect_languages(self) -> List[Dict[str, Any]]:
        """Convert language counts to sorted list of detected languages."""
        languages = []
        for ext, count in sorted(self._language_counts.items(), key=lambda x: x[1], reverse=True):
            languages.append({
                "extension": ext,
                "name": LANGUAGE_EXTENSIONS.get(ext, ext),
                "file_count": count,
            })
        return languages

    def _detect_frameworks(self) -> List[Dict[str, Any]]:
        """Convert framework matches to sorted list."""
        frameworks = []
        for framework, files in sorted(self._framework_matches.items(), key=lambda x: len(x[1]), reverse=True):
            frameworks.append({
                "name": framework,
                "matched_files": files,
                "confidence": "high" if len(files) >= 2 else "medium" if len(files) == 1 else "low",
            })
        return frameworks

    def _summarize_structure(self) -> Dict[str, Any]:
        """Generate a summary of the project structure."""
        top_level_dirs = []
        for i, subdir in enumerate(self._subdirs):
            if "/" not in subdir:
                top_level_dirs.append(subdir)
            if i > 50:
                top_level_dirs.append("...")
                break

        return {
            "root": str(self.project_path.name),
            "top_level_dirs": sorted(set(top_level_dirs))[:20],
            "total_dirs_scanned": len(self._subdirs),
        }

    def format_for_claude_md(self) -> str:
        """Format analysis results for CLAUDE.md.

        Returns a markdown string suitable for appending to CLAUDE.md.
        """
        analysis = self.analyze()

        lines = ["## 项目结构\n"]

        if analysis["languages"]:
            lang_lines = [f"- **{lang['name']}**: {lang['file_count']} files" for lang in analysis["languages"]]
            lines.append("\n**编程语言:**")
            lines.extend(lang_lines[:5])

        if analysis["frameworks"]:
            fw_lines = [f"- **{fw['name']}**" for fw in analysis["frameworks"]]
            lines.append("\n**框架/库:**")
            lines.extend(fw_lines[:5])

        if analysis["config_files"]:
            lines.append("\n**配置文件:**")
            for cfg in analysis["config_files"][:5]:
                lines.append(f"- {cfg}")

        if analysis["entry_points"]:
            lines.append("\n**入口点:**")
            for ep in analysis["entry_points"][:3]:
                lines.append(f"- `{ep['file']}`: {ep['description']}")

        if analysis["structure"]["top_level_dirs"]:
            lines.append("\n**主要目录:**")
            for d in analysis["structure"]["top_level_dirs"][:10]:
                lines.append(f"- `{d}/`")

        return "\n".join(lines)
