"""AI Compression Observer for Hermes Memory System.

This module provides AI-powered compression of tool observations,
converting detailed tool outputs into concise semantic summaries.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from tools.memory.models import CompressedObservation, generate_observation_id

logger = logging.getLogger(__name__)


COMPRESSION_PROMPT = """You are a memory compression system. Your task is to analyze tool execution results and create concise, informative summaries.

## Input Analysis
- Original text: Analyze the content and extract key information
- Tool context: Understand what the tool did
- Patterns: Identify recurring themes or patterns

## Output Requirements
Create a summary with these components:
1. **summary**: A 1-2 sentence description of what happened (in the user's language)
2. **entities**: Key technical terms, file names, class names, function names
3. **patterns**: Themes, methodologies, or recurring concepts
4. **importance**: "high", "medium", or "low" based on likely future relevance

## Guidelines
- Preserve the most important technical details
- Use the same language as the input content
- Be concise - target 50-200 characters for summary
- Focus on actionable and reusable information

## Output Format (JSON)
```json
{
  "summary": "Brief description of what happened",
  "entities": ["entity1", "entity2"],
  "patterns": ["pattern1", "pattern2"],
  "importance": "high|medium|low"
}
```

## Input to analyze:
{input_text}

## Your analysis (respond with JSON only):"""


@dataclass
class CompressionResult:
    """Result from AI compression."""
    success: bool
    observation: Optional[CompressedObservation] = None
    error: Optional[str] = None
    original_tokens: int = 0
    compressed_tokens: int = 0


class CompressionObserver:
    """Observes tool executions and generates AI-compressed observations.
    
    This class queues tool results and processes them asynchronously
    to generate compressed observations without blocking tool execution.
    """
    
    def __init__(
        self,
        llm_client: Optional[Callable] = None,
        queue_size: int = 100,
        worker_count: int = 2,
    ):
        """Initialize CompressionObserver.
        
        Args:
            llm_client: Async callable that takes a prompt and returns LLM response.
                       If None, uses heuristic compression as fallback.
            queue_size: Maximum queue size for pending compressions.
            worker_count: Number of background workers.
        """
        self.llm_client = llm_client
        self.queue_size = queue_size
        self.worker_count = worker_count
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._compression_count = 0
        self._compression_errors = 0
    
    async def start(self) -> None:
        """Start background compression workers."""
        if self._running:
            return
        
        self._running = True
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(worker_id=i))
            self._workers.append(worker)
        
        logger.info(f"Started {self.worker_count} compression workers")
    
    async def stop(self) -> None:
        """Stop background compression workers."""
        if not self._running:
            return
        
        self._running = False
        
        for _ in range(self.worker_count):
            await self._queue.put(None)
        
        for worker in self._workers:
            await worker
        
        self._workers.clear()
        logger.info("Stopped compression workers")
    
    async def observe(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: str,
        session_id: str,
    ) -> str:
        """Queue a tool result for compression.
        
        This method returns immediately after queuing - compression
        happens asynchronously in the background.
        
        Args:
            tool_name: Name of the tool.
            tool_args: Arguments passed to the tool.
            tool_result: Result from tool execution.
            session_id: Current session ID.
        
        Returns:
            Observation ID (will be populated after compression).
        """
        obs_id = generate_observation_id()
        
        item = {
            "obs_id": obs_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            self._queue.put_nowait(item)
            logger.debug(f"Queued observation {obs_id} for compression")
        except asyncio.QueueFull:
            logger.warning("Compression queue full, skipping observation")
            self._compression_errors += 1
        
        return obs_id
    
    async def _worker(self, worker_id: int) -> None:
        """Background worker that processes compression queue."""
        logger.debug(f"Compression worker {worker_id} started")
        
        while self._running:
            try:
                item = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                
                if item is None:
                    break
                
                await self._process_compression(item)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Compression worker {worker_id} error: {e}")
        
        logger.debug(f"Compression worker {worker_id} stopped")
    
    async def _process_compression(self, item: Dict[str, Any]) -> None:
        """Process a single compression request."""
        try:
            if self.llm_client:
                result = await self._ai_compress(
                    input_text=item["tool_result"],
                    tool_name=item["tool_name"],
                )
            else:
                result = await self._heuristic_compress(
                    input_text=item["tool_result"],
                    tool_name=item["tool_name"],
                )
            
            if result.success:
                self._compression_count += 1
                ratio = "1:1"
                if result.compressed_tokens > 0 and result.original_tokens > 0:
                    ratio = f"{result.original_tokens // result.compressed_tokens}:1"
                logger.debug(f"Compressed observation {item['obs_id']}: {ratio}")
            else:
                self._compression_errors += 1
                logger.warning(f"Compression failed for {item['obs_id']}: {result.error}")
                
        except Exception as e:
            self._compression_errors += 1
            logger.error(f"Error processing compression: {e}")
    
    async def _ai_compress(
        self,
        input_text: str,
        tool_name: str,
    ) -> CompressionResult:
        """Compress text using AI (LLM).
        
        Args:
            input_text: Text to compress.
            tool_name: Name of the tool for context.
        
        Returns:
            CompressionResult with compressed observation.
        """
        original_tokens = self._estimate_tokens(input_text)
        
        prompt = COMPRESSION_PROMPT.format(input_text=input_text[:4000])
        
        try:
            response = await self.llm_client(prompt)
            
            text_response = ""
            if isinstance(response, dict):
                text_response = response.get("content", "")
            elif hasattr(response, "content"):
                text_response = response.content
            else:
                text_response = str(response)
            
            parsed = self._parse_compression_response(text_response)
            
            compressed_tokens = self._estimate_tokens(parsed.get("summary", ""))
            
            ratio = "1:1"
            if compressed_tokens > 0 and original_tokens > 0:
                ratio = f"{original_tokens // compressed_tokens}:1"
            
            obs = CompressedObservation(
                id=generate_observation_id(),
                timestamp=datetime.now(timezone.utc).isoformat(),
                compression="ai",
                ratio=ratio,
                summary=parsed.get("summary", ""),
                entities=parsed.get("entities", []),
                patterns=parsed.get("patterns", []),
                importance=parsed.get("importance", "medium"),
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                tool_name=tool_name,
            )
            
            return CompressionResult(
                success=True,
                observation=obs,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
            )
            
        except Exception as e:
            return CompressionResult(
                success=False,
                error=str(e),
                original_tokens=original_tokens,
            )
    
    async def _heuristic_compress(
        self,
        input_text: str,
        tool_name: str,
    ) -> CompressionResult:
        """Fallback heuristic compression when LLM is not available.
        
        Args:
            input_text: Text to compress.
            tool_name: Name of the tool for context.
        
        Returns:
            CompressionResult with heuristically compressed observation.
        """
        original_tokens = self._estimate_tokens(input_text)
        
        lines = input_text.strip().split("\n")
        first_lines = lines[:5] if len(lines) > 5 else lines
        summary = " ".join(first_lines)[:200]
        
        entities = self._extract_entities(input_text)
        patterns = self._extract_patterns(input_text)
        
        importance = "medium"
        if any(kw in input_text.lower() for kw in ["error", "exception", "failed"]):
            importance = "high"
        elif len(input_text) > 10000:
            importance = "high"
        elif len(input_text) < 100:
            importance = "low"
        
        compressed_tokens = self._estimate_tokens(summary)
        ratio = "1:1"
        if compressed_tokens > 0 and original_tokens > 0:
            ratio = f"{original_tokens // compressed_tokens}:1"
        
        obs = CompressedObservation(
            id=generate_observation_id(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            compression="heuristic",
            ratio=ratio,
            summary=summary,
            entities=entities,
            patterns=patterns,
            importance=importance,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            tool_name=tool_name,
        )
        
        return CompressionResult(
            success=True,
            observation=obs,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
        )
    
    def _parse_compression_response(self, text: str) -> Dict[str, Any]:
        """Parse LLM compression response.
        
        Args:
            text: Raw LLM response text.
        
        Returns:
            Parsed dict with summary, entities, patterns, importance.
        """
        text = text.strip()
        
        json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if json_match:
            try:
                import json
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        lines = text.split("\n")
        result = {
            "summary": "",
            "entities": [],
            "patterns": [],
            "importance": "medium",
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith("summary:") or line.startswith("- summary:"):
                result["summary"] = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("entities:") or line.startswith("- entities:"):
                pass
            elif line.startswith("patterns:") or line.startswith("- patterns:"):
                pass
            elif line.startswith("importance:") or line.startswith("- importance:"):
                imp = line.split(":", 1)[1].strip().strip('"')
                if imp in ("high", "medium", "low"):
                    result["importance"] = imp
        
        if not result["summary"] and text:
            result["summary"] = text[:200]
        
        return result
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract technical entities from text.
        
        Args:
            text: Text to analyze.
        
        Returns:
            List of entity names.
        """
        import re
        
        patterns = [
            r'\b[A-Z][a-z]+[A-Z][a-zA-Z]+\b',
            r'\b[a-z_]+\.[a-z_]+\b',
            r'\b[class|def|function|method]\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'`([^`]+)`',
            r'["\'](/[\w/.-]+)["\']',
        ]
        
        entities = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            entities.update(matches)
        
        return list(entities)[:20]
    
    def _extract_patterns(self, text: str) -> List[str]:
        """Extract patterns/themes from text.
        
        Args:
            text: Text to analyze.
        
        Returns:
            List of pattern names.
        """
        pattern_keywords = {
            "性能优化": ["optimize", "performance", "fast", "efficient", "优化", "性能"],
            "并行处理": ["parallel", "concurrent", "async", "并行", "并发"],
            "错误处理": ["error", "exception", "handle", "错误", "异常"],
            "API调用": ["api", "endpoint", "request", "api", "调用"],
            "数据处理": ["parse", "process", "transform", "parse", "处理"],
            "测试": ["test", "mock", "verify", "测试", "验证"],
            "配置": ["config", "setting", "configure", "配置", "设置"],
        }
        
        text_lower = text.lower()
        found_patterns = []
        
        for pattern_name, keywords in pattern_keywords.items():
            if any(kw in text_lower for kw in keywords):
                found_patterns.append(pattern_name)
        
        return found_patterns[:5]
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation).
        
        Args:
            text: Text to count.
        
        Returns:
            Estimated token count.
        """
        return len(text) // 4 + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics.
        
        Returns:
            Dict with compression stats.
        """
        return {
            "compression_count": self._compression_count,
            "compression_errors": self._compression_errors,
            "queue_size": self._queue.qsize(),
            "workers_running": len(self._workers),
        }
