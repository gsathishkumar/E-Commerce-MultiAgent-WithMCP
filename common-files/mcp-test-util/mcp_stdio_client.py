# list_mcp_tools.py
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server = StdioServerParameters(
        command="python",
        args=["path/to/your_mcp_server.py"],
        env=os.environ.copy(),
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.list_tools()

            print(f"Found {len(result.tools)} tool(s)\n")
            for tool in result.tools:
                print(f"Name: {tool.name}")
                print(f"Description: {tool.description or '(no description)'}")
                print("Input schema:")
                print(json.dumps(tool.inputSchema, indent=2))
                print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
