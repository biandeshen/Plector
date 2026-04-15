# 任务：技能可发现性分析与设计规范生成

## 目标

1. 扫描 `skills/` 下所有 skill.json，分析每个技能的描述质量
2. 生成"技能可被发现性报告"
3. 基于报告生成 `SKILL_DESIGN_PRINCIPLES.md`

## 执行步骤

### Step 1: 读取所有 skill.json

读取 `skills/` 下每个技能的 `skill.json`，分析：
- description 是否清晰完整
- tools[].description 是否自描述
- 是否包含触发词/场景说明

### Step 2: 生成技能可发现性报告

格式：
```
## 技能可发现性报告

| 技能名 | 描述质量 | 问题 | 建议 |
|--------|---------|------|------|
| xxx    | 高/中/低 | ... | ... |
```

### Step 3: 生成 SKILL_DESIGN_PRINCIPLES.md

包含：
- 技能设计原则（4条）
- 模板：标准 skill.json 结构
- 现有技能的改进建议

## 交付物

1. `docs/reports/skill_discoverability_report.md` - 可发现性报告
2. `docs/SKILL_DESIGN_PRINCIPLES.md` - 设计规范文档
