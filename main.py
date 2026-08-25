import os
from dotenv import load_dotenv

# Load environment variables FIRST (critical for LangSmith)
load_dotenv()

# Explicitly set LangSmith (optional but safe)
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "risk-monitor-system"
from langgraph.graph import StateGraph, START, END
from state import AgentState
from agent_nodes import supervisor_node, data_agent_node, rag_agent_node, alert_agent_node, macro_agent_node
from langchain_core.messages import HumanMessage

def build_graph():
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("Supervisor", supervisor_node)
    builder.add_node("Data_Agent", data_agent_node)
    builder.add_node("RAG_Agent", rag_agent_node)
    builder.add_node("Alert_Agent", alert_agent_node)
    builder.add_node("Macro_Agent", macro_agent_node)

    # Set entry point
    builder.add_edge(START, "Supervisor")

    # The router logic
    members = ["Data_Agent", "RAG_Agent", "Macro_Agent"]
    for member in members:
        # Workers always report back to supervisor
        builder.add_edge(member, "Supervisor")
        
    # Alert_Agent goes straight to END to prevent infinite loops
    builder.add_edge("Alert_Agent", END)

    # Conditional edges from supervisor
    conditional_map = {
        "Data_Agent": "Data_Agent",
        "RAG_Agent": "RAG_Agent",
        "Alert_Agent": "Alert_Agent",
        "Macro_Agent": "Macro_Agent",
        "FINISH": END
    }
    builder.add_conditional_edges("Supervisor", lambda x: x["next"], conditional_map)

    return builder.compile()

if __name__ == "__main__":
    print("Starting Risk Monitor Multi-Agent System...")
    
    # Verify Anthropic Key
    if not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") == "your_key_here":
        print("ERROR: ANTHROPIC_API_KEY is not set or is still the default placeholder.")
        print("Please set your API key in the .env file before running.")
        exit(1)
        
    graph = build_graph()
    
    user_input = (
        "Check the risk for my Binance Testnet account. First get my live account balances, then check the policy for any exposure or margin limit breaches, "
        "and if it breaches the threshold, send an alert."
    )
    print(f"\nUser Request: {user_input}\n")
    
    events = graph.stream(
        {"messages": [HumanMessage(content=user_input)]},
        {"recursion_limit": 20}
    )
    
    try:
        for s in events:
            print("---")
            for k, v in s.items():
                print(f"Node: {k}")
                if "messages" in v:
                    for m in v["messages"]:
                        safe_content = m.content.encode('ascii', 'replace').decode('ascii')
                        print(f"  {safe_content}")
                if "next" in v:
                    print(f"  Routing to: {v['next']}")
    except Exception as e:
        print(f"An error occurred during execution: {e}")
