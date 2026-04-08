---
title: 数据查询 - Plector 开发流程
tags: [Plector, Dataview, 工具]
type: dataview
created: 2026-04-08
---

# 📊 Plector 开发流程 - 数据查询

> 本页展示 Dataview 查询示例，利用 frontmatter 数据对笔记库进行统计和筛选。

---

## 📈 总览统计

### 文档类型分布

```dataview
TABLE length(rows) as 数量
GROUP BY type
SORT length(rows) DESC
```

### 标签云统计

```dataview
TABLE length(rows) as 数量
GROUP BY tags
FLATTEN tags
WHERE tags != ""
SORT length(rows) DESC
LIMIT 20
```

---

## 🗓️ 按版本分类

### v1.0 系列

```dataview
TABLE file.ctime as 创建时间, type as 类型
FROM "00_v1.0"
SORT file.name ASC
```

### v1.1 系列

```dataview
TABLE file.ctime as 创建时间, type as 类型
FROM "16_v1.1" or "17_v1.1" or "18_v1.1" or "19_v1.1" or "20_v1.1" or "21_v1.1"
SORT file.name ASC
```

### v1.2 系列

```dataview
TABLE file.ctime as 创建时间, type as 类型
FROM "22_v1.2" or "23_v1.2" or "24_v1.2" or "25_v1.2" or "26_v1.2" or "27_v1.2" or "28_v1.2" or "29_v1.2" or "30_v1.2"
SORT file.name ASC
```

### v1.3 系列

```dataview
TABLE file.ctime as 创建时间, type as 类型
FROM "31_v1.3" or "32_v1.3"
SORT file.name ASC
```

### v2.x 系列

```dataview
TABLE file.ctime as 创建时间, type as 类型
FROM "41_v2.x"
SORT file.name ASC
```

---

## 🏷️ 按类型筛选

### 里程碑 / 版本发布

```dataview
TABLE version, file.ctime as 创建时间
FROM ""
WHERE type = "milestone"
SORT file.name ASC
```

### Bug 修复记录

```dataview
TABLE file.ctime as 创建时间, tags
FROM ""
WHERE type = "bugfix"
SORT file.name ASC
```

### 规范文档

```dataview
TABLE file.ctime as 创建时间
FROM ""
WHERE type = "spec" or type = "standard"
SORT file.name ASC
```

### 产品文档 (BRD/PRD/Design)

```dataview
TABLE file.ctime as 创建时间
FROM ""
WHERE type = "brd" or type = "prd" or type = "design"
SORT file.name ASC
```

---

## 🔍 快速查找

### 最近更新的文档

```dataview
TABLE file.mtime as 修改时间, type as 类型
FROM ""
SORT file.mtime DESC
LIMIT 10
```

### 核心模块实现文档

```dataview
TABLE file.ctime as 创建时间
FROM ""
WHERE contains(tags, "核心模块")
SORT file.name ASC
```

### 技能 / MCP 相关

```dataview
TABLE file.ctime as 创建时间
FROM ""
WHERE contains(tags, "技能") or contains(tags, "MCP")
SORT file.name ASC
```

---

## 📋 附录：frontmatter 参考

所有文档统一使用以下 frontmatter 格式：

```yaml
---
title: 文档标题
tags: [标签1, 标签2, ...]
type: 类型        # note | milestone | bugfix | spec | feature | brd | prd | design | standard | doc
created: 日期
version: 版本号   # 可选
---
```

### type 字段说明

| type | 含义 |
|------|------|
| `note` | 一般笔记 |
| `milestone` | 里程碑 / 版本发布 |
| `bugfix` | Bug 修复记录 |
| `spec` | 技术规范 |
| `feature` | 功能实现 |
| `brd` | 商业需求文档 |
| `prd` | 产品需求文档 |
| `design` | 技术设计文档 |
| `standard` | 开发标准规范 |
| `doc` | 使用文档 |
