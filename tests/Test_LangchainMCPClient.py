import asyncio
from orchestrator.LangchainMCPClient import EnterpriseGraph

async def main():

    graph = EnterpriseGraph()

    await graph.initialize()

    print("\n" + "=" * 60)
    print("CONNECTED SERVERS")
    print("=" * 60)

    for server in graph.mcp_servers:
        print(f"✓ {server}")

    print("\n" + "=" * 60)
    print("AVAILABLE TOOLS")
    print("=" * 60)

    for tool in graph.tools:
        print(f"• {tool.name}")

    print("\nTotal Servers :", len(graph.mcp_servers))
    print("Total Tools   :", len(graph.tools))


if __name__ == "__main__":
    asyncio.run(main())