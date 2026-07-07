import sys
from pathlib import Path
from contextlib import AsyncExitStack

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

class MCPIntegrationTester:
    def __init__(self):
        root = Path(__file__).resolve().parent.parent
        
        self.mcp_servers = {}
        servers_folder = root / "mcp_servers"

        for server_file in servers_folder.glob("*_mcp.py"):
            server_name = server_file.stem.replace("_mcp", "")
            self.mcp_servers[server_name] = server_file
        
        # self.servers = {
        #     "sales": root / "mcp_servers" / "sales_mcp.py",
        #     "crm": root / "mcp_servers" / "crm_mcp.py"
        #     }
        self.sessions = {}
        self.exit_stack = AsyncExitStack()
        self.tool_registry = {}

        
    async def connect(self, server_name: str):
        if server_name not in self.mcp_servers:
            raise ValueError(f"Server '{server_name}' not found.")
        
        server = StdioServerParameters(command=sys.executable, args=[str(self.mcp_servers[server_name])])
        read, write = await self.exit_stack.enter_async_context(stdio_client(server)                                                                )
        session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        
        await session.initialize()
        self.sessions[server_name] = session
        
        tools = await session.list_tools()
        self.tool_registry[server_name] = tools.tools
        
        print(f"Connected to {server_name.upper()} server.")
        
    async def connect_all(self):
        for server_name in self.mcp_servers:
            
            print("server_name", server_name)
            print("self.mcp_servers", self.mcp_servers)
            
            try:
                await self.connect(server_name)
            except FileNotFoundError:
                print(f"⚠ {server_name} server not found.")
            except Exception as e:
                print(f"❌ Failed to connect to {server_name}")
                print(e)
                
    async def list_tools(self):
        print("\n" + "=" * 60)
        print("AVAILABLE TOOLS")
        print("=" * 60)
        for server, tools in self.tool_registry.items():
            print(f"\n{server.upper()}")
            for tool in tools:
                print(f"   • {tool.name}")

    async def call_tool(self,
                        server_name: str,
                        tool_name: str,
                        arguments: dict):
        if server_name not in self.sessions:
            raise ValueError(f"{server_name} not connected.")
        result = await self.sessions[server_name].call_tool(
            tool_name,
            arguments=arguments
        )
        return result

    async def close(self):
        await self.exit_stack.aclose()
        self.sessions.clear()
        self.tool_registry.clear()