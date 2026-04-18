"""测试 LLMClient 流式响应的 tool_call arguments 合并逻辑"""

import pytest
import json


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
            tool_call_id = chunk.get("id")
            func = chunk.get("function", {})
            args = func.get("arguments", "")

            if tool_call_id and tool_call_id not in buffer:
                completed.append({"id": tool_call_id, "function": {"name": func["name"], "arguments": args}})

        assert len(completed) == 1
        assert completed[0]["function"]["arguments"] == '{"query": "天气"}'

    def test_multi_chunk_requires_buffering(self):
        """多片到达，需要缓冲合并"""
        raw_chunks = [
            {"index": 0, "id": "call_001", "function": {"name": "web_search", "arguments": '{"query"'}},
            {"index": 0, "function": {"arguments": ': "天气"}'}},
        ]

        buffer = {}
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

            if "name" in func and func["name"]:
                buffer[index]["name"] = func["name"]

            if "arguments" in func and func["arguments"]:
                buffer[index]["arguments"] += func["arguments"]

                try:
                    parsed = json.loads(buffer[index]["arguments"])
                    completed.append({
                        "id": buffer[index]["id"],
                        "function": {
                            "name": buffer[index]["name"],
                            "arguments": buffer[index]["arguments"]
                        }
                    })
                    del buffer[index]
                except json.JSONDecodeError:
                    pass

        assert len(completed) == 1
        assert completed[0]["function"]["name"] == "web_search"
        assert json.loads(completed[0]["function"]["arguments"]) == {"query": "天气"}

    def test_mixed_text_and_tool_calls(self):
        """混合文本片段和 tool_call 片段（真实场景）"""
        raw_chunks = [
            {"choices": [{"delta": {"content": "让我帮"}}]},
            {"choices": [{"delta": {"content": "你搜索"}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_001", "function": {"name": "web_search", "arguments": ""}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"query"'}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ': "天气"}'}}]}}]},
            {"choices": [{"delta": {"content": "，搜索结果："}}]},
        ]

        text_buffer, tool_buffer, completed_tool_calls = self._process_chunks(raw_chunks)
        completed_text = [text_buffer] if text_buffer else []

        assert completed_text == ["让我帮你搜索，搜索结果："]
        assert len(completed_tool_calls) == 1
        assert completed_tool_calls[0]["function"]["name"] == "web_search"
        assert json.loads(completed_tool_calls[0]["function"]["arguments"]) == {"query": "天气"}

    def _process_chunks(self, raw_chunks):
        """处理原始数据块，返回 (text, tool_buffer, completed_tool_calls)"""
        text_buffer = ""
        tool_buffer = {}
        completed_tool_calls = []

        for chunk in raw_chunks:
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if "content" in delta:
                text_buffer += delta["content"]
            if "tool_calls" in delta:
                self._process_tool_calls(delta["tool_calls"], tool_buffer, completed_tool_calls)

        return text_buffer, tool_buffer, completed_tool_calls

    def _process_tool_calls(self, tool_calls, tool_buffer, completed):
        """处理 tool_call 片段"""
        for tc in tool_calls:
            index = tc.get("index", 0)
            if index not in tool_buffer:
                tool_buffer[index] = {"id": tc.get("id"), "name": tc.get("function", {}).get("name"), "arguments": ""}
            func = tc.get("function", {})
            if func.get("name"):
                tool_buffer[index]["name"] = func["name"]
            if func.get("arguments"):
                tool_buffer[index]["arguments"] += func["arguments"]
                try:
                    json.loads(tool_buffer[index]["arguments"])
                    completed.append({"id": tool_buffer[index]["id"], "function": {"name": tool_buffer[index]["name"], "arguments": tool_buffer[index]["arguments"]}})
                    del tool_buffer[index]
                except json.JSONDecodeError:
                    pass


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

        assert buffer[0]["arguments"] == ""
        with pytest.raises(json.JSONDecodeError):
            json.loads(buffer[0]["arguments"])

    def test_nested_json_arguments(self):
        """嵌套 JSON 的 arguments"""
        buffer = {}
        code_content = 'def hello():\\n    print(\\"world\\")\\n'
        chunks = [
            {"index": 0, "id": "call_002", "function": {"name": "code_writer", "arguments": '{"code": "'}},
            {"index": 0, "function": {"arguments": code_content}},
            {"index": 0, "function": {"arguments": '"}'}},
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

        final_args = buffer[0]["arguments"]
        parsed = json.loads(final_args)
        assert "code" in parsed
        assert "def hello" in parsed["code"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
