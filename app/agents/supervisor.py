import json
import re
from typing import Any, Dict
from app.agents.base import BaseAgent
from app.observability.logger import agent_logger
from app.config import settings

class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent acts as the central router for user requests,
    determining the state path and invoking the next appropriate agent.
    """
    def __init__(self):
        super().__init__("supervisor", "Workflow Orchestrator and Semantic Router")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("current_query", "")
        dataframe_summary = state.get("dataframe_summary", "")
        agent_history = state.get("agent_history", [])
        errors = state.get("errors", [])
        
        # Guard clause: Stop if we are looping too much or have persistent errors
        if len(agent_history) >= 8:
            agent_logger.warning("Max routing depth reached. Ending workflow.")
            state["selected_agent"] = "__end__"
            return state
            
        if errors and len(errors) >= 3:
            agent_logger.warning(f"Aborting due to multiple errors: {errors}")
            state["selected_agent"] = "__end__"
            return state

        # Compile chat history context
        messages = state.get("messages", [])
        history_context = ""
        if messages:
            history_context = "\nConversation History:\n"
            for msg in messages[-settings.CONVERSATION_HISTORY_LIMIT:]:
                history_context += f"- {msg['role'].capitalize()}: {msg['content']}\n"

        # Compile current outputs context
        query_result = state.get("query_result", "")
        insights = state.get("insights", "")
        chart_specs = state.get("chart_specs", "")
        report_path = state.get("report_path", "")
        
        outputs_context = ""
        if query_result or insights or chart_specs or report_path:
            outputs_context = "\nCurrent Computed Outputs in State:\n"
            if query_result:
                outputs_context += f"- Data Query Result (computed by data_analyst/sql_assistant):\n{str(query_result)[:500]}\n"
            if insights:
                outputs_context += f"- Insights (computed by insight_generator):\n{str(insights)[:300]}...\n"
            if chart_specs:
                outputs_context += f"- Chart Specifications: [Generated Plotly Config]\n"
            if report_path:
                outputs_context += f"- Report Path: {report_path}\n"

        # Build prompt history context
        visited_agents = [step.get("agent") for step in agent_history]
        
        prompt = f"""
        You are the Supervisor Agent of an Enterprise Multi-Agent Analytics Assistant.
        Your job is to route the user's business query to the correct specialized agent.

        {history_context}
        {outputs_context}
        User Request: "{query}"

        Available Specialized Agents:
        1. "data_analyst": Performs direct dataframe queries, statistics, and counts on the loaded CSV/Excel dataset. Use this if the user asks for sales aggregates, performance rankings, average calculations, or column filters on their uploaded files.
        2. "sql_assistant": Accesses the corporate relational database. Use this if the query mentions "corporate sales", "database table", "quarterly sales", or references structural database schemas.
        3. "visualization": Generates Plotly charts (bar, line, scatter, pie) from query results. Use this if the user specifically requests a chart, trend line, plot, dashboard, or visual representation.
        4. "insight_generator": Analyzes data aggregates to generate executive summaries, explanation of trends (like why sales dropped), and business recommendations. Use this when the user asks qualitative business questions or needs an overall executive summary.
        5. "reporter": Generates official business summaries in structured Markdown/PDF reports. Use this if the user explicitly asks to "generate report", "create PDF summary", or "write documentation".

        Execution Rules:
        - If a specialized agent has ALREADY run and produced results (e.g. data_analyst or sql_assistant has populated the query_result), and the user requested a chart, route to "visualization".
        - If data analysis results are ready and the query requires high-level insights or explanations, route to "insight_generator".
        - If all requested tasks (data query, charts, insights) have been completed, output "__end__" to deliver the final response to the user.
        - Analyze the history of agents run so far: {visited_agents}

        Dataset schema info:
        {dataframe_summary if dataframe_summary else "No local file uploaded yet. The corporate database is available via sql_assistant."}

        You must respond in valid JSON format only, matching the schema:
        {{
            "next_agent": "data_analyst" | "sql_assistant" | "visualization" | "insight_generator" | "reporter" | "__end__",
            "reasoning": "Brief explanation of why you selected this agent"
        }}
        """

        try:
            # Call LLM
            llm = self.get_model(state)
            response = llm.invoke(prompt)
            content = response.content
            
            # Clean JSON formatting wrappers
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(content.strip())
            next_agent = parsed.get("next_agent", "__end__")
            reasoning = parsed.get("reasoning", "No reason provided")
            
            # Basic validation
            valid_agents = ["data_analyst", "sql_assistant", "visualization", "insight_generator", "reporter", "__end__"]
            if next_agent not in valid_agents:
                next_agent = "__end__"
                
            agent_logger.info(f"Supervisor Route Decision: {next_agent} | Reasoning: {reasoning}")
            
            # Set state output
            state["selected_agent"] = next_agent
            agent_history.append({
                "agent": "supervisor",
                "decision": next_agent,
                "reasoning": reasoning
            })
            state["agent_history"] = agent_history
            
        except Exception as e:
            agent_logger.error(f"Supervisor failed to parse route: {e}. Defaulting to __end__")
            state["selected_agent"] = "__end__"
            state["errors"] = state.get("errors", []) + [f"Supervisor router failed: {str(e)}"]

        return state
