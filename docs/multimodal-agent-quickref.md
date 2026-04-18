# Hermes Multimodal Agent 快速参考

## 工具速查表

### Document Tools (6)
| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `parse_pdf` | PDF 文本提取 | `file_path`, `max_pages` |
| `get_pdf_info` | PDF 元信息 | `file_path` |
| `parse_docx` | Word 文档解析 | `file_path`, `extract_images` |
| `get_docx_info` | Word 元信息 | `file_path` |
| `parse_spreadsheet` | Excel/CSV 解析 | `file_path`, `sheet_index` |
| `get_spreadsheet_info` | 电子表格元信息 | `file_path` |

### Image Tools (7)
| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `ocr_image` | 图像 OCR | `file_path`, `language` |
| `ocr_pdf` | PDF OCR | `file_path`, `language` |
| `get_ocr_languages` | 支持的语言 | - |
| `batch_analyze_images` | 批量图像分析 | `image_paths` |
| `batch_analyze_directory` | 目录图像分析 | `directory_path` |
| `compare_images` | 图像比较 | `image_path_a`, `image_path_b` |
| `find_similar_images` | 相似图像查找 | `image_path`, `directory` |

### Video Tools (6)
| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `extract_video_frame` | 提取单帧 | `video_path`, `frame_number` |
| `extract_multiple_video_frames` | 提取多帧 | `video_path`, `frame_numbers` |
| `get_video_info` | 视频元信息 | `video_path` |
| `analyze_video` | 视频分析 | `video_path`, `analysis_type` |
| `generate_video_thumbnail` | 生成缩略图 | `video_path`, `timestamp` |
| `extract_video_audio` | 提取音频 | `video_path`, `output_path` |

### Voice Tools (4)
| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `get_audio_info` | 音频元信息 | `audio_path` |
| `convert_audio` | 格式转换 | `input_path`, `output_path` |
| `trim_audio` | 音频裁剪 | `audio_path`, `start_seconds` |
| `adjust_audio_volume` | 音量调整 | `audio_path`, `volume_factor` |

### Memory Tools (4)
| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `auto_summarize` | 文本摘要 | `context`, `max_length` |
| `extract_entities` | 实体提取 | `text` |
| `detect_patterns` | 模式检测 | `text` |
| `memory_search` | 记忆搜索 | `query`, `limit` |

### Subagent Tools (3)
| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `execute_parallel` | 并行执行 | `tasks`, `max_workers` |
| `aggregate_results` | 结果聚合 | `results`, `strategy` |
| `delegate_task` | 任务委托 | `task_description`, `agent_type` |

### Skills Hub (4)
| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `list_skills` | 列出技能 | `category` |
| `search_skills` | 搜索技能 | `query` |
| `get_skill_details` | 技能详情 | `skill_name` |
| `check_skill_compatibility` | 兼容性检查 | `skill_name`, `context` |

### MCP Tools (3)
| 工具 | 用途 | 关键参数 |
|------|------|----------|
| `mcp_transport` | 传输管理 | `action`, `config_json` |
| `mcp_connection` | 连接管理 | `action`, `name` |
| `mcp_health` | 健康监控 | `action`, `server_name` |

---

## 常用工作流

### 文档分析流程
```
parse_pdf → auto_summarize → extract_entities → memory_search
```

### 图像批量处理
```
batch_analyze_directory → compare_images → find_similar_images
```

### 视频处理流程
```
get_video_info → extract_multiple_video_frames → analyze_video → generate_video_thumbnail
```

### 并行任务处理
```
execute_parallel(tasks=[...]) → aggregate_results(results=[...])
```

---

## 返回格式

### 成功响应
```json
{
  "success": true,
  "data": {
    // 具体数据
  }
}
```

### 错误响应
```json
{
  "success": false,
  "error": "错误描述",
  "error_code": "ERROR_CODE"
}
```

---

## 工具集映射

| Toolset | 工具 |
|----------|------|
| document | parse_pdf, get_pdf_info, parse_docx, get_docx_info, parse_spreadsheet, get_spreadsheet_info |
| image | ocr_image, ocr_pdf, get_ocr_languages, batch_analyze_images, batch_analyze_directory, compare_images, find_similar_images |
| video | extract_video_frame, extract_multiple_video_frames, get_video_info, analyze_video, generate_video_thumbnail, extract_video_audio |
| voice | get_audio_info, convert_audio, trim_audio, adjust_audio_volume |
| memory | auto_summarize, extract_entities, detect_patterns, memory_search |
| subagents | execute_parallel, aggregate_results, delegate_task |
| skills | list_skills, search_skills, get_skill_details, check_skill_compatibility |
| mcp | mcp_transport, mcp_connection, mcp_health |

---

## 性能提示

1. **批量操作**: 使用 `batch_analyze_*` 而非循环调用单个工具
2. **并行处理**: 多任务用 `execute_parallel` 而非串行
3. **大文件**: 优先使用流式 API 或分片处理
4. **缓存**: 重复使用的数据考虑缓存结果
5. **超时设置**: 复杂任务适当增加 timeout

---

## API Relay (中转站) 配置

通过设置中转站，所有 AI Provider 请求都经过中转服务器。

### 快速配置

```bash
# 环境变量方式
export CUSTOM_RELAY_BASE_URL="https://your-relay.com/v1"
export CUSTOM_RELAY_API_KEY="your-key"
```

```yaml
# config.yaml 方式
relay:
  enabled: true
  base_url: "https://your-relay.com/v1"
  api_key: "your-key"
  providers: []  # 空 = 所有 Provider
```

### 主要优势

- 网络受限环境下也能访问 AI 服务
- 统一管理 API 密钥和流量
- 可配合日志、缓存、限流等使用

---

## 代码示例

```python
# 完整文档处理流程
import json
import tools.pdf_parser_tool as pdf
import tools.auto_memory_tool as memory
import tools.skills_hub_tool as skills

# 1. 解析 PDF
result = pdf.parse_pdf_tool("/path/to/doc.pdf", max_pages=50)
data = json.loads(result)

# 2. 摘要
summary = memory.auto_summarize_tool(data["data"]["text"])
summary_data = json.loads(summary)

# 3. 提取实体
entities = memory.extract_entities_tool(data["data"]["text"])
entities_data = json.loads(entities)

# 4. 搜索相关技能
skill_match = skills.search_skills_tool("document analysis")
skill_data = json.loads(skill_match)
```
