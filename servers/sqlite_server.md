---
name: sqlite
description: 查询和操作 SQLite 数据库。当用户要求"查询数据库"、"执行 SQL"、"查看表结构"、"列出表"时使用。
---

# SQLite MCP Server

## 目的
提供 SQLite 数据库的查询和操作能力。

## 适用场景
- 用户要求查询数据库中的数据
- 用户要求创建表、插入数据
- 用户要求查看表结构
- 用户要求列出所有表

## 执行步骤
1. 确认操作类型（查询/写入/查看）
2. 执行对应操作
3. 返回结果

## 成功标准
- SELECT 查询返回格式化表格
- 写入操作返回影响行数
- 表结构返回列信息

## 相关工具
- `query`：执行 SELECT 查询，返回格式化表格结果
- `execute`：执行 SQL 写入操作（INSERT / UPDATE / DELETE / CREATE TABLE）
- `list_tables`：列出数据库中的所有表和行数
- `describe_table`：查看指定表的结构（列名、类型、约束）

## 注意事项
- query 工具只支持 SELECT 语句
- execute 工具不支持 SELECT 语句
- 默认数据库路径：data/plector.db
