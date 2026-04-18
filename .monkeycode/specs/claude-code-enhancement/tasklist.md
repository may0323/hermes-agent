# Hermes Agent - Claude Code 能力增强实施计划

## 目标

将 Claude Code 的核心能力增强添加到 Hermes Agent 框架中，重点关注：
1. Git Workflows 集成
2. 代码库理解增强
3. SessionStart Hooks 增强
4. 多端同步能力

## 现有能力分析

### 已完成 (Claude Memory System Phase 1-6)
- ✅ TwoTierMemory 存储层
- ✅ AI Compression Observer
- ✅ CLAUDE.md Auto-Writer
- ✅ MCP Memory Tools (search/timeline/get)
- ✅ MemoryManager 集成
- ✅ 35 个测试全部通过

### 已有 Hooks (需增强)
- ✅ `on_session_end` - 会话结束钩子
- ✅ `on_turn_start` - Turn 开始钩子
- ✅ `on_pre_compress` - 压缩前钩子
- ✅ `on_delegation` - 委托完成钩子
- ❌ `on_session_start` - **会话开始钩子（缺失）**

### 已有 Git 相关
- ✅ `terminal_tool` - 可执行 git 命令
- ❌ 专用 Git Workflow 工具

---

## 任务列表

### 1. SessionStart Hooks 增强

- [ ] 1.1 在 `agent/memory_manager.py` 添加 `on_session_start` 钩子
  - 定义 `on_session_start(self, session_id: str, **kwargs) -> None` 方法
  - 通知所有 provider 会话开始
  - 触发 CLAUDE.md 加载和 memory 预热

- [ ] 1.2 在 `agent/memory_provider.py` 添加 `on_session_start` 接口
  - 为所有 provider 定义 `on_session_start` 方法签名
  - 内置 provider 实现会话开始时的 memory 加载

- [ ] 1.3 在 `run_agent.py` 的会话初始化中调用 `on_session_start`
  - 在 `run_conversation` 开始时调用
  - 传递 session_id 和项目上下文

- [ ] 1.4 添加测试
  - [ ]* 测试 on_session_start 钩子调用
  - [ ]* 测试 provider 预热逻辑

### 2. Git Workflows 集成

- [ ] 2.1 创建 `tools/git_workflow_tool.py`
  - 实现 `git_branch_list()` - 列出分支
  - 实现 `git_branch_create(name: str)` - 创建分支
  - 实现 `git_branch_delete(name: str)` - 删除分支
  - 实现 `git_commit(message: str, files: List[str])` - 提交更改
  - 实现 `git_status()` - 获取状态
  - 实现 `git_log(limit: int)` - 获取提交日志

- [ ] 2.2 注册 Git workflow 工具
  - 在 `toolsets.py` 添加 `git_workflow` toolset
  - 添加工具注册到 `registry`

- [ ] 2.3 实现 branch 命名规范 (遵循 auto-create-branch-on-master.md)
  - 自动生成符合规范的分支名
  - 支持 feat/fix/chore/refactor 类型

- [ ] 2.4 添加 Git 安全检查
  - 检测危险操作 (force push, dangerous rebases)
  - 防止意外的数据丢失

- [ ] 2.5 添加测试
  - [ ]* 测试 git_branch_list
  - [ ]* 测试 git_branch_create
  - [ ]* 测试 git_commit
  - [ ]* 测试安全检查

### 3. 代码库理解增强

- [ ] 3.1 增强 `agent/subdirectory_hints.py`
  - 添加项目结构扫描
  - 识别主要编程语言
  - 检测框架和依赖

- [ ] 3.2 创建 `agent/codebase_analyzer.py`
  - 分析项目目录结构
  - 识别代码模式 (patterns)
  - 提取关键文件和模块

- [ ] 3.3 增强 CLAUDE.md Writer
  - 添加项目结构摘要
  - 自动识别入口点
  - 记录代码约定

- [ ] 3.4 集成到 SessionStart
  - 在会话开始时自动分析项目
  - 将分析结果注入 system prompt

- [ ] 3.5 添加测试
  - [ ]* 测试代码库结构分析
  - [ ]* 测试模式识别
  - [ ]* 测试 CLAUDE.md 更新

### 4. 多端同步能力 (Gateway 增强)

- [ ] 4.1 增强 `gateway/session.py`
  - 添加跨会话状态同步
  - 支持 session 恢复

- [ ] 4.2 实现 Session 共享
  - 多端访问同一会话
  - 消息同步

- [ ] 4.3 添加配置选项
  - `gateway.multi_device_sync`
  - `gateway.session_persistence`

- [ ] 4.4 添加测试
  - [ ]* 测试会话恢复
  - [ ]* 测试状态同步

### 5. 配置增强

- [ ] 5.1 更新 `hermes_cli/config.py`
  - 添加 `memory.on_session_start_preload` 配置
  - 添加 `git.workflow_enabled` 配置
  - 添加 `codebase.auto_analyze` 配置
  - Bump `_config_version`

- [ ] 5.2 添加环境变量支持
  - `HERMES_SESSION_START_PRELOAD`
  - `HERMES_GIT_WORKFLOW_ENABLED`

### 6. 检查点

- [ ] 确保所有新增测试通过
- [ ] 确保不破坏现有功能
- [ ] 更新 AGENTS.md 文档

---

## 技术细节

### SessionStart Hook 时序

```
run_conversation()
  └── on_session_start(session_id, project_path, cwd)
        ├── BuiltinMemoryProvider.on_session_start()
        │     ├── Load CLAUDE.md
        │     ├── Prefetch recent memories
        │     └── Analyze codebase structure
        ├── ExternalMemoryProvider.on_session_start() (if configured)
        └── Update session metadata
```

### Git Workflow Tool Schema

```python
registry.register(
    name="git_branch_list",
    toolset="git_workflow",
    schema={
        "name": "git_branch_list",
        "description": "List all local and remote git branches",
        "parameters": {...}
    },
    handler=lambda args, **kw: git_branch_list_tool(...),
)

registry.register(
    name="git_commit",
    toolset="git_workflow",
    schema={
        "name": "git_commit",
        "description": "Create a git commit with the specified files",
        "parameters": {
            "properties": {
                "message": {"type": "string", "description": "Commit message"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "Files to commit"}
            },
            "required": ["message", "files"]
        }
    },
    handler=lambda args, **kw: git_commit_tool(...),
)
```

---

## 依赖关系

```
Phase 1 (SessionStart Hooks)
  └── Phase 2 (Git Workflows)
        └── Phase 3 (Codebase Understanding)
              └── Phase 4 (Multi-device Sync)
                    └── Phase 5 (Config)
```

## 风险与注意事项

1. **Prompt Caching**: SessionStart Hooks 不能破坏现有的 prompt caching 机制
2. **性能**: 代码库分析应在后台异步执行
3. **向后兼容**: 所有新增配置应有默认值，不破坏现有功能
