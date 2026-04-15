#!/usr/bin/env python3
"""直接测试LLM流式"""
import asyncio, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from core.llm_client_v2 import LLMClientV2

async def test():
    config = {
        "provider": "openai",
        "openai": {
            "api_key": os.getenv('OPENAI_API_KEY'),
            "base_url": os.getenv('OPENAI_BASE_URL'),
            "model": "MiniMax-M2.7",
        }
    }
    client = LLMClientV2(config)
    messages = [{"role": "user", "content": "say hi in 3 words"}]

    print("Testing streaming...")
    count = 0
    try:
        async for chunk in client.stream_chat(messages, tools=None):
            t = chunk.get("type", "")
            if t == "content":
                c = chunk.get("content", "")
                print("got: " + repr(c))
                count += 1
            elif t == "done":
                content = chunk.get("content", "")
                print("done, content: " + content[:50])
    except Exception as e:
        print("ERROR: " + str(e))
    print("Total: " + str(count) + " chunks")

asyncio.run(test())
