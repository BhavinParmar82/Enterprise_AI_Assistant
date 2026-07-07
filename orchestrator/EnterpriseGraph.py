from dotenv import load_dotenv
from typing import TypedDict, Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from orchestrator.LangchainMCPClient import LangchainMCPClient
import asyncio
import json
from tabulate import tabulate

load_dotenv()

llm = ChatOpenAI(model_name="gpt-4.1-mini", temperature=0)


class EnterpriseGraphState(TypedDict):
    user_query: str
    conversation_history: list
    planner_result: str
    need_more_info: bool
    clarification_question: str
    planned_actions: list
    action_results: list
    final_response: Optional[str]


def format_results(tool_results: list):
    """Format raw MCP tool results into readable tables."""
    for item in tool_results:
        print(f"\n🔧 Tool: {item['tool']}")
        print("-" * 60)

        rows = []
        for block in item["result"]:
            if isinstance(block, dict) and block.get("type") == "text":
                try:
                    parsed = json.loads(block["text"])
                    rows.append(parsed)
                except (json.JSONDecodeError, KeyError):
                    print(f"  {block.get('text', block)}")

        if rows:
            headers = list(rows[0].keys())
            table_data = [list(row.values()) for row in rows]
            print(tabulate(table_data, headers=headers,
                           tablefmt="rounded_outline",
                           floatfmt=".2f", numalign="right"))


class EnterpriseGraph:
    def __init__(self):
        self.mcp = LangchainMCPClient()
        self.graph = None
        self.tools = []

    async def initialize(self):
        if self.graph is None:
            await self.mcp.initialize()
            # Pull tools from the MCP client so action_node can find them.
            self.tools = getattr(self.mcp, "tools", [])
            self.graph = self.build_graph()
        else:
            print("Graph already initialized.")

    # ---------------- Nodes ----------------

    async def planner_node(self, state: EnterpriseGraphState) -> EnterpriseGraphState:
        """Analyze the user query and determine if more information is needed."""

        history = state.get("conversation_history", [])
        user_query = state.get("user_query", "")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an enterprise AI assistant. "
                    "Given the user query, analyze it and ALWAYS start your response with this exact block:\n\n"
                    "ANALYSIS:\n"
                    "- need_more_info: <true or false>\n"
                    "- reason: <why you need more info OR what you will do>\n"
                    "- clarification_question: <your question if need_more_info is true, else 'N/A'>\n\n"
                    "Then explain your plan and call the appropriate tools if need_more_info is false."
                )
            },
            *history,
            {
                "role": "user",
                "content": user_query
            }
        ]

        response = await self.mcp.llm_with_tools.ainvoke(messages)

        need_more_info = False
        clarification_question = "N/A"

        if response.content:
            for line in response.content.splitlines():
                line_lower = line.strip().lower()
                if "need_more_info:" in line_lower:
                    value = line_lower.split("need_more_info:")[-1].strip()
                    need_more_info = value == "true"
                if "clarification_question:" in line_lower:
                    clarification_question = line.strip().split("clarification_question:")[-1].strip()

        print(f"\n [PLANNER] need_more_info: {need_more_info}")
        print(f" [PLANNER] tools planned : {[t['name'] for t in response.tool_calls] if response.tool_calls else 'None'}")
        print(f" [PLANNER] clarification_question: {clarification_question}")

        return {
            **state,
            "user_query": user_query,
            "conversation_history": history + [HumanMessage(content=user_query), AIMessage(content=response.content)],
            "planner_result": response.content,
            "need_more_info": need_more_info,
            "clarification_question": clarification_question,
            "planned_actions": response.tool_calls if response.tool_calls else []
        }

    def ask_user_node(self, state: EnterpriseGraphState) -> EnterpriseGraphState:
        """Surface the clarification question and end this turn.

        No blocking input() here — callers (e.g. a web UI) don't have a
        terminal attached. This node just hands the question back as
        final_response; the caller collects the user's reply and starts
        a new run_query() call with it, passing the existing
        conversation_history back in so context isn't lost.
        """
        return {
            **state,
            "final_response": state["clarification_question"]
        }

    async def action_node(self, state: EnterpriseGraphState) -> EnterpriseGraphState:
        """Execute the actions needed to fulfill the plan by calling tools."""

        planned_actions = state.get("planned_actions", [])
        history = state.get("conversation_history", [])

        tool_map = {tool.name: tool for tool in self.tools}
        tool_results = []

        for tool_call in planned_actions:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"   🔧 Calling: {tool_name} | Args: {tool_args}")

            if tool_name in tool_map:
                try:
                    result = await tool_map[tool_name].ainvoke(tool_args)
                    print(f"   ✅ {tool_name} done")
                    tool_results.append({"tool": tool_name, "result": result})
                except Exception as e:
                    print(f"   ❌ {tool_name} failed: {e}")
                    tool_results.append({"tool": tool_name, "result": f"Error: {str(e)}"})
            else:
                print(f"   ⚠️  Tool '{tool_name}' not found")

        action_results_text = "\n\n".join([
            f"[{r['tool']}]:\n{r['result']}" for r in tool_results
        ])

        return {
            **state,
            "action_results": tool_results,
            "conversation_history": history + [AIMessage(content=action_results_text)]
        }

    async def summarize_node(self, state: EnterpriseGraphState) -> EnterpriseGraphState:
        """Summarizes the action results into a clean user response."""

        messages = [
            SystemMessage(content="""You are a helpful assistant.
                          Summarize the action results into a clear, concise, user-friendly response.
                          Be direct and avoid technical jargon."""),
            HumanMessage(content=f"""Original Query: {state['user_query']}
                          Action Results: {state['action_results']}
                          Provide a clean summary for the user.""")
        ]

        response = await self.mcp.llm.ainvoke(messages)

        print("✅ Summary generated")
        return {**state, "final_response": response.content}

    # ---------------- Graph wiring ----------------

    @staticmethod
    def check_needs_more_info(state: EnterpriseGraphState) -> Literal["ask_user", "action"]:
        if state["need_more_info"] is True:
            return "ask_user"
        return "action"

    def build_graph(self):
        builder = StateGraph(EnterpriseGraphState)

        builder.add_node("planner", self.planner_node)
        builder.add_node("ask_user", self.ask_user_node)
        builder.add_node("action", self.action_node)
        builder.add_node("summarize", self.summarize_node)

        builder.set_entry_point("planner")

        builder.add_conditional_edges(
            source="planner",
            path=self.check_needs_more_info,
            path_map={"ask_user": "ask_user", "action": "action"}
        )
        builder.add_edge("ask_user", END)
        builder.add_edge("action", "summarize")
        builder.add_edge("summarize", END)
        return builder.compile()

    # ---------------- Entry point ----------------

    async def run_query(self, user_query: str, history: list = None):
        """Run the enterprise graph with the given user query and conversation history."""
        await self.initialize()
        initial_state: EnterpriseGraphState = {
            "user_query": user_query,
            "conversation_history": history or [],
            "planner_result": "",
            "need_more_info": False,
            "clarification_question": "",
            "planned_actions": [],
            "action_results": [],
            "final_response": None
        }
        final_state = await self.graph.ainvoke(initial_state)
        print(final_state)
        return final_state


async def main():
    graph = EnterpriseGraph()
    history = []
    query = input("Enter your query: ").strip()
    while True:
        state = await graph.run_query(query, history=history)
        history = state["conversation_history"]
        print(f"\nAssistant: {state.get('final_response')}")
        if not state["need_more_info"]:
            break
        query = input("\n USER : ").strip()


if __name__ == "__main__":
    asyncio.run(main())