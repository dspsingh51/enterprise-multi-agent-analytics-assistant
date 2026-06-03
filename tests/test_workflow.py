import pytest
from app.workflows.analytics import analytics_graph
from app.workflows.state import AnalyticsState

def test_workflow_compiles():
    """
    Assert that the compiled state machine is ready to execute.
    """
    assert analytics_graph is not None
    # Check that all agent nodes are registered
    node_keys = analytics_graph.nodes.keys()
    assert "supervisor" in node_keys
    assert "data_analyst" in node_keys
    assert "sql_assistant" in node_keys
    assert "visualization" in node_keys
    assert "insight_generator" in node_keys
    assert "reporter" in node_keys

def test_workflow_execution():
    """
    Run an end-to-end trace query with the mock LLM to ensure the graph executes and completes.
    """
    initial_state = {
        "run_id": "test_run_123",
        "session_id": "session_test",
        "messages": [],
        "current_query": "Show monthly sales trends for Q3",
        "selected_agent": "supervisor",
        "agent_history": [],
        "data_context": "examples/sales_and_marketing_q3.csv",
        "dataframe_summary": "Test Schema columns: region, revenue",
        "sql_query": None,
        "query_result": None,
        "chart_specs": None,
        "insights": None,
        "report_path": None,
        "errors": []
    }
    
    # Run the graph
    final_state = analytics_graph.invoke(initial_state)
    
    assert final_state is not None
    # The supervisor should eventually route to __end__ (which corresponds to END)
    # The output state will contain the history of nodes executed
    assert len(final_state["agent_history"]) > 0
    assert final_state["selected_agent"] == "__end__"
