# Hermes Multimodal Agent 工具文档

本文档描述 Hermes Agent 新增的多模态 AI 工具集。

## 概述

Hermes Multimodal Agent 整合了 8 大模块，共 **37 个工具**，涵盖文档处理、图像分析、视频处理、音频处理、记忆增强、子代理并行执行、技能管理和 MCP 协议增强。

## 工具集总览

| 工具集 | 工具数 | 描述 |
|--------|--------|------|
| `document` | 6 | 文档解析 (PDF, Word, Excel) |
| `image` | 7 | 图像处理 (OCR, 批量分析, 比较) |
| `video` | 6 | 视频处理 (帧提取, 分析, 缩略图) |
| `voice` | 4 | 音频处理 (格式转换, 裁剪) |
| `memory` | 4 | 记忆增强 (摘要, 实体提取) |
| `subagents` | 3 | 并行执行 (委托, 聚合) |
| `skills` | 4 | 技能管理 (列表, 搜索, 详情) |
| `mcp` | 3 | MCP 协议增强 (传输, 连接, 健康) |

---

## Document Tools (`document`)

文档处理工具集，支持 PDF、Word、Excel 等常见文档格式。

### parse_pdf

解析 PDF 文件并提取文本内容。

```python
parse_pdf_tool(file_path: str, max_pages: int = None, start_page: int = 1)
```

**参数:**
- `file_path`: PDF 文件路径
- `max_pages`: 最大页数限制
- `start_page`: 起始页码

**返回:**
```json
{
  "success": true,
  "data": {
    "text": "提取的文本内容...",
    "page_count": 10,
    "metadata": {...}
  }
}
```

### get_pdf_info

获取 PDF 文件的元信息。

```python
get_pdf_info_tool(file_path: str)
```

### parse_docx

解析 Word 文档 (.docx)。

```python
parse_docx_tool(file_path: str, extract_images: bool = False)
```

### parse_spreadsheet

解析电子表格 (Excel/CSV)。

```python
parse_spreadsheet_tool(
    file_path: str,
    sheet_index: int = 0,
    max_rows: int = None
)
```

---

## Image Tools (`image`)

图像处理工具集，支持 OCR、批量分析和图像比较。

### ocr_image

对图像进行光学字符识别 (OCR)。

```python
ocr_image_tool(
    file_path: str,
    language: str = "eng+chi_sim",
    preserve_layout: bool = True
)
```

### batch_analyze_images

批量分析多张图像。

```python
batch_analyze_images_tool(image_paths: List[str])
```

### compare_images

比较两张图像的相似度。

```python
compare_images_tool(image_path_a: str, image_path_b: str)
```

---

## Video Tools (`video`)

视频处理工具集，支持帧提取、分析和缩略图生成。

### extract_video_frame

从视频中提取指定帧。

```python
extract_video_frame_tool(
    video_path: str,
    frame_number: int = 1,
    output_path: str = None
)
```

### analyze_video

分析视频内容。

```python
analyze_video_tool(
    video_path: str,
    analysis_type: str = "basic"
)
```

### get_video_info

获取视频元信息。

```python
get_video_info_tool(video_path: str)
```

---

## Voice Tools (`voice`)

音频处理工具集，支持格式转换、裁剪和音量调整。

### convert_audio

转换音频格式。

```python
convert_audio_tool(
    input_path: str,
    output_path: str,
    output_format: str = "mp3",
    bitrate: str = "192k"
)
```

### trim_audio

裁剪音频片段。

```python
trim_audio_tool(
    audio_path: str,
    output_path: str,
    start_seconds: float = 0,
    duration_seconds: float = None
)
```

### get_audio_info

获取音频文件元信息。

```python
get_audio_info_tool(audio_path: str)
```

---

## Memory Tools (`memory`)

记忆增强工具集，提供自动摘要、实体提取和模式检测。

### auto_summarize

自动摘要长文本。

```python
auto_summarize_tool(
    context: str,
    max_length: int = 500
)
```

### extract_entities

从文本中提取命名实体。

```python
extract_entities_tool(text: str)
```

**返回:**
```json
{
  "success": true,
  "data": {
    "entities": [
      {"type": "PERSON", "value": "John", "confidence": 0.95},
      {"type": "LOCATION", "value": "New York", "confidence": 0.88}
    ]
  }
}
```

### detect_patterns

检测文本中的模式。

```python
detect_patterns_tool(text: str)
```

### memory_search

搜索记忆内容。

```python
memory_search_tool(
    query: str,
    limit: int = 10
)
```

---

## Subagent Tools (`subagents`)

并行执行工具集，支持子代理委托和多任务并行处理。

### execute_parallel

并行执行多个任务。

```python
execute_parallel_tool(
    tasks: List[Dict],
    max_workers: int = 4,
    timeout_per_task: int = 60
)
```

**示例:**
```python
execute_parallel_tool(
    tasks=[
        {"id": "1", "action": "analyze", "data": "..."},
        {"id": "2", "action": "summarize", "data": "..."}
    ],
    max_workers=4
)
```

### aggregate_results

聚合多个任务的结果。

```python
aggregate_results_tool(
    results: List[Dict],
    strategy: str = "merge"
)
```

### delegate_task

委托任务给子代理。

```python
delegate_task_tool(
    task_description: str,
    agent_type: str = "general"
)
```

---

## Skills Hub (`skills`)

技能管理工具集，用于浏览、搜索和检查技能兼容性。

### list_skills

列出所有可用技能或按类别筛选。

```python
list_skills_tool(category: str = None)
```

**示例:**
```json
{
  "success": true,
  "data": {
    "categories": ["coding", "research", "creative", "automation", "communication"],
    "skills": [
      {"name": "code_analysis", "category": "coding"},
      {"name": "web_search", "category": "research"}
    ]
  }
}
```

### search_skills

根据功能关键词搜索技能。

```python
search_skills_tool(query: str)
```

### get_skill_details

获取技能详细信息。

```python
get_skill_details_tool(skill_name: str)
```

### check_skill_compatibility

检查技能与上下文的兼容性。

```python
check_skill_compatibility_tool(
    skill_name: str,
    context: str
)
```

**返回:**
```json
{
  "success": true,
  "data": {
    "compatibility_score": 0.85,
    "recommendation": "highly_recommended",
    "keywords_matched": 5
  }
}
```

---

## MCP Enhancement (`mcp`)

MCP 协议增强工具集，提供传输层抽象、连接管理和健康监控。

### mcp_transport

管理 MCP 传输层连接。

```python
mcp_transport_tool(
    action: str,
    config_json: str = "{}"
)
```

**支持的 action:**
- `list`: 列出支持的传输类型
- `create`: 创建传输配置
- `connect`: 建立连接
- `disconnect`: 断开连接
- `stats`: 获取传输统计

### mcp_connection

管理 MCP 服务器连接。

```python
mcp_connection_tool(
    action: str,
    name: str = "",
    config_json: str = "{}"
)
```

**支持的 action:**
- `list`: 列出所有连接
- `create`: 创建新连接
- `get`: 获取连接详情
- `remove`: 删除连接
- `stats`: 获取连接统计

### mcp_health

监控 MCP 服务器健康状态。

```python
mcp_health_tool(
    action: str,
    server_name: str = "",
    config_json: str = "{}"
)
```

**支持的 action:**
- `summary`: 获取所有服务器健康摘要
- `status`: 获取特定服务器状态
- `check`: 执行健康检查
- `history`: 获取健康历史
- `register`: 注册服务器进行监控
- `unregister`: 取消监控
- `record`: 记录请求指标

**健康等级:**
- `healthy`: 健康
- `degraded`: 性能下降
- `unhealthy`: 不健康
- `unknown`: 未知

---

## 使用示例

### 完整工作流示例

```python
# 1. 导入需要的工具模块
import tools.pdf_parser_tool
import tools.ocr_tool
import tools.auto_memory_tool
import tools.skills_hub_tool

# 2. 解析 PDF 文档
pdf_result = tools.pdf_parser_tool.parse_pdf_tool("/path/to/document.pdf")
pdf_data = json.loads(pdf_result)

# 3. OCR 图像
ocr_result = tools.ocr_tool.ocr_image_tool("/path/to/image.png")
ocr_data = json.loads(ocr_result)

# 4. 自动摘要
summary_result = tools.auto_memory_tool.auto_summarize_tool(
    context=pdf_data["data"]["text"]
)
summary_data = json.loads(summary_result)

# 5. 搜索相关技能
skills_result = tools.skills_hub_tool.search_skills_tool(query="document analysis")
skills_data = json.loads(skills_result)

# 6. 检查技能兼容性
compat_result = tools.skills_hub_tool.check_skill_compatibility_tool(
    skill_name="code_analysis",
    context="analyze this document structure"
)
```

---

## 错误处理

所有工具都遵循统一的返回格式：

```json
{
  "success": true/false,
  "error": "错误信息",
  "error_code": "ERROR_CODE"
}
```

**常见错误码:**
- `FILE_NOT_FOUND`: 文件不存在
- `INVALID_FORMAT`: 格式无效
- `PROCESSING_ERROR`: 处理错误
- `TIMEOUT`: 操作超时
- `PERMISSION_DENIED`: 权限被拒绝

---

## 工具注册机制

工具通过 `tools/registry.py` 的 `registry.register()` 自动注册：

```python
registry.register(
    name="tool_name",
    toolset="category",
    schema={...},
    handler=lambda args, **kw: tool_function(...),
    check_fn=lambda: True,
    requires_env=[],
)
```

工具集定义在 `toolsets.py`，支持组合和继承。

---

## 性能考虑

- 大文件处理建议使用流式 API
- 批量操作使用 `batch_analyze_*` 系列工具
- 并行任务使用 `execute_parallel` 提高效率
- 长时间运行的任务考虑后台执行
