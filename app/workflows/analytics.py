from typing import Any, Dict, List
from langgraph.graph import StateGraph, END

# Import State and Agents
from app.workflows.state import AnalyticsState
from app.agents.supervisor import SupervisorAgent
from app.agents.data_analyst import DataAnalystAgent
from app.agents.sql_assistant import SQLAssistantAgent
from app.agents.insight_generator import InsightGeneratorAgent
from app.agents.visualization import VisualizationAgent
from app.agents.reporter import ReporterAgent

# Initialize agents
supervisor_agent = SupervisorAgent()
data_analyst_agent = DataAnalystAgent()
sql_assistant_agent = SQLAssistantAgent()
insight_generator_agent = InsightGeneratorAgent()
visualization_agent = VisualizationAgent()
reporter_agent = ReporterAgent()

# Define Node Wrapper Functions
def supervisor_node(state: AnalyticsState) -> AnalyticsState:
    return supervisor_agent.execute(state)

def data_analyst_node(state: AnalyticsState) -> AnalyticsState:
    return data_analyst_agent.execute(state)

def sql_assistant_node(state: AnalyticsState) -> AnalyticsState:
    return sql_assistant_agent.execute(state)

def insight_generator_node(state: AnalyticsState) -> AnalyticsState:
    return insight_generator_agent.execute(state)

def visualization_node(state: AnalyticsState) -> AnalyticsState:
    return visualization_agent.execute(state)

def reporter_node(state: AnalyticsState) -> AnalyticsState:
    return reporter_agent.execute(state)

# Define Routing Function for Conditional Edge
def route_decision(state: AnalyticsState) -> str:
    """
    Decides where to route next based on Supervisor's decision stored in state.
    """
    next_agent = state.get("selected_agent", END)
    
    if next_agent == "__end__" or not next_agent:
        return END
        
    return next_agent

# Assemble LangGraph Workflow State Machine
workflow = StateGraph(AnalyticsState)

# Add Nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("data_analyst", data_analyst_node)
workflow.add_node("sql_assistant", sql_assistant_node)
workflow.add_node("insight_generator", insight_generator_node)
workflow.add_node("visualization", visualization_node)
workflow.add_node("reporter", reporter_node)

# Set Entry Point
workflow.set_entry_point("supervisor")

# Configure Router (Conditional Edge) from Supervisor
workflow.add_conditional_edges(
    "supervisor",
    route_decision,
    {
        "data_analyst": "data_analyst",
        "sql_assistant": "sql_assistant",
        "visualization": "visualization",
        "insight_generator": "insight_generator",
        "reporter": "reporter",
        END: END
    }
)

# Connect Worker Nodes back to Supervisor for evaluation loop
workflow.add_edge("data_analyst", "supervisor")
workflow.add_edge("sql_assistant", "supervisor")
workflow.add_edge("visualization", "supervisor")
workflow.add_edge("insight_generator", "supervisor")
workflow.add_edge("reporter", "supervisor")

# Compile Graph
analytics_graph = workflow.compile()
