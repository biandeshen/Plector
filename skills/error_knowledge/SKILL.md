---
name: error_knowledge
description: 记录和分类错误信息。当用户提到"记录错误"、"分析错误"、"错误分类"、"错误日志"时使用。
---

# Error Knowledge Skill

## 目的
存储错误记录并进行分类，帮助分析和追踪问题。

## 适用场景
- 记录新的错误
- 分析错误原因
- 分类错误类型
- 查询历史错误

## 执行步骤
1. 接收错误描述
2. 调用 store_error 存储错误
3. 调用 classify_error 分类错误
4. 返回错误 ID 和分类结果

## 成功标准
- 错误已存储到 data/errors/ 目录
- 返回错误 ID
- 返回错误分类（syntax_error / runtime_error / logic_error / network_error / unknown）

## 相关工具
- `store_error`：存储错误信息到本地知识库
- `classify_error`：分类错误类型，返回分类结果和置信度
