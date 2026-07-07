from langchain_mcp_adapters.client import MultiServerMCPClient
import sys
from pathlib import Path
import asyncio
from langchain_openai import ChatOpenAI


class LangchainMCPClient:
    def __init__(self):
        self.root = Path(__file__).resolve().parent.parent
        self.client = None
        self.tools = []
        self.tool_map = {}
        self.graph = None
        self.mcp_servers = {}
        self.is_initialized = False
        self.llm = None
        self.llm_with_tools = None

    def find_servers(self):
        self.mcp_servers.clear()
        servers_folder = self.root / "mcp_servers"

        for server_file in servers_folder.glob("*_mcp.py"):
            server_name = server_file.stem.replace("_mcp", "")
            self.mcp_servers[server_name] = {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(server_file)]
            }

    async def initialize(self):
        """Discover MCP servers, connect, fetch tools, and set up the LLM.

        Idempotent — safe to call repeatedly (EnterpriseGraph.initialize()
        and run_query() both call this on every turn).
        """
        if self.is_initialized:
            print("MCP client already initialized.")
            return

        self.find_servers()

        if not self.mcp_servers:
            print("⚠️  No MCP servers found in mcp_servers/ folder.")

        self.client = MultiServerMCPClient(self.mcp_servers)

        # MultiServerMCPClient exposes get_tools() as an async method that
        # connects to each configured server and returns LangChain-compatible
        # tool objects.
        self.tools = await self.client.get_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}

        self.llm = ChatOpenAI(model_name="gpt-4.1-mini", temperature=0)
        self.llm_with_tools = self.llm.bind_tools(self.tools) if self.tools else self.llm

        self.is_initialized = True

        print(f"✅ MCP client initialized with {len(self.tools)} tool(s): "
              f"{[t.name for t in self.tools]}")