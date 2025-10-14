import asyncio
from fastmcp import Client as FastMCPClient

async def test():
    client = FastMCPClient("http://127.0.0.1:8000/mcp")
    async with client:
        tools = await client.list_tools()
        print(tools)

asyncio.run(test())
