import asyncio
from McpIntegrationTester import MCPIntegrationTester


async def main():

    tester = MCPIntegrationTester()

    await tester.connect_all()

    await tester.list_tools()

    await tester.close()


if __name__ == "__main__":
    asyncio.run(main())