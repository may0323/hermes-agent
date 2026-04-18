# Hermes Multimodal Agent - 工作任务分解

**项目**: Hermes Multimodal Agent  
**日期**: 2026-04-18  
**分支策略**: 每个模块独立分支，并行开发

---

## 分支清单

| 模块 | 分支名 | 测试覆盖率 | 负责人 |
|------|--------|------------|--------|
| Document Tools | `quede-feat-document-tools` | >95% | Dev A |
| Image Tools | `quede-feat-image-tools` | >95% | Dev A |
| Auto Memory | `quede-feat-auto-memory` | >95% | Dev B |
| Sub-Agents | `quede-feat-subagents` | >95% | Dev B |
| Skills Hub | `quede-feat-skills-hub` | >95% | Dev C |
| MCP Enhancement | `quede-feat-mcp-enhancement` | >95% | Dev C |
| Video Tools | `quede-feat-video-tools` | >95% | Dev D |
| Voice Tools | `quede-feat-voice-tools` | >95% | Dev D |

---

## Team A: Document + Image Tools

### Week 1: Document Tools (Day 1-5)

| Task ID | 任务 | 工时 | 验收标准 | 输出物 |
|---------|------|------|----------|--------|
| A1.1 | PDF Parser 基础 | 2d | 文本提取测试 >95% | `tools/pdf_parser_tool.py` |
| A1.2 | Word Parser | 1.5d | 表格提取测试 >95% | `tools/docx_parser_tool.py` |
| A1.3 | Excel/CSV Parser | 1.5d | 数据完整性 >95% | `tools/spreadsheet_parser_tool.py` |
| A1.4 | Document Index | 1.5d | 语义搜索 >90% | `tools/document_index_tool.py` |
| A1.5 | Toolset 集成 | 0.5d | CLI 注册正常 | `toolsets.py` 更新 |

### Week 2: Image Tools (Day 6-10)

| Task ID | 任务 | 工时 | 验收标准 | 输出物 |
|---------|------|------|----------|--------|
| A2.1 | OCR Tool | 2d | 中英文 >95% | `tools/ocr_tool.py` |
| A2.2 | Batch Analyze | 1.5d | 批量测试 >95% | `tools/image_batch_analyze.py` |
| A2.3 | Image Compare | 1.5d | 差异检测 >90% | `tools/image_compare.py` |
| A2.4 | Chart Understanding | 1.5d | 图表解读 >90% | `tools/chart_understanding.py` |
| A2.5 | Toolset 集成 | 0.5d | CLI 注册正常 | `toolsets.py` 更新 |

### 测试要求

```
单元测试文件:
- tests/tools/test_pdf_parser.py       (覆盖率 >95%)
- tests/tools/test_docx_parser.py      (覆盖率 >95%)
- tests/tools/test_spreadsheet.py      (覆盖率 >95%)
- tests/tools/test_document_index.py    (覆盖率 >95%)
- tests/tools/test_ocr_tool.py         (覆盖率 >95%)
- tests/tools/test_image_batch.py      (覆盖率 >95%)
- tests/tools/test_image_compare.py    (覆盖率 >95%)
- tests/tools/test_chart_understanding.py (覆盖率 >95%)
```

---

## Team B: Auto Memory + Sub-Agents

### Week 1-2: Auto Memory (Day 1-7)

| Task ID | 任务 | 工时 | 验收标准 | 输出物 |
|---------|------|------|----------|--------|
| B1.1 | AutoMemory 基础架构 | 1.5d | 核心类测试 >95% | `agent/auto_memory.py` |
| B1.2 | 模式检测引擎 | 2d | 框架检测 >95% | `agent/memory/pattern_detector.py` |
| B1.3 | 记忆持久化 | 1.5d | 跨会话 >95% | `agent/memory/persistence.py` |
| B1.4 | CLI 命令 | 1d | 命令测试 >95% | `hermes_cli/memory_commands.py` |
| B1.5 | Agent 集成 | 1d | 上下文集成 >90% | `agent/memory/integration.py` |

### Week 3: Sub-Agents (Day 8-12)

| Task ID | 任务 | 工时 | 验收标准 | 输出物 |
|---------|------|------|----------|--------|
| B2.1 | AgentType 扩展 | 1d | 枚举测试 >95% | `tools/delegate_tool.py` 更新 |
| B2.2 | 共享内存 | 1.5d | 线程安全 >95% | `agent/subagent_memory.py` |
| B2.3 | 结果汇总器 | 1d | 汇总逻辑 >95% | `agent/subagent_aggregator.py` |
| B2.4 | 并行执行器 | 1.5d | 并发测试 >95% | `agent/parallel_executor.py` |
| B2.5 | CLI 管理命令 | 0.5d | 命令测试 >95% | `hermes_cli/agent_commands.py` |
| B2.6 | 集成测试 | 1.5d | E2E 测试 >95% | 完整流程测试 |

### 测试要求

```
单元测试文件:
- tests/agent/test_auto_memory.py           (覆盖率 >95%)
- tests/agent/test_pattern_detector.py      (覆盖率 >95%)
- tests/agent/test_memory_persistence.py     (覆盖率 >95%)
- tests/tools/test_delegate_tool.py          (覆盖率 >95%)
- tests/agent/test_subagent_memory.py       (覆盖率 >95%)
- tests/agent/test_subagent_aggregator.py   (覆盖率 >95%)
- tests/agent/test_parallel_executor.py      (覆盖率 >95%)
```

---

## Team C: Skills Hub + MCP Enhancement

### Week 1: Skills Hub (Day 1-5)

| Task ID | 任务 | 工时 | 验收标准 | 输出物 |
|---------|------|------|----------|--------|
| C1.1 | Codex 兼容层 | 1.5d | 格式兼容 >95% | `hermes_cli/codex_compat.py` |
| C1.2 | 参数系统 | 1.5d | 参数验证 >95% | `hermes_cli/skills_config.py` |
| C1.3 | 市场客户端 | 1.5d | API 测试 >90% | `hermes_cli/marketplace.py` |
| C1.4 | CLI 命令 | 0.5d | 命令测试 >95% | `hermes_cli/skills_commands.py` |
| C1.5 | 版本管理 | 0.5d | 版本测试 >95% | `hermes_cli/skill_version.py` |

### Week 2: MCP Enhancement (Day 6-12)

| Task ID | 任务 | 工时 | 验收标准 | 输出物 |
|---------|------|------|----------|--------|
| C2.1 | 传输层抽象 | 1.5d | 三种传输 >95% | `tools/mcp_transport.py` |
| C2.2 | 连接管理器 | 1.5d | 连接管理 >95% | `tools/mcp_connection.py` |
| C2.3 | 健康监控 | 1d | 重连测试 >95% | `tools/mcp_health.py` |
| C2.4 | SSE/WS 支持 | 1.5d | 连接测试 >95% | `tools/mcp_tool.py` 更新 |
| C2.5 | CLI 管理命令 | 0.5d | 命令测试 >95% | `hermes_cli/mcp_commands.py` |
| C2.6 | 集成测试 | 1d | E2E 测试 >95% | 完整流程测试 |

### 测试要求

```
单元测试文件:
- tests/hermes_cli/test_codex_compat.py     (覆盖率 >95%)
- tests/hermes_cli/test_skills_config.py    (覆盖率 >95%)
- tests/hermes_cli/test_marketplace.py      (覆盖率 >95%)
- tests/hermes_cli/test_skill_version.py    (覆盖率 >95%)
- tests/tools/test_mcp_transport.py          (覆盖率 >95%)
- tests/tools/test_mcp_connection.py         (覆盖率 >95%)
- tests/tools/test_mcp_health.py             (覆盖率 >95%)
```

---

## Team D: Video + Voice Tools

### Week 1-2: Video Tools (Day 1-7)

| Task ID | 任务 | 工时 | 验收标准 | 输出物 |
|---------|------|------|----------|--------|
| D1.1 | Frame Extractor | 2d | 帧提取 >95% | `tools/video_frame_extractor.py` |
| D1.2 | Video Analyzer | 1.5d | 摘要生成 >90% | `tools/video_analyzer.py` |
| D1.3 | Timeline Generator | 1.5d | 时间线 >90% | `tools/video_timeline.py` |
| D1.4 | Toolset 集成 | 0.5d | CLI 注册正常 | `toolsets.py` 更新 |
| D1.5 | 集成测试 | 1.5d | E2E 测试 >95% | 完整流程测试 |

### Week 3: Voice Tools (Day 8-12)

| Task ID | 任务 | 工时 | 验收标准 | 输出物 |
|---------|------|------|----------|--------|
| D2.1 | Audio Streaming | 3d | 流式测试 >95% | `tools/audio_streaming.py` |
| D2.2 | Voice Activity Detection | 1.5d | VAD 测试 >95% | `tools/voice_activity_detection.py` |
| D2.3 | Audio Processing | 1.5d | 格式转换 >95% | `tools/audio_processing.py` |
| D2.4 | 集成测试 | 1.5d | E2E 测试 >95% | 完整流程测试 |

### 测试要求

```
单元测试文件:
- tests/tools/test_video_frame_extractor.py  (覆盖率 >95%)
- tests/tools/test_video_analyzer.py         (覆盖率 >95%)
- tests/tools/test_video_timeline.py         (覆盖率 >95%)
- tests/tools/test_audio_streaming.py        (覆盖率 >95%)
- tests/tools/test_voice_activity_detection.py (覆盖率 >95%)
- tests/tools/test_audio_processing.py       (覆盖率 >95%)
```

---

## 里程碑

| 里程碑 | 日期 | 交付内容 | 验收 |
|--------|------|----------|------|
| M1 | Day 5 | Document Tools v1.0 | 测试 >95% |
| M2 | Day 10 | Image Tools v1.0 | 测试 >95% |
| M3 | Day 7 | Auto Memory v1.0 | 测试 >95% |
| M4 | Day 12 | Sub-Agents v1.0 | 测试 >95% |
| M5 | Day 5 | Skills Hub v1.0 | 测试 >95% |
| M6 | Day 12 | MCP Enhancement v1.0 | 测试 >95% |
| M7 | Day 7 | Video Tools v1.0 | 测试 >95% |
| M8 | Day 12 | Voice Tools v1.0 | 测试 >95% |
| M9 | Day 14 | 集成测试 + 文档 | 全部模块联调 |

---

## 代码合并流程

```
1. 开发分支完成 → 创建 PR
2. CI 检查 (lint + test + coverage)
3. 代码审查 (至少 1 人)
4. 合并到 main
```

### PR 必须满足

| 检查项 | 要求 |
|--------|------|
| 覆盖率 | > 95% |
| lint | `ruff` 通过 |
| 类型检查 | `mypy` 通过 |
| 测试 | 全部通过 |
| 审查 | 至少 1 人 approve |

---

## 每日站会内容

每个团队需要报告：

1. **昨日完成**: 完成了哪些任务
2. **今日计划**: 计划完成哪些任务
3. **阻塞问题**: 有哪些阻碍

---

## 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 依赖冲突 | 中 | 中 | 锁定版本，CI 检测 |
| 接口变更 | 高 | 高 | 定期同步，及时沟通 |
| 覆盖率不达标 | 中 | 高 | 每日检查，早发现早修复 |
| 集成失败 | 中 | 高 | 预留集成缓冲时间 |

---

## 通讯录

| 角色 | 职责 | 联系方式 |
|------|------|----------|
| Dev A | Document + Image Tools | - |
| Dev B | Auto Memory + Sub-Agents | - |
| Dev C | Skills Hub + MCP | - |
| Dev D | Video + Voice Tools | - |
