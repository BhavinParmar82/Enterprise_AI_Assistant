from pathlib import Path

root = Path(__file__).resolve().parent.parent

mcp_servers = {}
servers_folder = root / "mcp_servers"

for server_file in servers_folder.glob("*_mcp.py"):
    server_name = server_file.stem.replace("_mcp", "")
    mcp_servers[server_name] = server_file

print(mcp_servers)