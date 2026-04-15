#!/usr/bin/env python3
"""测试MiniMax流式"""
import httpx, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('OPENAI_API_KEY')
host = os.getenv('OPENAI_BASE_URL')
print(f'Host: {host}')

r = httpx.post(f'{host}/chat/completions',
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    json={'model': 'auto', 'stream': True, 'messages': [{'role': 'user', 'content': 'hi'}], 'max_tokens': 20},
    timeout=15)
print(f'Status: {r.status_code}')
print(f'Headers: {dict(r.headers)}')
print(f'Content: {r.text[:300]}')
