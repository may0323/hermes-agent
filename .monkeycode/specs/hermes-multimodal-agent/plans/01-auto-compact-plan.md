# Plan: Auto Compact (自动上下文压缩)

**模块编号**: MOD-001
**优先级**: High
**状态**: ✅ 已有最佳实现
**借鉴来源**: OpenCode (已整合到 Hermes)

---

## 1. 功能描述

Auto Compact 是 OpenCode 引入的特性，在对话接近 context window 限制时自动压缩上下文。Hermes 已整合此功能并做了增强。

---

## 2. 现有 Hermes 能力分析

### 已有能力 (✅ 完善)
| 功能 | 文件 | 状态 |
|------|------|------|
| Context Compressor | `agent/context_compressor.py` | ✅ 已完善 |
| Token 估算 | `agent/model_metadata.py` | ✅ 已完善 |
| 摘要生成 | `call_llm()` | ✅ 已完善 |

### 特性对比

| 特性 | OpenCode | Hermes | 评估 |
|------|----------|--------|------|
| 95% 阈值触发 | ✅ | ✅ | Hermes 更完善 |
| LLM 摘要 | ✅ | ✅ | Hermes 更详细 |
| 渐进式摘要 | ❌ | ✅ | Hermes 独有 |
| 工具输出剪枝 | ❌ | ✅ | Hermes 独有 |

---

## 3. Hermes 实现分析

### 核心特性

1. **工具输出剪枝** (Pre-compression)
   - 替换旧工具输出为信息摘要
   - 避免完全丢弃有用信息

2. **渐进式摘要**
   - 保留之前摘要的信息
   - 增量更新而非重新生成

3. **Token 预算保护**
   - 尾部保护 ~20K tokens
   - 头部保护 system + 首个 exchange

4. **防抖动机制**
   - 连续压缩效果差时跳过
   - 避免无限循环

---

## 4. 配置选项

```yaml
# config.yaml
context:
  compressor:
    threshold_percent: 0.50  # 50% 触发压缩
    protect_first_n: 3     # 保护前 3 条消息
    summary_target_ratio: 0.20  # 20% token 用于摘要
```

---

## 5. 评估结论

**无需修改** - Hermes 的 Auto Compact 实现比 OpenCode 更完善。

---

## 6. 后续优化建议

1. **可视化** - 添加 `/compact --stats` 显示压缩统计
2. **手动触发** - `/compress <topic>` 专注压缩
3. **历史追溯** - 保留多次压缩历史
