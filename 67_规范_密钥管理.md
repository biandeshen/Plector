---
tags: [Plector, 密钥管理, 安全]
type: security
created: 2026-04-08
---

# 密钥管理规范

## 原则

1. **绝不硬编码** - 密钥永远不写入代码或配置文件
2. **环境变量** - 所有密钥通过环境变量传递
3. **配置引用** - config.yaml 中使用 ${VAR_NAME} 引用
4. **gitignore** - .env 文件必须被忽略

## 新增密钥流程

### 1. 在 .env 中添加密钥

```bash
# .env
NEW_SERVICE_API_KEY=your_real_key_here
```

### 2. 在 config.yaml 中引用

```yaml
# config.yaml
new_service:
  env:
    API_KEY: "${NEW_SERVICE_API_KEY}"
```

### 3. 在代码中使用

```python
# 方式一：通过 config_loader（推荐）
from core.config_loader import load_config
config = load_config()
api_key = config["new_service"]["env"]["API_KEY"]

# 方式二：直接读取环境变量
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ.get("NEW_SERVICE_API_KEY")
```

## 检查命令

```bash
# 手动检查密钥安全
python scripts/check_secrets.py

# pre-commit 自动检查
git commit -m "xxx"
```

## 常见错误

### ❌ 错误：硬编码密钥

```yaml
# config.yaml
minimax:
  env:
    MINIMAX_API_KEY: "sk-abc123xyz"
```

### ✅ 正确：环境变量引用

```yaml
# config.yaml
minimax:
  env:
    MINIMAX_API_KEY: "${MINIMAX_API_KEY}"
```

```bash
# .env
MINIMAX_API_KEY=sk-abc123xyz
```

## 文件清单

| 文件 | 作用 | 是否提交到 Git |
|------|------|---------------|
| .env | 存放真实密钥 | ❌ 不提交 |
| config/config.yaml | 存放 ${VAR} 引用 | ✅ 提交 |
| core/config_loader.py | 加载配置 + 替换变量 | ✅ 提交 |
| scripts/check_secrets.py | 检测硬编码密钥 | ✅ 提交 |
| docs/SECRETS.md | 密钥管理规范 | ✅ 提交 |
