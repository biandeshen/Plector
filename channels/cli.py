import argparse
import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix Windows console encoding for UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from core.agent_loop import AgentLoop


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", help="用户输入")
    args = parser.parse_args()

    if not args.query:
        print("用法: python channels/cli.py --query '你的问题'")
        return

    agent = AgentLoop()
    try:
        streamed = False
        async for event in agent.run_streaming(args.query):
            etype = event.get("type")
            if etype == "chunk":
                print(event.get("content", ""), end="", flush=True)
                streamed = True
            elif etype == "done":
                # If no chunks were streamed (e.g. image command), print the final content
                if not streamed and event.get("content"):
                    print(event["content"])
                else:
                    print()  # trailing newline after streamed chunks
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
