---
tags: [Plector, 命名规范, 开发标准]
type: standard
created: 2026-04-08
---

## Plector 文档命名规范

```markdown
---
title: Plector Document Naming Convention
category: explanation
last_updated: 2026-04-04
---

# Plector Document Naming Convention

*Version: 1.0.0*
*Updated: 2026-04-04*
*Related: BRD v1.1 / PRD v1.2 / DESIGN v1.2 / CODE_STANDARD.md*

---

## 一、命名原则

| 原则 | 说明 |
|------|------|
| **英文命名** | 文档名称使用英文，与代码和配置风格一致 |
| **规范化** | 统一格式，统一风格 |
| **可读性** | 文件名应能表达文档内容 |
| **唯一性** | 文档名称唯一，不重复 |

---

## 二、文件命名格式

### 2.1 主文档命名

```
[DocumentType]_[Project]_[Date]_[Version].md
```

示例：
```
System_Diagnosis_Plector_20260404_v1.md
Closed_Loop_Analysis_Plector_20260404.md
Architecture_Spec_Plector_20260404.md
```

### 2.2 提示词模板命名

在主文档文件名后加 `_prompt_template` 后缀：

```
[MainDocument]_prompt_template.md
```

示例：
| 主文档 | 提示词模板 |
|--------|-----------|
| `System_Diagnosis_Plector_20260404_v1.md` | `System_Diagnosis_Plector_20260404_v1_prompt_template.md` |
| `Closed_Loop_Analysis_Plector_20260404.md` | `Closed_Loop_Analysis_Plector_20260404_prompt_template.md` |

---

## 三、文档分类命名规范

### 3.1 产品文档

| 文档类型 | 命名格式 | 示例 |
|----------|----------|------|
| BRD | `BRD_Plector_[Version].md` | `BRD_Plector_v1.1.md` |
| PRD | `PRD_Plector_[Version].md` | `PRD_Plector_v1.2.md` |
| Design | `Design_Plector_[Version].md` | `Design_Plector_v1.2.md` |

### 3.2 规范文档

| 文档类型 | 命名格式 | 示例 |
|----------|----------|------|
| 代码规范 | `Code_Standard_Plector.md` | `Code_Standard_Plector.md` |
| 命名规范 | `Naming_Convention_Plector.md` | `Naming_Convention_Plector.md` |
| 架构规范 | `Architecture_Spec_Plector.md` | `Architecture_Spec_Plector.md` |

### 3.3 报告文档

| 文档类型 | 命名格式 | 示例 |
|----------|----------|------|
| 系统诊断 | `System_Diagnosis_Plector_[Date].md` | `System_Diagnosis_Plector_20260404.md` |
| 闭环分析 | `Closure_Analysis_Plector_[Date].md` | `Closure_Analysis_Plector_20260404.md` |
| 技能健康 | `Skill_Health_Report_Plector_[Date].md` | `Skill_Health_Report_Plector_20260404.md` |
| 测试报告 | `Test_Report_Plector_[Date].md` | `Test_Report_Plector_20260404.md` |
| 周报 | `Weekly_Report_Plector_[Year]W[Week].md` | `Weekly_Report_Plector_2026W14.md` |

### 3.4 技能文档

| 文档类型 | 命名格式 | 示例 |
|----------|----------|------|
| 技能目录 | `Skill_Catalog_Plector_[Date].md` | `Skill_Catalog_Plector_20260404.md` |
| 闭环配置 | `Closure_Config_Plector_[Date].md` | `Closure_Config_Plector_20260404.md` |
| 技能说明 | `Skill_[Name]_Guide.md` | `Skill_Health_Monitor_Guide.md` |

### 3.5 开发文档

| 文档类型 | 命名格式 | 示例 |
|----------|----------|------|
| TDD 计划 | `TDD_Plan_Plector_[Version].md` | `TDD_Plan_Plector_v1.md` |
| 迁移指南 | `Migration_Guide_Plector_[Version].md` | `Migration_Guide_Plector_v1.md` |
| API 参考 | `API_Reference_Plector_[Version].md` | `API_Reference_Plector_v1.md` |
| README | `README.md` | `README.md` |

---

## 四、日期格式规范

| 格式 | 示例 | 使用场景 |
|------|------|----------|
| `YYYYMMDD` | `20260404` | 文件名中使用 |
| `YYYY-MM-DD` | `2026-04-04` | 文档标题中使用 |

---

## 五、版本号规范

| 格式 | 说明 |
|------|------|
| `v1` / `v1.0` | 初版 |
| `v1.1` / `v1.2` | 修订版 |
| `_final` | 最终版 |
| `_draft` | 草稿 |

---

## 六、目录结构规范

```
docs/
├── specs/                          # 产品规格文档
│   ├── BRD_Plector_v1.1.md
│   ├── PRD_Plector_v1.2.md
│   └── Design_Plector_v1.2.md
├── standards/                      # 规范文档
│   ├── Code_Standard_Plector.md
│   ├── Naming_Convention_Plector.md
│   └── Architecture_Spec_Plector.md
├── reports/                        # 报告文档
│   ├── System_Diagnosis_Plector_20260404.md
│   ├── System_Diagnosis_Plector_20260404_prompt_template.md
│   └── Closure_Analysis_Plector_20260404.md
├── skills/                         # 技能文档
│   ├── Skill_Catalog_Plector_20260404.md
│   └── Skill_Health_Monitor_Guide.md
├── dev/                            # 开发文档
│   ├── TDD_Plan_Plector_v1.md
│   └── Migration_Guide_Plector_v1.md
└── README.md
```

---

## 七、强制规则

| 规则 | 说明 |
|------|------|
| **英文命名** | 文件名必须使用英文，单词间用下划线连接 |
| **配对生成** | 报告类文档必须同时生成对应的 `_prompt_template.md` |
| **日期标注** | 报告类文件名必须包含日期 |
| **版本控制** | 规格文档更新时，版本号递增 |
| **无空格** | 文件名中不使用空格，用下划线替代 |

---

## 八、当前文档清单

| 文档 | 路径 | 状态 |
|------|------|------|
| BRD v1.1 | `docs/specs/BRD_Plector_v1.1.md` | ✅ 定稿 |
| PRD v1.2 | `docs/specs/PRD_Plector_v1.2.md` | ✅ 定稿 |
| Design v1.2 | `docs/specs/Design_Plector_v1.2.md` | ✅ 定稿 |
| Code Standard | `docs/standards/Code_Standard_Plector.md` | ✅ 定稿 |
| Naming Convention | `docs/standards/Naming_Convention_Plector.md` | 本文档 |
| TDD Plan | `docs/dev/TDD_Plan_Plector_v1.md` | ✅ 定稿 |

---

*本规范会持续更新。*
```

---
