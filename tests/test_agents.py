import os
import pytest
from app.agents.base import get_llm, NoAPIKeyError
from app.agents.supervisor import SupervisorAgent
from app.agents.data_analyst import DataAnalystAgent
from app.agents.sql_assistant import SQLAssistantAgent

def test_llm_factory_no_key_raises():
    """
    Ensure the LLM factory raises NoAPIKeyError when no valid key is provided.
    """
    with pytest.raises(NoAPIKeyError):
        get_llm()

def test_llm_factory_with_dynamic_key():
    """
    Ensure the LLM client initializes using the dynamic key.
    """
    # Key starts with Google prefix 'AIzaSy' and is at least 30 chars
    llm = get_llm(api_key="AIzaSyDynamicTestKeyForGeminiAPIKey")
    assert llm is not None

def test_supervisor_initialization():
    """
    Verify Supervisor agent metadata.
    """
    agent = SupervisorAgent()
    assert agent.name == "supervisor"
    assert "router" in agent.role.lower() or "orchestrator" in agent.role.lower()

def test_data_analyst_initialization():
    """
    Verify Data Analyst agent metadata.
    """
    agent = DataAnalystAgent()
    assert agent.name == "data_analyst"
    assert "df" in agent.role.lower() or "data" in agent.role.lower()

def test_sql_assistant_initialization():
    """
    Verify SQL Assistant agent metadata.
    """
    agent = SQLAssistantAgent()
    assert agent.name == "sql_assistant"
    assert "sql" in agent.role.lower() or "database" in agent.role.lower()

def test_supervisor_routing_needs_api_key():
    """
    Test that supervisor routing requires a valid API key in state.
    """
    agent = SupervisorAgent()
    state = {
        "run_id": "test_run",
        "current_query": "Compare region-wise revenue",
        "dataframe_summary": "Dataset File: test.csv",
        "agent_history": [],
        "errors": [],
        "gemini_api_key": None
    }
    # Without a valid API key, the agent should fail gracefully
    updated_state = agent.execute(state)
    # Should have an error in state since no API key was provided
    assert len(updated_state.get("errors", [])) > 0 or updated_state.get("selected_agent") == "__end__"
