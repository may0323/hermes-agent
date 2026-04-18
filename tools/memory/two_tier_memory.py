"""Two-tier memory storage system.

Working Memory: Compressed observations (fast, in-context)
Archive Memory: Full transcripts (complete, searchable)
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hermes_constants import get_hermes_home

from tools.memory.models import (
    CompressedObservation,
    MemoryStats,
    SearchResult,
    TimelineEntry,
    Transcript,
    generate_observation_id,
)

logger = logging.getLogger(__name__)


class TwoTierMemory:
    """Two-tier memory: Working (compressed) + Archive (full).
    
    Storage structure:
        ~/.hermes/memories/
        ├── working/
        │   ├── 2026-04-18.json   # One file per day
        │   └── 2026-04-17.json
        └── archive/
            ├── 2026-04/
            │   ├── session_xxx.json
            │   └── session_yyy.json
            └── 2026-03/
    """
    
    WORKING_DIR = "memories/working"
    ARCHIVE_DIR = "memories/archive"
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize TwoTierMemory.
        
        Args:
            base_path: Base path for memory storage. Defaults to ~/.hermes
        """
        self.base_path = base_path or get_hermes_home()
        self.working_path = self.base_path / self.WORKING_DIR
        self.archive_path = self.base_path / self.ARCHIVE_DIR
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.working_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)
    
    def _get_working_file(self, date: Optional[str] = None) -> Path:
        """Get the working memory file for a given date.
        
        Args:
            date: Date string (YYYY-MM-DD). Defaults to today.
        
        Returns:
            Path to the working file.
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.working_path / f"{date}.json"
    
    def _get_archive_dir(self, year_month: str) -> Path:
        """Get the archive directory for a given year-month.
        
        Args:
            year_month: Year-month string (YYYY-MM).
        
        Returns:
            Path to the archive directory.
        """
        return self.archive_path / year_month
    
    def _load_working_file(self, path: Path) -> List[Dict[str, Any]]:
        """Load observations from a working file.
        
        Args:
            path: Path to the working file.
        
        Returns:
            List of observation dicts.
        """
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load working file {path}: {e}")
            return []
    
    def _save_working_file(self, path: Path, observations: List[Dict[str, Any]]) -> None:
        """Save observations to a working file.
        
        Args:
            path: Path to the working file.
            observations: List of observation dicts.
        """
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(observations, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save working file {path}: {e}")
            raise
    
    def _parse_search_query(self, query: str) -> List[str]:
        """Parse search query into keywords.
        
        Args:
            query: Search query string.
        
        Returns:
            List of keywords.
        """
        import unicodedata
        
        keywords: List[str] = []
        current_word = []
        
        for char in query.lower():
            if char.isalnum() or char in ('_', '-'):
                current_word.append(char)
            else:
                if current_word:
                    word = ''.join(current_word)
                    if len(word) > 2:
                        keywords.append(word)
                    current_word = []
        
        if current_word:
            word = ''.join(current_word)
            if len(word) > 2:
                keywords.append(word)
        
        if not keywords:
            keywords = [query.lower().strip()]
        
        return keywords
    
    def _calculate_relevance(self, observation: Dict[str, Any], keywords: List[str]) -> float:
        """Calculate relevance score for an observation.
        
        Args:
            observation: Observation dict.
            keywords: Search keywords.
        
        Returns:
            Relevance score (0-1).
        """
        if not keywords:
            return 0.0
        
        text = " ".join([
            observation.get("summary", ""),
            observation.get("tool_name", ""),
            " ".join(observation.get("entities", [])),
            " ".join(observation.get("patterns", [])),
        ]).lower()
        
        matches = sum(1 for kw in keywords if kw in text)
        return matches / len(keywords)
    
    async def store_working(self, obs: CompressedObservation) -> str:
        """Store a compressed observation in working memory.
        
        Args:
            obs: Compressed observation to store.
        
        Returns:
            Observation ID.
        """
        date = datetime.fromisoformat(obs.timestamp.replace("Z", "+00:00"))
        date_str = date.strftime("%Y-%m-%d")
        working_file = self._get_working_file(date_str)
        
        observations = self._load_working_file(working_file)
        observations.append(obs.to_dict())
        
        self._save_working_file(working_file, observations)
        logger.debug(f"Stored observation {obs.id} in working memory")
        
        return obs.id
    
    async def store_archive(self, session_id: str, transcript: Transcript) -> str:
        """Store a full transcript in archive memory.
        
        Args:
            session_id: Session ID.
            transcript: Full transcript to archive.
        
        Returns:
            Archive path.
        """
        start = datetime.fromisoformat(transcript.start_time.replace("Z", "+00:00"))
        year_month = start.strftime("%Y-%m")
        
        archive_dir = self._get_archive_dir(year_month)
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        archive_file = archive_dir / f"{session_id}.json"
        
        try:
            with open(archive_file, "w", encoding="utf-8") as f:
                json.dump(transcript.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"Archived transcript for session {session_id}")
        except IOError as e:
            logger.error(f"Failed to archive transcript: {e}")
            raise
        
        return str(archive_file)
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        importance_filter: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Search working memory.
        
        Args:
            query: Search query.
            limit: Maximum number of results.
            importance_filter: Filter by importance levels.
        
        Returns:
            List of search results.
        """
        keywords = self._parse_search_query(query)
        if not keywords:
            return []
        
        all_observations: List[Tuple[Path, Dict[str, Any]]] = []
        
        for working_file in self.working_path.glob("*.json"):
            observations = self._load_working_file(working_file)
            for obs in observations:
                all_observations.append((working_file, obs))
        
        all_observations.sort(
            key=lambda x: datetime.fromisoformat(
                x[1].get("timestamp", "1970-01-01").replace("Z", "+00:00")
            ),
            reverse=True,
        )
        
        scored_results: List[Tuple[SearchResult, float]] = []
        
        for _, obs in all_observations:
            if importance_filter and obs.get("importance") not in importance_filter:
                continue
            
            score = self._calculate_relevance(obs, keywords)
            if score > 0:
                preview = obs.get("summary", "")[:100]
                result = SearchResult(
                    id=obs.get("id", ""),
                    score=score,
                    preview=preview,
                    timestamp=obs.get("timestamp", ""),
                    importance=obs.get("importance", "medium"),
                )
                scored_results.append((result, score))
        
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        return [result for result, _ in scored_results[:limit]]
    
    async def get_timeline(self, ids: List[str]) -> List[TimelineEntry]:
        """Get timeline entries for observations.
        
        Args:
            ids: List of observation IDs.
        
        Returns:
            List of timeline entries.
        """
        id_set = set(ids)
        timeline: List[TimelineEntry] = []
        
        for working_file in self.working_path.glob("*.json"):
            observations = self._load_working_file(working_file)
            for obs in observations:
                if obs.get("id") in id_set:
                    tool_name = obs.get("tool_name", "unknown")
                    summary = obs.get("summary", "")
                    context = f"[{tool_name}] {summary}" if summary else tool_name
                    
                    entry = TimelineEntry(
                        id=obs.get("id", ""),
                        timestamp=obs.get("timestamp", ""),
                        session_id=obs.get("session_id", ""),
                        context=context,
                        importance=obs.get("importance", "medium"),
                    )
                    timeline.append(entry)
        
        timeline.sort(
            key=lambda x: datetime.fromisoformat(x.timestamp.replace("Z", "+00:00")),
            reverse=True,
        )
        
        return timeline
    
    async def get_observations(self, ids: List[str]) -> List[CompressedObservation]:
        """Get full observations by IDs.
        
        Args:
            ids: List of observation IDs.
        
        Returns:
            List of compressed observations.
        """
        id_set = set(ids)
        observations: List[CompressedObservation] = []
        
        for working_file in self.working_path.glob("*.json"):
            obs_list = self._load_working_file(working_file)
            for obs_dict in obs_list:
                if obs_dict.get("id") in id_set:
                    observations.append(CompressedObservation.from_dict(obs_dict))
        
        return observations
    
    async def get_stats(self) -> MemoryStats:
        """Get memory system statistics.
        
        Returns:
            Memory statistics.
        """
        total_working = 0
        total_working_tokens = 0
        total_archive = 0
        total_compressed_tokens = 0
        total_original_tokens = 0
        latest_timestamp = ""
        
        for working_file in self.working_path.glob("*.json"):
            observations = self._load_working_file(working_file)
            for obs in observations:
                total_working += 1
                compressed = obs.get("compressed_tokens", 0)
                original = obs.get("original_tokens", 0)
                total_working_tokens += compressed
                total_compressed_tokens += compressed
                total_original_tokens += original
                ts = obs.get("timestamp", "")
                if ts and (not latest_timestamp or ts > latest_timestamp):
                    latest_timestamp = ts
        
        for archive_dir in self.archive_path.rglob("*.json"):
            if archive_dir.is_file():
                total_archive += 1
        
        ratio = "1:1"
        if total_compressed_tokens > 0 and total_original_tokens > 0:
            ratio = f"{total_original_tokens // total_compressed_tokens}:1"
        
        return MemoryStats(
            working_count=total_working,
            working_tokens=total_working_tokens,
            archive_count=total_archive,
            compression_ratio=ratio,
            last_updated=latest_timestamp,
        )
    
    async def cleanup_old_archives(self, older_than_days: int = 90) -> int:
        """Clean up archives older than specified days.
        
        Args:
            older_than_days: Delete archives older than this many days.
        
        Returns:
            Number of files deleted.
        """
        deleted = 0
        cutoff = datetime.now(timezone.utc).timestamp() - (older_than_days * 86400)
        
        for archive_dir in self.archive_path.iterdir():
            if not archive_dir.is_dir():
                continue
            
            for archive_file in archive_dir.glob("*.json"):
                if archive_file.stat().st_mtime < cutoff:
                    try:
                        archive_file.unlink()
                        deleted += 1
                    except OSError as e:
                        logger.warning(f"Failed to delete {archive_file}: {e}")
        
        return deleted
