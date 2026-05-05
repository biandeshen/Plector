#!/usr/bin/env python3
"""
Plector MCP SQLite Server（纯 Python 实现）

功能：
    1. 执行 SQL 查询（SELECT）
    2. 执行 SQL 写入（INSERT / UPDATE / DELETE）
    3. 列出所有表
    4. 查看表结构

使用方式：
    python servers/sqlite_server.py [数据库路径]

协议：
    JSON-RPC 2.0 over stdio

Author: Plector
Version: 1.0.0
Created: 2026-04-05
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

# 从命令行参数获取数据库路径
if len(sys.argv) > 1:
    DB_PATH = sys.argv[1]
else:
    DB_PATH = "data/plector.db"


def get_connection():
    """获取数据库连接"""
    db = Path(DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db))


# 禁止的 DDL/DML 操作关键字
DANGEROUS_KEYWORDS = [
    "DROP",
    "ALTER",
    "TRUNCATE",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "REINDEX",
    "PRAGMA",
]


def _validate_table_name(name: str) -> str:
    """校验表名，防止 SQL 注入"""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"无效的表名: {name}")
    return name


def handle_query(args):
    """执行 SELECT 查询"""
    sql = args.get("sql", "")
    if not sql:
        return "错误: SQL 语句为空"

    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return "错误: query 工具只支持 SELECT 语句，请使用 execute 工具执行写入操作"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()

        if not rows:
            return "查询结果为空"

        # 转换为格式化文本
        result_lines = []
        result_lines.append("| " + " | ".join(columns) + " |")
        result_lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
        for row in rows:
            result_lines.append("| " + " | ".join(str(v) if v is not None else "NULL" for v in row) + " |")

        return "\n".join(result_lines)
    finally:
        conn.close()


def handle_execute(args):
    """执行 SQL 写入操作"""
    sql = args.get("sql", "")
    if not sql:
        return "错误: SQL 语句为空"

    sql_upper = sql.strip().upper()
    if sql_upper.startswith("SELECT"):
        return "错误: execute 工具不支持 SELECT 语句，请使用 query 工具查询"

    # 检查是否包含危险的 DDL 操作
    first_word = sql_upper.split()[0] if sql_upper.split() else ""
    if first_word in DANGEROUS_KEYWORDS:
        return f"错误: 不允许执行 {first_word} 操作"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        return f"执行成功，影响 {cursor.rowcount} 行"
    except Exception as e:
        return f"执行失败: {e}"
    finally:
        conn.close()


def handle_list_tables(args):
    """列出所有表"""
    _ = args  # unused
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        if not tables:
            return "数据库中没有表"

        result_lines = []
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = cursor.fetchone()[0]
            result_lines.append(f"- {table_name} ({count} 行)")

        return "\n".join(result_lines)
    finally:
        conn.close()


def handle_describe_table(args):
    """查看表结构"""
    table_name = _validate_table_name(args.get("table", ""))
    if not table_name:
        return "错误: 表名为空"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = cursor.fetchall()

        if not columns:
            return f"表 '{table_name}' 不存在"

        result_lines = [f"表: {table_name}", ""]
        result_lines.append("| 列名 | 类型 | 非空 | 默认值 | 主键 |")
        result_lines.append("|------|------|------|--------|------|")
        for col in columns:
            _cid, name, dtype, notnull, default_val, pk = col
            result_lines.append(
                f"| {name} | {dtype} | {'是' if notnull else '否'} | "
                f"{default_val if default_val is not None else '-'} | "
                f"{'是' if pk else '否'} |"
            )

        return "\n".join(result_lines)
    finally:
        conn.close()


# 工具定义
TOOLS = [
    {
        "name": "query",
        "description": "执行 SELECT 查询，返回格式化表格结果",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SELECT 查询语句"},
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
    },
    {
        "name": "execute",
        "description": "执行 SQL 写入操作（INSERT / UPDATE / DELETE / CREATE TABLE）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SQL 写入语句"},
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_tables",
        "description": "列出数据库中的所有表和行数",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "describe_table",
        "description": "查看指定表的结构（列名、类型、约束）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "表名"},
            },
            "required": ["table"],
            "additionalProperties": False,
        },
    },
]

TOOL_HANDLERS = {
    "query": handle_query,
    "execute": handle_execute,
    "list_tables": handle_list_tables,
    "describe_table": handle_describe_table,
}


def handle_initialize(req_id):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "plector-sqlite", "version": "1.0.0"},
        },
    }


def handle_tools_list(req_id):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": TOOLS},
    }


def handle_tools_call(req_id, params):
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"未知工具: {tool_name}"},
        }
    try:
        result_text = handler(arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": result_text}]},
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": f"错误: {e}"}]},
        }


def handle_request(request):
    """处理 JSON-RPC 2.0 请求"""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return handle_initialize(req_id)
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        return handle_tools_list(req_id)
    elif method == "tools/call":
        return handle_tools_call(req_id, params)
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"未知方法: {method}"},
        }


def main():
    """主循环"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            response = handle_request(request)

            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

        except json.JSONDecodeError:
            sys.stdout.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "JSON 解析失败"},
                    }
                )
                + "\n"
            )
            sys.stdout.flush()
        except Exception:
            break


if __name__ == "__main__":
    main()
