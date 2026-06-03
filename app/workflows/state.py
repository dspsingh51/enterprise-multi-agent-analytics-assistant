from typing import Any, Dict, List, Optional, TypedDict

class AnalyticsState(TypedDict):
    """
    Defines the global state shared across all agents in the LangGraph workflow.
    """
    # System metadata
    run_id: str
    session_id: str
    gemini_api_key: Optional[str]

    
    # Conversational messages
    messages: List[Dict[str, Any]]
    current_query: str
    
    # Selected path/routing
    selected_agent: str
    agent_history: List[Dict[str, Any]]
    
    # Data contexts
    data_context: Optional[str]           # File path to CSV/Excel
    dataframe_summary: Optional[str]      # Dataframe column/type summary
    
    # Outputs of agent executions
    sql_query: Optional[str]              # Generated SELECT query
    query_result: Optional[str]           # Markdown formatting of results
    chart_specs: Optional[str]            # Plotly JSON config
    insights: Optional[str]               # Business narrative
    report_path: Optional[str]            # Compiled markdown/PDF path
    
    # Error records
    errors: List[str]
