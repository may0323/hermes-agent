# Claude Memory System - Technical Design

Feature Name: claude-memory
Date: 2026-04-18

## Description

为 Hermes Agent 实现完整的 Claude Code Memory 系统，包括：
1. CLAUDE.md 自动写入 - 自动学习项目知识
2. Two-Tier Memory - Working Memory + Archive Memory
3. AI Compression Observer - 工具使用后自动生成压缩观察
4. MCP Memory Server - 三层搜索 (Search → Timeline → Get)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes Memory System                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  CLAUDE.md   │    │ Working Mem  │    │ Archive Mem  │  │
│  │  Auto-Write  │    │  (Compressed)│    │ (Full Trans) │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Memory Manager (统一协调)                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ MCP Memory   │  │ AI Compress │  │ Session      │      │
│  │ Search Tools │  │ Observer    │  │ Integration  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Data Models

### 1. Compressed Observation Schema
```json
{
  "id": "obs_20260418_001",
  "timestamp": "2026-04-18T10:30:00Z",
  "session_id": "xxx",
  "compression": "ai",
  "ratio": "15:1",
  "summary": "添加了 PDF 并行解析，优化后性能提升 3x",
  "entities": ["PDFParserTool", "ThreadPoolExecutor"],
  "patterns": ["性能优化", "并行处理"],
  "importance": "high",
  "original_tokens": 5000,
  "compressed_tokens": 350
}
```

### 2. Two-Tier Storage Structure
```
~/.hermes/memories/
├── claude.md              # 项目上下文 (自动维护)
├── working/
│   ├── 2026-04-18.json   # 压缩观察 (每个会话一个)
│   └── 2026-04-17.json
└── archive/
    ├── 2026-04/
    │   ├── session_xxx.json  # 完整转录
    │   └── session_yyy.json
    └── 2026-03/
```

## MCP Memory Tools

### Layer 1: Search
```python
memory_search(query: str, limit: int = 5) -> {
    "results": [
        {"id": "obs_xxx", "score": 0.95, "preview": "添加了PDF解析..."},
    ]
}
```

### Layer 2: Timeline
```python
memory_timeline(ids: list[str]) -> {
    "timelines": [
        {
            "id": "obs_xxx",
            "timestamp": "2026-04-18T10:30:00Z",
            "session_id": "s_xxx",
            "context": "该观察来自会话..."
        }
    ]
}
```

### Layer 3: Get
```python
memory_get(ids: list[str]) -> {
    "observations": [
        {
            "id": "obs_xxx",
            "full_text": "完整压缩后的观察内容...",
            "entities": [...],
            "patterns": [...]
        }
    ]
}
```

## Configuration

```python
"memory": {
    "auto_claude_md": True,           # 自动写入 CLAUDE.md
    "compression_enabled": True,       # AI 压缩观察
    "working_memory_limit": 5000,      # Working memory tokens
    "archive_memory_enabled": True,    # 归档记忆
    "mcp_memory_server": False,        # MCP Memory Server
}
```

## Implementation Components

| Component | File | Purpose |
|-----------|------|---------|
| TwoTierMemory | tools/memory/two_tier_memory.py | 双层存储管理 |
| CompressionObserver | tools/memory/compression_observer.py | AI 压缩 |
| ClaudeMDWriter | tools/memory/claude_md_writer.py | CLAUDE.md 自动写入 |
| MCPMemoryServer | tools/memory/mcp_memory_server.py | MCP 搜索工具 |
| MemoryIntegration | agent/memory_manager.py (增强) | 现有系统集成 |
