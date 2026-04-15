#!/usr/bin/env python3
"""测试流式"""
import asyncio, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI

async def test():
    client = AsyncOpenAI(
        api_key=os.getenv('OPENAI_API_KEY', 'test'),
        base_url=os.getenv('OPENAI_BASE_URL', 'https://api.minimaxi.com/v1'),
    )
    model = 'MiniMax-M2.7'

    try:
        result = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'say hi in 5 words'}],
            stream=True,
            max_tokens=20,
        )
        print(f'Stream type: {type(result)}')
        count = 0
        async for chunk in result:
            print(f'chunk: {chunk.choices[0].delta.content}', end='', flush=True)
            count += 1
            if count >= 3:
                break
        print(f'\nDone, {count} chunks')
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')

asyncio.run(test())
