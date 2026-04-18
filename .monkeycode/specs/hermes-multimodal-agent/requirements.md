# Requirements Document - Hermes Multimodal Agent

## Introduction

基于 Hermes Agent 核心架构，整合 OpenCode、Claude Code、Codex 等优秀 AI Agent 的最佳特性，构建一个功能强大的综合型多模态 AI Agent。

## Glossary

- **Hermes Core**: Hermes Agent 的核心推理引擎（run_agent.py）
- **Tool**: 可被 AI 模型调用的外部工具
- **Toolset**: 工具的分组集合
- **Multimodal**: 多模态，支持多种输入输出形式
- **Auto Compact**: 自动上下文压缩（来自 OpenCode）
- **Auto Memory**: 自动学习项目知识（来自 Claude Code）
- **Skills Hub**: 技能市场，支持自定义技能（来自 Codex）
- **Sub-Agent**: 子代理，多任务协作（来自 Claude Code）

## Requirements

### REQ-001: 语音交互能力扩展

**User Story:** AS 用户, I want 能够通过语音与 Agent 对话, so that 我可以在双手忙碌时仍能与 Agent 交互

#### Acceptance Criteria

1. WHEN 用户上传音频文件, the system SHALL 调用 STT 工具将语音转为文本
2. WHEN Agent 需要以语音回复, the system SHALL 调用 TTS 工具将文本转为语音
3. WHEN 用户直接发送语音消息（通过 Messaging Gateway）, the system SHALL 自动转录后处理
4. WHILE 语音对话模式启用, the system SHALL 支持语音流式传输以降低延迟
5. WHEN 语音输入包含多说话者, the system SHALL 识别并标注不同说话者

---

### REQ-002: 图像理解能力扩展

**User Story:** AS 用户, I want 上传图片并获得分析结果, so that 我可以快速获取图像内容的理解和解答

#### Acceptance Criteria

1. WHEN 用户上传图片文件（PNG/JPG/GIF/WebP）, the system SHALL 将图片转为 base64 并调用 vision_analyze 工具
2. WHEN 图片包含图表或数据可视化, the system SHALL 提供详细的图表解读和数据提取
3. WHEN 图片包含文本内容, the system SHALL 支持 OCR 式的文本提取
4. WHEN 用户上传多张图片, the system SHALL 支持批量图像分析并整合结果
5. WHEN 用户对比两张图片差异, the system SHALL 标注关键差异点

---

### REQ-003: 文档处理能力扩展

**User Story:** AS 用户, I want 上传 PDF/Word/Excel 文档并与内容对话, so that 我可以快速从文档中提取信息和知识

#### Acceptance Criteria

1. WHEN 用户上传 PDF 文件, the system SHALL 调用 pdf_parser 工具提取文本内容和元数据
2. WHEN 用户上传 Word 文档, the system SHALL 调用 docx_parser 工具提取文本、表格和图片
3. WHEN 用户上传 Excel/CSV 文件, the system SHALL 调用 spreadsheet_parser 工具提取表格数据
4. WHEN 文档内容被提取后, the system SHALL 将内容注入对话上下文供模型分析
5. WHEN 用户搜索历史文档, the system SHALL 支持语义搜索已索引的文档

---

### REQ-004: 视频处理能力扩展

**User Story:** AS 用户, I want 上传视频并获得内容摘要, so that 我可以快速了解视频的主要内容

#### Acceptance Criteria

1. WHEN 用户上传视频文件, the system SHALL 调用 video_frame_extractor 工具按时间间隔提取关键帧
2. WHEN 关键帧被提取, the system SHALL 调用 vision_analyze 工具分析每帧内容
3. WHEN 视频分析完成, the system SHALL 生成视频内容摘要和时间线标注
4. WHEN 用户指定时间点, the system SHALL 支持跳转到指定位置并提取该帧
5. WHEN 用户需要视频关键事件, the system SHALL 自动检测场景切换和重要事件

---

### REQ-005: Auto Compact 自动上下文压缩 (来自 OpenCode)

**User Story:** AS 用户, I want Agent 自动压缩长对话上下文, so that 我不需要手动管理 context window

#### Acceptance Criteria

1. WHEN 对话 token 使用率达到 80%, the system SHALL 提示用户上下文即将压缩
2. WHEN 对话 token 使用率达到 95%, the system SHALL 自动触发上下文压缩
3. WHEN 压缩发生时, the system SHALL 使用 LLM 生成对话摘要
4. WHEN 压缩完成后, the system SHALL 创建新会话并保留摘要内容
5. WHEN 用户召回历史讨论, the system SHALL 能够从摘要恢复关键上下文

---

### REQ-006: Auto Memory 自动记忆系统 (来自 Claude Code)

**User Story:** AS 用户, I want Agent 自动学习项目知识, so that 它能越来越了解我的代码库

#### Acceptance Criteria

1. WHEN Agent 分析代码时发现项目模式, the system SHALL 自动保存到项目记忆
2. WHEN Agent 学习到构建命令或依赖, the system SHALL 更新项目上下文文件
3. WHEN 用户讨论了特定的图片或文档, the system SHALL 在记忆中保存引用
4. WHILE 对话进行, the system SHALL 增量更新用户偏好模型
5. WHEN 新会话开始, the system SHALL 自动加载相关项目记忆

---

### REQ-007: Skills Hub 技能系统增强 (来自 Codex)

**User Story:** AS 用户/开发者, I want 创建和分享自定义技能, so that 我可以复用成功的工作流

#### Acceptance Criteria

1. WHEN 开发者创建 `.codex/skills/` 目录, the system SHALL 识别并加载自定义技能
2. WHEN 技能被创建, the system SHALL 支持 SKILL.md 格式定义指令和示例
3. WHEN 用户执行 `/skill_name` 命令, the system SHALL 激活对应技能
4. WHEN 技能市场有更新, the system SHALL 支持从 agentskills.io 安装社区技能
5. WHEN 自定义技能包含参数, the system SHALL 支持交互式参数输入

---

### REQ-008: Sub-Agent 子代理协作 (来自 Claude Code)

**User Story:** AS 用户, I want Agent 能够分派任务给子代理, so that 可以并行处理复杂任务

#### Acceptance Criteria

1. WHEN 复杂任务被分解, the system SHALL 分派子任务给多个子代理并行执行
2. WHEN 子代理执行时, the system SHALL 支持专业分工（coder/reviewer/writer）
3. WHEN 子任务完成, the system SHALL 汇总结果生成综合回复
4. WHEN 子代理需要共享上下文, the system SHALL 支持跨代理内存访问
5. WHEN 用户指定子代理数量, the system SHALL 限制并行度以控制资源使用

---

### REQ-009: MCP 协议增强 (来自 OpenCode/Claude Code)

**User Story:** AS 开发者, I want 通过 MCP 协议扩展 Agent 能力, so that 我可以连接自定义工具和服务

#### Acceptance Criteria

1. WHEN MCP 服务器配置在 config.yaml, the system SHALL 自动发现并连接
2. WHEN MCP 工具被注册, the system SHALL 暴露给 LLM 可调用
3. WHEN MCP 连接断开, the system SHALL 自动重连并通知用户
4. WHEN 用户需要多模态扩展, the system SHALL 支持 vision/audio/document MCP 服务器

---

### REQ-010: 多模态工具集成

**User Story:** AS 开发者, I want 新工具能无缝集成到 Hermes 生态, so that 我可以灵活扩展多模态能力

#### Acceptance Criteria

1. WHEN 添加新的多模态工具, the system SHALL 支持通过 registry.register() 自动发现和注册
2. WHEN 多模态工具被注册, the system SHALL 自动生成对应的 tool schema 供模型调用
3. WHEN 工具需要额外依赖, the system SHALL 支持通过 check_fn 检查依赖可用性
4. WHEN 工具执行失败, the system SHALL 返回结构化的错误信息而非直接崩溃
5. WHEN 工具支持批处理, the system SHALL 标注 supports_batch=true 并支持分页

---

### REQ-011: 多模态工具集配置

**User Story:** AS 用户, I want 灵活启用/禁用特定的多模态工具, so that 我可以按需配置 Agent 能力

#### Acceptance Criteria

1. WHEN 用户配置 toolsets, the system SHALL 支持通过 `hermes tools` 命令启用/禁用多模态工具
2. WHEN 特定平台启用, the system SHALL 支持按平台配置不同的工具集
3. WHEN 工具依赖外部 API key, the system SHALL 在 key 缺失时优雅降级并提示用户
4. WHEN 工具执行超时, the system SHALL 支持可配置的超时时间
5. WHEN 批量工具处理大文件, the system SHALL 支持进度回调和取消

---

### REQ-012: 多模态记忆管理

**User Story:** AS 用户, I want 多模态交互的记忆被持久化, so that Agent 能记住之前的图像、文档讨论等

#### Acceptance Criteria

1. WHEN 用户讨论了特定的图片或文档, the system SHALL 在记忆中保存引用而非完整内容
2. WHEN 用户召回之前的讨论, the system SHALL 能从记忆中的引用重新加载内容
3. WHILE 对话上下文压缩, the system SHALL 优先保留多模态内容的引用和摘要
4. WHEN 多模态内容被删除, the system SHALL 更新相关记忆引用

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Hermes Multimodal Agent                            │
│              (整合 OpenCode + Claude Code + Codex 最佳特性)          │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │   Voice     │  │   Image     │  │   Document                  │ │
│  │   Tools     │  │   Tools     │  │   Tools                     │ │
│  │             │  │             │  │                             │ │
│  │ • STT/TTS   │  │ • Vision   │  │ • PDF/Word/Excel Parser    │ │
│  │ • Streaming │  │ • OCR      │  │ • Semantic Search          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Advanced Features (Competitor Best Practices)      │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ │   │
│  │  │Auto Compact│ │Auto Memory│ │ Skills Hub │ │ Sub-Agents│ │   │
│  │  │ (OpenCode) │ │(Claude)   │ │  (Codex)  │ │ (Claude)  │ │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Multimodal Tool Registry                           │   │
│  │         (tools/registry.py - auto-discovery)                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   Hermes Core (run_agent.py)                    │   │
│  │              • AIAgent • Tool Calling Loop • MCP Client        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    LLM Providers                               │   │
│  │   OpenRouter • Anthropic • OpenAI • Ollama • Nous Portal     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## Competitor Feature Mapping

| Feature | Source | Hermes Integration |
|---------|--------|-------------------|
| Auto Compact | OpenCode | `agent/context_compressor.py` 增强 |
| Custom Commands | OpenCode | `hermes_cli/skills_hub.py` 扩展 |
| MCP Integration | OpenCode | `tools/mcp_tool.py` 增强 |
| Multi-Surface | Claude Code | `gateway/` 已有 |
| Sub-Agents | Claude Code | `tools/delegate_tool.py` 增强 |
| Routines | Claude Code | `cron/` 已有 |
| CLAUDE.md Memory | Claude Code | `agent/context_files.py` 扩展 |
| Auto Memory | Claude Code | `agent/auto_memory.py` 新增 |
| Skills System | Codex | `skills/` 已有 + 扩展 |
| IDE Integration | Codex | `acp_adapter/` 已有 |

## References

- Hermes Agent: https://github.com/NousResearch/hermes-agent
- OpenCode: https://github.com/opencode-ai/opencode
- Claude Code: https://github.com/anthropics/claude-code
- Codex CLI: https://github.com/openai/codex
