"""Smoke test: start contree-mcp over stdio, list its tools. No tool is called."""
import asyncio
import shutil

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command=shutil.which("contree-mcp"), args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"{len(tools.tools)} tools:")
            for tool in tools.tools:
                print(" -", tool.name)


asyncio.run(asyncio.wait_for(main(), timeout=30))
