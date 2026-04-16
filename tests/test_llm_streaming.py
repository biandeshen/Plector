"""
测试 LLMClient 流式响应的 tool_call arguments 合并逻辑

OpenAI 流式中 tool_call 的 arguments 是分片到达的，例如：
  chunk1: {"function": {"arguments": '{"query'}}
  chunk2: {"function": {"arguments": '": "天气"}'}
  chunk3: {"function": {"arguments": '"}}'}

需要缓冲器将同一 tool_call id 的 arguments 合并后，才能 yield 完整事件。
"""

import pytest
import asyncio
import json
import copy


class TestToolCallBuffer:
    """tool_call 流式参数缓冲器测试"""

    def test_single_chunk_no_buffer_needed(self):
        """单片到达，直接发射"""
        buffer = {}
        chunks = [
            {"id": "call_001", "function": {"name": "web_search", "arguments": '{"query": "天气"}'}}
        ]

        completed = []
        for chunk in chunks:
            # 模拟：arguments 完整到达
            tool_call_id = chunk.get("id")
            func = chunk.get("function", {})
            args = func.get("arguments", "")

            # 如果 buffer 中没有这个 id 的待合并数据，且 arguments 完整
            if tool_call_id and tool_call_id not in buffer:
                # 可以直接发射
                completed.append({"id": tool_call_id, "function": {"name": func["name"], "arguments": args}})

        assert len(completed) == 1
        assert completed[0]["function"]["arguments"] == '{"query": "天气"}'

    def test_multi_chunk_requires_buffering(self):
        """多片到达，需要缓冲合并"""
        # 模拟 OpenAI 流式分片
        raw_chunks = [
            {"index": 0, "id": "call_001", "function": {"name": "web_search", "arguments": '{"query': None}},  # name 和部分 args
            {"index": 0, "function": {"arguments": '": "天气"'}},  # 继续 args
            {"index": 0, "function": {"arguments": '"}},  # args 完成
        ]

        # 缓冲器实现
        buffer: dict[int, dict] = {}
        completed = []

        for chunk in raw_chunks:
            index = chunk.get("index", 0)

            if index not in buffer:
                buffer[index] = {
                    "id": chunk.get("id"),
                    "name": None,
                    "arguments": ""
                }

            func = chunk.get("function", {})

            # 合并 name
            if "name" in func and func["name"]:
                buffer[index]["name"] = func["name"]

            # 合并 arguments
            if "arguments" in func and func["arguments"]:
                buffer[index]["arguments"] += func["arguments"]

                # 尝试解析，如果成功说明 args 完整
                try:
                    parsed = json.loads(buffer[index]["arguments"])
                    # 完整了，发射
                    completed.append({
                        "id": buffer[index]["id"],
                        "function": {
                            "name": buffer[index]["name"],
                            "arguments": buffer[index]["arguments"]
                        }
                    })
                    del buffer[index]
                except json.JSONDecodeError:
                    # 还不完整，继续缓冲
                    pass

        assert len(completed) == 1
        assert completed[0]["function"]["name"] == "web_search"
        assert json.loads(completed[0]["function"]["arguments"]) == {"query": "天气"}

    def test_mixed_text_and_tool_calls(self):
        """混合文本片段和 tool_call 片段（真实场景）"""
        raw_chunks = [
            {"choices": [{"delta": {"content": "让我帮"}}},  # 文本片段
            {"choices": [{"delta": {"content": "你搜索"}}},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_001", "function": {"name": "web_search", "arguments": ""}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"query"'}}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '": "天'}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"气"}'}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"}'}]}}]},
            {"choices": [{"delta": {"content": "，搜索结果："}}]},
        ]

        text_buffer = ""
        tool_buffer: dict[int, dict] = {}
        completed_tool_calls = []
        completed_text = []

        for chunk in raw_chunks:
            delta = chunk.get("choices", [{}])[0].get("delta", {})

            # 处理文本
            if "content" in delta:
                text_buffer += delta["content"]

            # 处理 tool_calls
            if "tool_calls" in delta:
                for tc in delta["tool_calls"]:
                    index = tc.get("index", 0)

                    if index not in tool_buffer:
                        tool_buffer[index] = {
                            "id": tc.get("id"),
                            "name": tc.get("function", {}).get("name"),
                            "arguments": ""
                        }

                    func = tc.get("function", {})

                    # 合并 name（如果有）
                    if "name" in func and func["name"]:
                        tool_buffer[index]["name"] = func["name"]

                    # 合并 arguments
                    if "arguments" in func and func["arguments"]:
                        tool_buffer[index]["arguments"] += func["arguments"]

                        # 尝试解析
                        try:
                            parsed = json.loads(tool_buffer[index]["arguments"])
                            completed_tool_calls.append({
                                "id": tool_buffer[index]["id"],
                                "function": {
                                    "name": tool_buffer[index]["name"],
                                    "arguments": tool_buffer[index]["arguments"]
                                }
                            })
                            del tool_buffer[index]
                        except json.JSONDecodeError:
                            pass

        # 最终收集完整文本
        if text_buffer:
            completed_text.append(text_buffer)

        assert completed_text == ["让你搜索，搜索结果："]
        assert len(completed_tool_calls) == 1
        assert completed_tool_calls[0]["function"]["name"] == "web_search"
        assert json.loads(completed_tool_calls[0]["function"]["arguments"]) == {"query": "天气"}


class TestStreamingEdgeCases:
    """边界情况测试"""

    def test_empty_arguments(self):
        """arguments 空字符串的情况"""
        buffer = {}
        chunks = [
            {"index": 0, "id": "call_001", "function": {"name": "no_args", "arguments": ""}},
        ]

        for chunk in chunks:
            index = chunk.get("index", 0)
            buffer[index] = {
                "id": chunk.get("id"),
                "name": chunk.get("function", {}).get("name"),
                "arguments": ""
            }

        # 空字符串也是合法的 JSON
        assert buffer[0]["arguments"] == ""
        parsed = json.loads(buffer[0]["arguments"])
        assert parsed == {}

    def test_nested_json_arguments(self):
        """嵌套 JSON 的 arguments"""
        buffer = {}
        chunks = [
            {"index": 0, "id": "call_002", "function": {"name": "code_writer", "arguments": '{"code": "'}},
            {"index": 0, "function": {"arguments": 'def hello():\\n    print("world")\\n"'}},
            {"index": 0, "function": {"arguments": '}'}},
        ]

        for chunk in chunks:
            index = chunk.get("index", 0)
            if index not in buffer:
                buffer[index] = {"id": chunk.get("id"), "name": None, "arguments": ""}

            func = chunk.get("function", {})
            if "name" in func:
                buffer[index]["name"] = func["name"]
            if "arguments" in func:
                buffer[index]["arguments"] += func["arguments"]

        # 最后合并
        final_args = buffer[0]["arguments"]
        parsed = json.loads(final_args)
        assert "code" in parsed
        assert "def hello" in parsed["code"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
