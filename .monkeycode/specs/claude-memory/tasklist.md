# Claude Memory System - Implementation Task List

## Phase 1: Two-Tier Memory Storage Layer

- [ ] 1.1 Create tools/memory/ directory structure
  - Create tools/memory/__init__.py
  - Define module exports

- [ ] 1.2 Implement TwoTierMemory class in tools/memory/two_tier_memory.py
  - Implement __init__(base_path: Path) constructor
  - Implement store_working(obs: CompressedObservation) method
  - Implement store_archive(session_id: str, transcript: Transcript) method
  - Implement search(query: str, limit: int) -> List[SearchResult] method
  - Implement get_timeline(ids: List[str]) -> List[TimelineEntry] method
  - Implement get_observations(ids: List[str]) -> List[Observation] method
  - Implement get_stats() -> MemoryStats method

- [ ] 1.3 Define data models in tools/memory/models.py
  - Create CompressedObservation dataclass
  - Create Transcript dataclass
  - Create SearchResult dataclass
  - Create TimelineEntry dataclass
  - Create MemoryStats dataclass

- [ ] 1.4 Implement storage utilities
  - JSON file read/write helpers
  - File locking for concurrent access
  - Automatic directory creation

- [ ] 1.5 Write unit tests for TwoTierMemory
  - [ ]* Test store_working creates correct file structure
  - [ ]* Test store_archive creates correct archive structure
  - [ ]* Test search returns relevant results
  - [ ]* Test get_timeline returns correct timeline entries
  - [ ]* Test get_observations returns full observations

## Phase 2: AI Compression Observer

- [ ] 2.1 Implement CompressionObserver class in tools/memory/compression_observer.py
  - Implement __init__(llm_client) constructor
  - Implement observe(tool_result: ToolResult) -> CompressionResult method
  - Implement compress(text: str) -> CompressedObservation method
  - Implement _build_compression_prompt(text: str) -> str helper

- [ ] 2.2 Implement background worker
  - Create observation queue (asyncio.Queue)
  - Implement _worker() background task
  - Implement start() and stop() lifecycle methods
  - Ensure non-blocking tool execution

- [ ] 2.3 Implement LLM compression interface
  - Define compression prompt template
  - Handle LLM API calls
  - Parse compression results
  - Handle compression failures gracefully

- [ ] 2.4 Write unit tests for CompressionObserver
  - [ ]* Test observe queues compression request
  - [ ]* Test compress generates valid observation
  - [ ]* Test background worker processes queue
  - [ ]* Test compression failure handling

## Phase 3: CLAUDE.md Auto-Writer

- [ ] 3.1 Implement ClaudeMDWriter class in tools/memory/claude_md_writer.py
  - Implement __init__(memory_manager: MemoryManager) constructor
  - Implement learn_from_session(session_summary: SessionSummary) method
  - Implement update_claude_md(增量内容: str) method
  - Implement read_claude_md(project_path: Path) -> str method
  - Implement _parse_existing_claude_md(content: str) -> dict helper

- [ ] 3.2 Implement session summary extraction
  - Extract used tools from session
  - Extract modified files from session
  - Extract key decisions from session
  - Generate summary text

- [ ] 3.3 Implement CLAUDE.md merge logic
  - Read existing CLAUDE.md
  - Parse existing sections
  - Merge new content appropriately
  - Maintain CLAUDE.md format

- [ ] 3.4 Implement project path discovery
  - Find project root (.git directory)
  - Handle nested project structures
  - Skip vendor/node_modules directories

- [ ] 3.5 Write unit tests for ClaudeMDWriter
  - [ ]* Test learn_from_session extracts correct info
  - [ ]* Test update_claude_md merges correctly
  - [ ]* Test read_claude_md parses existing content
  - [ ]* Test project path discovery

## Phase 4: MCP Memory Server

- [ ] 4.1 Implement MCP memory tools in tools/memory/mcp_memory_tools.py
  - Implement memory_search_tool(query: str, limit: int) -> str
  - Implement memory_timeline_tool(ids: list) -> str
  - Implement memory_get_tool(ids: list) -> str
  - Implement memory_context_tool() -> str
  - Implement memory_stats_tool() -> str

- [ ] 4.2 Register MCP memory tools
  - Add registry.register() calls for each tool
  - Define tool schemas
  - Set correct toolset name

- [ ] 4.3 Implement tool handlers
  - memory_search handler - 调用 TwoTierMemory.search()
  - memory_timeline handler - 调用 TwoTierMemory.get_timeline()
  - memory_get handler - 调用 TwoTierMemory.get_observations()
  - memory_context handler - 调用 ClaudeMDWriter.read_claude_md()
  - memory_stats handler - 调用 TwoTierMemory.get_stats()

- [ ] 4.4 Write unit tests for MCP tools
  - [ ]* Test memory_search returns correct format
  - [ ]* Test memory_timeline returns correct format
  - [ ]* Test memory_get returns correct format
  - [ ]* Test memory_context returns CLAUDE.md content
  - [ ]* Test memory_stats returns correct stats

## Phase 5: Memory Manager Integration

- [ ] 5.1 Update agent/memory_manager.py
  - Integrate TwoTierMemory into MemoryManager
  - Add compression_enabled config option
  - Add auto_claude_md config option
  - Add mcp_memory_server config option

- [ ] 5.2 Add session end hook
  - Implement on_session_end() hook in MemoryManager
  - Trigger CLAUDE.md update on session end
  - Trigger archive of full transcript

- [ ] 5.3 Add tool execution hook
  - Implement after_tool_execution() hook
  - Queue observation for compression
  - Ensure non-blocking

- [ ] 5.4 Update config.py with new memory options
  - Add memory.auto_claude_md option
  - Add memory.compression_enabled option
  - Add memory.working_memory_limit option
  - Add memory.archive_memory_enabled option
  - Add memory.mcp_memory_server option
  - Bump _config_version to 20

- [ ] 5.5 Write integration tests
  - [ ]* Test MemoryManager integration with TwoTierMemory
  - [ ]* Test session end triggers CLAUDE.md update
  - [ ]* Test tool execution triggers compression
  - [ ]* Test MCP tools work end-to-end

## Phase 6: End-to-End Testing

- [ ] 6.1 Create integration test file
  - Create tests/tools/memory/test_memory_integration.py
  - Test full flow: tool use -> compression -> storage -> search

- [ ] 6.2 Run full test suite
  - Run all memory-related tests
  - Ensure no regressions

- [ ] 6.3 Checkpoint: 确保所有测试通过

## Non-Functional Requirements

- [ ] 7.1 Performance
  - Compression must be non-blocking
  - Search must return within 500ms for typical queries

- [ ] 7.2 Error Handling
  - LLM compression failures must not break tool execution
  - Storage failures must be logged and reported

- [ ] 7.3 Configuration
  - All features must be configurable via config.yaml
  - Environment variable overrides supported
