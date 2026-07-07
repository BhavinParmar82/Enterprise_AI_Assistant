# Enterprise AI Assistant

## Overview

This project is an enterprise-focused AI assistant built with Streamlit, LangChain, LangGraph, and MCP (Multi-Server Connector Protocol). It uses a planning graph to route user questions to specialized MCP servers for CRM, Sales, and Finance data, then summarizes the results into an easy-to-understand response.

## Key Components

- `app.py`
  - Streamlit web UI for asking business questions.
  - Displays chat history, planning status, execution results, and tool selection.

- `orchestrator/EnterpriseGraph.py`
  - Defines an enterprise graph with planner, action, and summary nodes.
  - Uses an LLM to decide whether more information is needed or which tools to call.
  - Executes selected MCP tools and summarizes their outputs.

- `orchestrator/LangchainMCPClient.py`
  - Discovers MCP server files under `mcp_servers/`.
  - Connects to all detected servers using `MultiServerMCPClient`.
  - Loads tools and exposes a tool-enabled LLM.

- `mcp_servers/`
  - Contains independent MCP server scripts that expose data tools.
  - Each server runs over stdio and provides domain-specific capabilities.

- `data/`
  - Contains example CSV, JSON, and Excel data sources used by the MCP servers.

## How It Works

1. **User asks a question** in the Streamlit app.
2. `EnterpriseGraph.run_query()` initializes the graph and MCP client if needed.
3. The **planner node** sends the query to the LLM with the user history.
   - The planner determines whether the query needs clarification.
   - If not, it selects tools via `tool_calls`.
4. The **action node** invokes the selected MCP tools.
   - Each tool runs inside its respective MCP server.
   - Results are returned as structured outputs.
5. The **summarize node** generates a clean natural-language response.
6. The app shows:
   - planner reasoning,
   - executed tool names,
   - and the assistant response.

## MCP Servers and Tools

### CRM (`mcp_servers/crm_mcp.py`)
- `get_customer_profile(customer_id)`
- `get_open_opportunities(customer_id)`
- `get_pipeline_summary()`
- `get_high_value_opportunities(threshold)`
- `get_upcoming_followups(customer_id)`
- `search_customers(query)`

### Finance (`mcp_servers/finance_mcp.py`)
- `get_financial_summary(month)`
- `get_monthly_revenue(month)`
- `get_target_vs_actual(month)`
- `get_sales_target(month)`
- `get_target_achievement(month)`
- `get_top_customers(month, top_n)`
- `get_revenue_variance(month)`
- `get_top_revenue_customers(month, top_n)`

### Sales (`mcp_servers/sales_mcp.py`)
- `get_sales_by_month(request)`
- `get_top_customers(request)`

## Running the Project

### Getting Started

1. Create a Python virtual environment:

```bash
python -m venv .venv
```

2. Activate the virtual environment:

- PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

- Command Prompt:

```cmd
.\.venv\Scripts\activate.bat
```

3. Install requirements:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file if needed and add OpenAI credentials:

```env
OPENAI_API_KEY=your_api_key_here
```

### Start the UI

```bash
streamlit run app.py
```

### Check MCP server connectivity

```bash
python khalipeli.py
```

### Run tests and integration checks

```bash
python tests/test.py
python tests/Test_LangchainMCPClient.py
python tests/Test_McpIntegration.py
```

## Package Metadata

- Project name: `enterprise-ai-assistant`
- Python requirement: `>=3.12`
- Main libraries: `streamlit`, `langchain`, `langchain-openai`, `langgraph`, `mcp`, `fastapi`, `pandas`, `pydantic`

## Notes

- The app is designed to keep conversation history with the graph so follow-up questions can reuse previous context.
- MCP servers are discovered dynamically from the `mcp_servers/` folder, so new servers can be added simply by dropping in a `*_mcp.py` file.
- The architecture separates planning, tool execution, and summarization for clearer logic and extendability.
