import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_loop import AgentLoop

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", help="用户输入")
    args = parser.parse_args()

    if not args.query:
        print("用法: python channels/cli.py --query '你的问题'")
        return

    agent = AgentLoop()
    response = await agent.run(args.query)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
