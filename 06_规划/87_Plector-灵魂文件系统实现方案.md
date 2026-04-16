# Plector "灵魂文件"系统实现方案

### 目标

让 Plector 拥有 OpenClaw 式的"人格 + 用户画像 + 安全规则 + 动态记忆"文件化系统。

### 文件结构

```
Plector/
├── soul.md                    # 新增：AI 人格定义
├── user.md                    # 新增：用户画像
├── agents.md                  # 新增：安全规则与工具权限
├── memory.md                  # 新增：长期知识记忆
├── memory/                    # 新增：记忆目录
│   ├── 2026-04-16.md          # 每日日志（短期记忆）
│   ├── 2026-04-17.md
│   └── sessions/              # 新增：会话存档
│       └── session_xxx.md
├── core/
│   ├── soul_loader.py         # 新增：灵魂文件加载器
│   ├── memory_writer.py       # 新增：记忆自动写入
│   └── agent_loop.py          # 修改：注入灵魂 + 自动写入
└── skills/
    └── memory/
        └── implementation.py  # 修改：记忆写入逻辑
```

---

### 一、创建 4 个灵魂文件

#### 1.1 `soul.md`

```markdown
# Plector 人格定义

## 核心性格
- 理性、务实、高效
- 技术导向，优先给出可执行方案
- 不废话，不寒暄，直奔主题

## 沟通风格
- 中文为主，技术术语保留英文
- 用代码说话，少用形容词
- 出错时直接承认，不找借口

## 能力边界
- 知道自己不知道什么
- 不确定时明确说"我不确定"
- 不编造信息

## 可自定义区域
<!-- 以下内容可由用户修改，AI 会加载但不会主动修改 -->
```

#### 1.2 `user.md`

```markdown
# 用户画像

## 基本信息
- 名称：（待填写）
- 职业：（待填写）
- 技术栈：Python, TypeScript, Docker

## 偏好
- 代码风格：简洁优先
- 沟通方式：直接
- 反馈方式：给出方案，不要过多解释

## 可自定义区域
<!-- 以下内容可由用户修改 -->
```

#### 1.3 `agents.md`

```markdown
# 安全规则与工具权限

## 安全边界
- 不删除系统文件
- 不修改 .env 中的 API Key
- 执行危险命令前必须确认

## 工具权限
- allow: read_file, write_file, run_command, web_search
- deny: rm -rf /, format, shutdown

## 记忆权限
- MEMORY.md: AI 可自主写入
- soul.md: 仅用户可修改
- user.md: 仅用户可修改（除非用户授权）
- agents.md: 仅用户可修改

## 可自定义区域
<!-- 以下内容可由用户修改 -->
```

#### 1.4 `memory.md`

```markdown
# 长期知识记忆

<!-- AI 会自动写入，用户也可以手动编辑 -->

## 项目知识
- Plector 是一个 AI Agent 框架
- 基于 Python 3.12，使用 ChromaDB 做向量存储

## 技术决策
- 2026-04-15: 选择 ChromaDB 而非 Pinecone（本地优先）

## 用户习惯
- 喜欢简洁的代码
- 不喜欢过多注释

## 待办事项
- [ ] 完善记忆系统
- [ ] 添加流式响应
```

---

### 二、创建灵魂文件加载器

创建 `core/soul_loader.py`：

```python
#!/usr/bin/env python3
"""
灵魂文件加载器 - 加载 SOUL.md, USER.md, AGENTS.md, MEMORY.md

功能：
    1. 加载灵魂文件内容
    2. 注入到 system prompt
    3. 检测文件变化并热加载
    4. 每日日志加载

Author: Plector
Version: 1.0.0
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 灵魂文件路径
SOUL_FILE = PROJECT_ROOT / "soul.md"
USER_FILE = PROJECT_ROOT / "user.md"
AGENTS_FILE = PROJECT_ROOT / "agents.md"
MEMORY_FILE = PROJECT_ROOT / "memory.md"
MEMORY_DIR = PROJECT_ROOT / "memory"


def load_file(filepath: Path, default: str = "") -> str:
    """加载文件内容，不存在则返回默认值"""
    try:
        if filepath.exists():
            return filepath.read_text(encoding="utf-8").strip()
        return default
    except Exception as e:
        logger.error(f"加载文件失败 {filepath}: {e}")
        return default


def load_soul() -> str:
    """加载 AI 人格"""
    return load_file(SOUL_FILE, "你是 Plector，一个务实的 AI 助手。")


def load_user() -> str:
    """加载用户画像"""
    return load_file(USER_FILE, "用户信息待补充。")


def load_agents() -> str:
    """加载安全规则"""
    return load_file(AGENTS_FILE, "遵守基本安全规则。")


def load_memory() -> str:
    """加载长期记忆"""
    return load_file(MEMORY_FILE, "")


def load_daily_log(days_back: int = 1) -> str:
    """
    加载每日日志

    参数:
        days_back: 加载最近几天的日志（0=今天，1=今天+昨天）
    """
    if not MEMORY_DIR.exists():
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    logs = []
    for i in range(days_back + 1):
        date = datetime.now() - timedelta(days=i)
        log_file = MEMORY_DIR / f"{date.strftime('%Y-%m-%d')}.md"
        content = load_file(log_file)
        if content:
            logs.append(f"## {date.strftime('%Y-%m-%d')} 日志\n{content}")

    return "\n\n".join(logs)


def load_session(session_id: str) -> str:
    """加载会话存档"""
    session_dir = MEMORY_DIR / "sessions"
    session_file = session_dir / f"{session_id}.md"
    return load_file(session_file)


def build_system_prompt() -> str:
    """
    构建完整的 system prompt

    注入顺序：
        1. AI 人格（soul.md）
        2. 用户画像（user.md）
        3. 安全规则（agents.md）
        4. 长期记忆（memory.md）
        5. 近期日志（memory/YYYY-MM-DD.md）
    """
    soul = load_soul()
    user = load_user()
    agents = load_agents()
    memory = load_memory()
    daily_log = load_daily_log(days_back=1)

    sections = []

    if soul:
        sections.append(f"# AI 人格\n{soul}")

    if user:
        sections.append(f"# 用户画像\n{user}")

    if agents:
        sections.append(f"# 安全规则\n{agents}")

    if memory:
        sections.append(f"# 长期记忆\n{memory}")

    if daily_log:
        sections.append(f"# 近期日志\n{daily_log}")

    return "\n\n---\n\n".join(sections)


def get_memory_permissions() -> dict:
    """
    从 agents.md 解析记忆权限

    返回:
        {"memory.md": True, "soul.md": False, "user.md": False, "agents.md": False}
    """
    agents_content = load_agents()
    permissions = {
        "memory.md": True,  # 默认允许
        "soul.md": False,
        "user.md": False,
        "agents.md": False,
    }

    # 解析 agents.md 中的权限设置
    for line in agents_content.split("\n"):
        line = line.strip()
        if line.startswith("- ") and ":" in line:
            parts = line[2:].split(":", 1)
            if len(parts = parts[0].strip()
                permission = parts[1].strip().lower()
                if file_name in permissions:
                    permissions[file_name] = ("可" in permission or "allow" in permission.lower())

    return permissions


def check_file_changed(filepath: Path, last_modified: dict) -> bool:
    """检测文件是否变化"""
    if not filepath.exists():
        return False
    current_mtime = filepath.stat().st_mtime
    key = str(filepath)
    if key not in last_modified or last_modified[key] != current_mtime:
        last_modified[key] = current_mtime
        return True
    return False
```

### 验证

```bash
python -m py_compile core/soul_loader.py
```

### 测试

```bash
python -c "
from core.soul_loader import build_system_prompt, load_daily_log
print(build_system_prompt())
print('---')
print(load_daily_log(days_back=1))
"
```

---

### 三、创建记忆自动写入器

创建 `core/memory_writer.py`：

```python
#!/usr/bin/env python3
"""
记忆自动写入器 - AI 自主判断哪些信息值得记录

功能：
    1. 从对话中提取值得记录的信息
    2. 写入 memory.md（长期记忆）
    3. 写入 memory/YYYY-MM-DD.md（每日日志）
    4. 写入 memory/sessions/（会话存档）

Author: Plector
Version: 1.0.0
"""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
MEMORY_FILE = PROJECT_ROOT / "memory.md"
MEMORY_DIR) == 2:
                file_name = PROJECT_ROOT / "memory"


def ensure_memory_dir():
    """确保记忆目录存在"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    (MEMORY_DIR / "sessions").mkdir(parents=True, exist_ok=True)


def append_to_daily_log(content: str, source: str = "auto") -> str:
    """
    追加到每日日志

    参数:
        content: 日志内容
        source: 来源（auto=AI自动/user=用户手动）

    返回:
        日志文件路径
    """
    ensure_memory_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = MEMORY_DIR / f"{today}.md"

    timestamp = datetime.now().strftime("%H:%M")
    entry = f"\n### [{timestamp}] ({source})\n{content}\n"

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
        logger.info(f"写入日志: {log_file}")
        return str(log_file)
    except Exception as e:
        logger.error(f"写入日志失败: {e}")
        return ""


def append_to_memory(content: str, category: str = "general") -> str:
    """
    追加到长期记忆 memory.md

    参数:
        content: 记忆内容
        category: < 2:
 分类（project/technical/decision/user_habit/todo）

    返回:
        记忆文件路径
    """
    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text("# 长期知识记忆\n\n", encoding="utf-8")

    try:
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            f.write(f"\n- [{timestamp}] {content}\n")
        logger.info(f"写入长期记忆: {content[:50]}...")
        return str(MEMORY_FILE)
    except Exception as e:
        logger.error(f"写入长期记忆失败: {e}")
 messages: list) -> str:
    """
    保存会话存档

    参数:
        session_id: 会话 ID
        messages: 消息列表 [{"role": "user/assistant", "content": "..."}]

    返回:
        存档文件路径
    """
    ensure_memory_dir()
    session_file        return {"written": False, "content": "", "category": ""}

    # 取最近 4 轮对话
    recent = conversation_history[-8:]
    conversation_text = "\n".join([
        f"{msg['role']}: {msg.get('content', '')[:200]}"
        for msg in recent
    ])

    prompt = f"""分析以下对话，判断是否有值得长期记忆的信息。

对话内容：
{conversation_text}

请以 JSON 格式返回：
{{
  "should_write": true/false,
  "content": "值得记录的内容（一句话）",
  "category": "project/technical/decision/user_habit/todo",
  "reason": "为什么值得记录"
}}

判断标准：
- 用户明确说"记住"、"以后"、"我喜欢" → should_write=true
- 重要的技术决策 → should_write=true
- 用户的习惯偏好 → should_write=true
- 普通问答、闲聊 → should_write=false

只返回 JSON，不要其他内容。"""

    try:
        result = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )

        import json
        text = result.get("content", "") if isinstance(result, dict) else str(result)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]

        parsed = json.loads(text)

        if parsed.get("should_write"):
            content = parsed.get("content", "")
            category = parsed.get("category", "general")

            # 写入长期记忆
            append_to_memory(content, category)

            # 写入每日日志
            append_to_daily_log(f"自动记忆: {content}", source="auto")

            return {"written": True, "content": content, "category": category}

        return {"written": False, "content": "", "category": ""}

    except Exception as e:
        logger.error(f"自动记忆判断失败: {e}")
        return {"written": False, "content": "", "category": ""}
        return ""


def save_session(session_id: str, = MEMORY_DIR / "sessions" / f"{session_id}.md"

    try:
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(f"# 会话存档: {session_id}\n\n")
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                f.write(f"## {role}\n{content}\n\n")
        logger.info(f"保存会话存档: {session_file}")
        return str(session_file)
    except Exception as e:
        logger.error(f"保存会话存档失败: {e}")
        return ""


async def auto_write_memory(
    conversation_history: list,
    llm_client,
) -> dict:
    """
    AI 自主判断哪些信息值得记录

    参数:
        conversation_history: 对话历史
        llm_client: LLM 客户端

    返回:
        {"written": bool, "content": str, "category": str}
    """
    if len(conversation_history)```

### _writer import auto_write_memory, append_to_daily_log, save_session
```

#### 4.2 修改 `__init__` 方法

在 `__init__` 方法中添加：

```python
        # 灵魂文件热加载
        self._soul_files_mtime = {}
        self._cached_system_prompt = None
```

#### 4.3 添加灵魂文件加载方法

在 `__init__` 方法后添加：

```python
    def _get_system_prompt(self) -> str:
        """
        获取 system prompt（带热加载）

        检测灵魂文件变化，变化时重新加载
        """
        files = [SOUL_FILE, USER_FILE, AGENTS_FILE, MEMORY_FILE]
        changed = any(check_file_changed(f, self._soul_files_mtime) for f in files)

        if changed or self._cached_system_prompt is None:
            self._cached_system_prompt = build_system_prompt()
            logger.info("灵魂文件已重新加载")

        return self._cached_system_prompt
```

#### 4.4 修改 `run` 方法

找到 `run` 方法，修改 system prompt 注入部分：

```python
    async def run(self, user_input: str, session_id: str = None) -> str:
        """执行 Agent 循环"""

        # 注入灵魂文件
        system_prompt = self._get_system_prompt()
        self.messages.append({"role": "system", "content": system_prompt})

        # ... 原有逻辑 ...

        # 在循环结束后，自动判断是否写入记忆
        if self.llm_client:
            await auto_write_memory(self.messages, self.llm_client)

        # 写入每日日志
        append_to_daily_log(
            f"用户: {user_input[:100]}\nAI: {response[:100]}",
            source="auto"
        )

        return response
```

#### 4.5 修改 `_build_system_prompt` 方法

如果你有 `_build_system_prompt` 方法，替换为：

```python
    def _build_system_prompt(self) -> str:
        """构建 system prompt（使用灵魂文件）"""
        return self._get_system_prompt()
```

### 验证

```bash
python -m py_compile core/agent_loop.py
```

---

### 五、修改记忆技能

在 `skills/memory/implementation.py` 中添加工具：

```python
    async def update_memory(self, content: str, category: str = "general",
                            **kwargs) -> dict:
        """
        手动写入长期记忆

        参数:
            content: 记忆内容
            category: 分类（project/technical/decision/user_habit/todo）
        """
        _ = kwargs
        try:
            from core.memory_writer import append_to_memory, append_to_daily_log

            append_to_memory(content, category)
            append_to_daily_log(f"手动记忆: {content}", source="user")

            return {"success": True, "data": {"content": content}, "error": None}
        except Exception as e:
            logger.error(f"写入记忆失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def edit_soul(self, content: str, **kwargs) -> dict:
        """
        修改 AI 人格（soul.md）

        参数:
            content: 新的人格定义
        """
        _ = kwargs
        try:
            from core.soul_loader import SOUL_FILE
            from core.soul_loader import get_memory_permissions

            permissions = get_memory_permissions()
            if not permissions.get("soul.md", False):
                return {
                    "success": False,
                    "data": None,
                    "error": "soul.md 权限未开放，请在 agents.md 中授权"
                }

            SOUL_FILE.write_text(content, encoding="utf-8")
            return {"success": True, "data": {"file": "soul.md"}, "error": None}
        except Exception as e:
            logger.error(f"修改人格失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def edit_user(self, content: str, **kwargs) -> dict:
        """
        修改用户画像（user.md）

        参数:
            content: 新的用户画像
        """
        _ = kwargs
        try:
            from core.soul_loader import USER_FILE
            from core.soul_loader import get_memory_permissions

            permissions = get_memory_permissions()
            if not permissions.get("user.md", False):
                return {
                    "success": False,
                    "data": None,
                    "error": "user.md 权限未开放，请在 agents.md 中授权"
                }

            USER_FILE.write_text(content, encoding="utf-8")
            return {"success": True, "data": {"file": "user.md"}, "error": None}
        except Exception as e:
            logger.error(f"修改用户画像失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}
```

---

### 六、更新 skill.json

在 `skills/memory/skill.json` 的 tools 数组中添加：

```json
    {
      "name": "update_memory",
      "description": "手动写入长期记忆（memory.md）。",
      "parameters": {
        "content": "string (记忆内容)",
        "category": "string (可选，project/technical/decision/user_habit/todo)"
      }
    },
    {
      "name": "edit_soul",
      "description": "修改 AI 人格（需要 agents.md 授权）。",
      "parameters": {
        "content": "string (新的人格定义)"
      }
    },
    {
      "name": "edit_user",
      "description": "修改用户画像（需要 agents.md 授权）。",
      "parameters": {
        "content": "string (新的用户画像)"
      }
    }
```

---

### 七、更新 SKILL.md

在 `skills/memory/SKILL.md` 中添加：

```markdown
### update_memory
手动写入长期记忆（memory.md）。

参数：
- content: 记忆内容（必需）
- category: 分类（可选，默认 general）

### edit_soul
修改 AI 人格。需要在 agents.md 中授权 soul.md 可修改。

### edit_user
修改用户画像。需要在 agents.md 中授权 user.md 可修改。

## 灵魂文件系统

| 文件 | 谁能改 | 说明 |
|------|--------|------|
| soul.md | 用户（需授权 AI） | AI 人格定义 |
| user.md | 用户（需授权 AI） | 用户画像 |
| agents.md | 仅用户 | 安全规则 |
| memory.md | AI + 用户 | 长期记忆 |
| memory/YYYY-MM-DD.md | AI 自动 | 每日日志 |
```

---

### 八、验证和提交

```bash
# 验证语法
python -m py_compile core/soul_loader.py
python -m py_compile core/memory_writer.py
python -m py_compile core/agent_loop.py
python -m py_compile skills/memory/implementation.py

# 运行测试
python -m pytest tests/ -v

# 提交
git add soul.md user.md agents.md memory.md memory/ core/soul_loader.py core/memory_writer.py core/agent_loop.py skills/memory/
git commit -m "feat(soul): 灵魂文件系统 + 记忆自动写入 + 每日日志"
git push
```

---

### 改动汇总

| 文件 | 改动 | 行数 |
|------|------|------|
| `soul.md` | 新增 AI 人格 | 20 |
| `user.md` | 新增用户画像 | 20 |
| `agents.md` | 新增安全规则 | 25 |
| `memory.md` | 新增长期记忆 | 20 |
| `memory/` | 新增记忆目录 | 自动创建 |
| `core/soul_loader.py` | 新增灵魂加载器 | 150 |
| `core/memory_writer.py` | 新增记忆写入器 | 150 |
| `core/agent_loop.py` | 注入灵魂 + 热加载 + 自动记忆 | +40 |
| `skills/memory/implementation.py` | 新增 3 个工具 | +60 |
| `skills/memory/skill.json` | 新增工具定义 | +30 |
| `skills/memory/SKILL.md` | 新增文档 | +20 |

---

### 执行顺序

```
1. 创建 4 个灵魂文件（soul.md, user.md, agents.md, memory.md）
2. 创建 memory/ 目录
3. 创建 core/soul_loader.py
4. 创建 core/memory_writer.py
5. 修改 core/agent_loop.py（注入灵魂 + 热加载）
6. 修改 skills/memory/implementation.py（新增工具）
7. 修改 skills/memory/skill.json（新增工具定义）
8. 修改 skills/memory/SKILL.md（新增文档）
9. 验证 + 测试 + 提交
```

**从第一步开始执行。**