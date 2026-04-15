#!/usr/bin/env python3
"""测试流式"""
import asyncio, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI

async def test():
    client = AsyncOpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_BASE_URL'),
    )
    model = 'MiniMax-M2.7'
    print(f'Model: {model}')

    # Test streaming
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'say hi in 5 words'}],
            stream=True,
            max_tokens=20,
        )
        print(f'Stream type: {type(stream)}')
        count = 0
        async for chunk in stream:
            print(f'chunk: {chunk}', end='')
            count += 1
            if count > 5:
                break
        print(f'\nTotal chunks: {count}')
    except Exception as e:
        print(f'Stream error: {e}')

asyncio.run(test())
