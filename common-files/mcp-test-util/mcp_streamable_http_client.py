import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with streamable_http_client("url-ti-mcp-server") as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

            for tool in result.tools:
                print(tool.name)
                # print(tool.description or "(no description)")
                print(json.dumps(tool.inputSchema, indent=2))
                print()


if __name__ == "__main__":
    asyncio.run(main())
