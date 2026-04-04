#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成 README.md

扫描项目状态，生成最新的 README.md

用法：
    python scripts/generate_readme.py
"""

import ast
import json
import subprocess
from pathlib import Path


def get_version():
    """从 git tag 获取版本"""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        return result.stdout.strip() or "v1.1.0"
    except Exception:
        return "v1.1.0"


def scan_skills(root):
    """扫描技能"""
    skills = []
    skills_dir = root / "skills"
    if not skills_dir.exists():
        return skills

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_json = skill_dir / "skill.json"
        if not skill_json.exists():
            continue

        with open(skill_json, encoding="utf-8") as f:
            meta = json.load(f)

        tools = meta.get("tools", [])
        skills.append({
            "name": meta.get("name", skill_dir.name),
            "description": meta.get("description", ""),
            "version": meta.get("version", "1.0.0"),
            "tools": tools,
            "tools_count": len(tools),
        })

    return skills


def scan_mcp_servers(root):
    """扫描 MCP Server"""
    servers = []
    servers_dir = root / "servers"
    if not servers_dir.exists():
        return servers

    for py_file in sorted(servers_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        try:
            with open(py_file, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            tools_count = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "TOOLS":
                            if isinstance(node.value, ast.List):
                                tools_count = len(node.value.elts)
            servers.append({
                "name": py_file.stem.replace("_server", ""),
                "file": py_file.name,
                "tools_count": tools_count,
            })
        except Exception:
            pass

    return servers


def scan_channels(root):
    """扫描渠道"""
    channels = []
    channels_dir = root / "channels"
    if not channels_dir.exists():
        return channels

    for py_file in sorted(channels_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        channels.append({
            "name": py_file.stem,
            "file": py_file.name,
        })

    for html_file in sorted(channels_dir.glob("*.html")):
        channels.append({
            "name": html_file.stem,
            "file": html_file.name,
        })

    return channels


def scan_core_modules(root):
    """扫描核心模块"""
    modules = []
    core_dir = root / "core"
    if not core_dir.exists():
        return modules

    for py_file in sorted(core_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        desc = ""
        with open(py_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# -*-") or line.startswith("#!"):
                    continue
                if not line:
                    continue
                if line.startswith('"""') or line.startswith("'''"):
                    desc = line.strip("\"' ")
                    break
                break
        modules.append({
            "name": py_file.stem,
            "file": py_file.name,
            "description": desc,
        })

    return modules


def add_quick_start(lines):
    """添加快速开始部分"""
    lines.append("## 快速开始")
    lines.append("")
    lines.append("```bash")
    lines.append("# 克隆")
    lines.append("git clone https://github.com/biandeshen/Plector.git")
    lines.append("cd Plector")
    lines.append("")
    lines.append("# 安装依赖")
    lines.append("python -m venv venv")
    lines.append("source venv/bin/activate  # Linux/macOS")
    lines.append("# venv\\Scripts\\activate   # Windows")
    lines.append("pip install -r requirements.txt")
    lines.append("")
    lines.append("# 配置 LLM（三选一）")
    lines.append("ollama pull qwen3:4b && ollama serve          # Ollama（本地）")
    lines.append('export OPENAI_API_KEY="sk-xxx"               # OpenAI')
    lines.append('export ANTHROPIC_API_KEY="sk-ant-xxx"        # Anthropic')
    lines.append("")
    lines.append("# 运行")
    lines.append('python channels/cli.py --query "你好"         # CLI 模式')
    lines.append("python channels/websocket.py --port 8080      # Web 模式")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")


def add_core_capabilities(lines):
    """添加核心能力部分"""
    lines.append("## 核心能力")
    lines.append("")
    lines.append("- **自主决策**: ReAct 循环，LLM 推理 → 调用工具 → 观察 → 迭代")
    lines.append("- **多 LLM 后端**: Ollama / OpenAI / Anthropic")
    lines.append("- **技能系统**: 插件化技能，MCP 格式定义")
    lines.append("- **事件驱动**: CloudEvents 1.0，组件异步解耦")
    lines.append("- **MCP 协议**: 连接外部 MCP Server，引入现成工具")
    lines.append("- **闭环引擎**: 条件图执行，支持自动修复")
    lines.append("- **Harness**: 7 项自动化检查，约束代码质量")
    lines.append("")
    lines.append("---")
    lines.append("")


def add_project_structure(lines, core_modules, skills, mcp_servers, channels):
    """添加项目结构部分"""
    lines.append("## 项目结构")
    lines.append("")
    lines.append("```")
    lines.append("Plector/")
    for m in core_modules:
        lines.append(f"├── core/{m['file']:<28} # {m['description']}")
    lines.append(f"├── skills/{'':<25} # {len(skills)} 个技能")
    for s in skills:
        lines.append(
            f"│   ├── {s['name'] + '/':<23} # {s['description']} "
            f"({s['tools_count']} tools)"
        )
    lines.append(f"├── servers/{'':<24} # {len(mcp_servers)} 个 MCP Server")
    for s in mcp_servers:
        lines.append(
            f"│   └── {s['file']:<23} # {s['name']} ({s['tools_count']} tools)"
        )
    lines.append(f"├── channels/{'':<23} # {len(channels)} 个渠道")
    for c in channels:
        lines.append(f"│   └── {c['file']}")
    lines.append("├── config/                         # 配置")
    lines.append("├── docs/                           # 文档")
    lines.append("├── scripts/                        # 检查脚本")
    lines.append("├── tests/                          # 单元测试")
    lines.append("├── CLAUDE.md                       # Claude Code 规范")
    lines.append("└── README.md")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")


def add_skills_list(lines, skills, mcp_servers, total_tools):
    """添加技能清单部分"""
    lines.append("## 技能清单")
    lines.append("")
    lines.append("| 技能 | 工具 | 用途 |")
    lines.append("|------|------|------|")
    for s in skills:
        tool_names = ", ".join(t["name"] for t in s["tools"])
        lines.append(
            f"| {s['name']} | {tool_names} | {s['description']} |"
        )
    for s in mcp_servers:
        lines.append(
            f"| MCP: {s['name']} | (远程工具) | MCP Server |"
        )
    lines.append(f"| **总计** | **{total_tools} 个** | |")
    lines.append("")
    lines.append("---")
    lines.append("")


def add_standards_alignment(lines):
    """添加标准对齐部分"""
    lines.append("## 标准对齐")
    lines.append("")
    lines.append("| 标准 | 组件 | 状态 |")
    lines.append("|------|------|------|")
    lines.append("| MCP Tool 格式 | skill.json | ✅ |")
    lines.append("| OpenAI Function Calling | function_calling.py | ✅ |")
    lines.append("| CloudEvents 1.0 | event_bus.py | ✅ |")
    lines.append("| JSON-RPC 2.0 | function_calling.py + mcp_client.py | ✅ |")
    lines.append("| MCP Protocol | mcp_client.py | ✅ |")
    lines.append("")
    lines.append("---")
    lines.append("")


def add_harness(lines):
    """添加 Harness 部分"""
    lines.append("## Harness（代码质量保障）")
    lines.append("")
    lines.append("| 检查项 | 说明 |")
    lines.append("|--------|------|")
    lines.append("| 依赖方向 | core/ 不依赖 skills/ tools/ |")
    lines.append("| 函数长度 | 单函数 ≤50 行 |")
    lines.append("| 技能语法 | Python 语法检查 |")
    lines.append("| skill.json 格式 | MCP Tool 格式校验 |")
    lines.append("| ruff 代码格式 | PEP8 + 最佳实践 |")
    lines.append("| mypy 类型检查 | 静态类型检查 |")
    lines.append("| pre-commit | Git 提交前自动检查 |")
    lines.append("")
    lines.append("```bash")
    lines.append("pre-commit run --all-files  # 运行全部检查")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")


def add_channels(lines):
    """添加渠道部分"""
    lines.append("## 渠道")
    lines.append("")
    lines.append("| 渠道 | 启动方式 | 访问 |")
    lines.append("|------|---------|------|")
    lines.append("| CLI | `python channels/cli.py --query \"你好\"` | 终端 |")
    lines.append("| WebSocket | `python channels/websocket.py` | http://localhost:8080 |")
    lines.append("")
    lines.append("---")
    lines.append("")


def add_documentation(lines):
    """添加文档部分"""
    lines.append("## 文档")
    lines.append("")
    lines.append("| 文档 | 说明 |")
    lines.append("|------|------|")
    lines.append("| CLAUDE.md | Claude Code 开发规范 |")
    lines.append("| docs/specs/ | 需求文档（BRD / PRD / Design） |")
    lines.append("| docs/standards/ | 规范文档（Code / Naming / Skill / Technical） |")
    lines.append("| docs/reports/ | 状态报告 |")
    lines.append("")
    lines.append("---")
    lines.append("")


def add_license(lines):
    """添加 License 部分"""
    lines.append("## License")
    lines.append("")
    lines.append("MIT")
    lines.append("")


def generate_readme(root):
    """生成 README 内容"""
    version = get_version()
    skills = scan_skills(root)
    mcp_servers = scan_mcp_servers(root)
    channels = scan_channels(root)
    core_modules = scan_core_modules(root)

    total_local_tools = sum(s["tools_count"] for s in skills)
    total_mcp_tools = sum(s["tools_count"] for s in mcp_servers)
    total_tools = total_local_tools + total_mcp_tools

    lines = []
    lines.append("# Plector")
    lines.append("")
    lines.append("> 事件驱动的 AI Agent 引擎")
    lines.append(">")
    lines.append(f"> **当前版本**: `{version}`")
    lines.append(
        f"> **技能**: {len(skills)} 个 | "
        f"**工具**: {total_tools} 个 | "
        f"**核心模块**: {len(core_modules)} 个"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    add_quick_start(lines)
    add_core_capabilities(lines)
    add_project_structure(lines, core_modules, skills, mcp_servers, channels)
    add_skills_list(lines, skills, mcp_servers, total_tools)
    add_standards_alignment(lines)
    add_harness(lines)
    add_channels(lines)
    add_documentation(lines)
    add_license(lines)

    return "\n".join(lines)


def main():
    root = Path(__file__).parent.parent
    readme = generate_readme(root)

    output_path = root / "README.md"
    output_path.write_text(readme, encoding="utf-8")

    print(f"README.md 已生成 ({len(readme)} 字符)")
    print(f"输出: {output_path}")


if __name__ == "__main__":
    main()
