from typing import Any, Dict
from app.agents.base import BaseAgent
from app.observability.logger import agent_logger

class InsightGeneratorAgent(BaseAgent):
    """
    Insight Generation Agent. Reviews numerical results and transforms them into
    professional narrative reports, explaining business anomalies and trends.
    """
    def __init__(self):
        super().__init__("insight_generator", "Executive Insights Specialist")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("current_query", "")
        query_result = state.get("query_result", "No query results loaded yet.")
        dataframe_summary = state.get("dataframe_summary", "No CSV schema uploaded.")

        prompt = f"""
        You are an expert Generative AI Architect and Enterprise Business Strategist.
        
        Your objective is to write a high-value Executive Business Insight report based on:
        1. Original User Question: "{query}"
        2. Computed Analytics Outputs:
        {query_result}
        
        Dataset Background Context (if available):
        {dataframe_summary}
        
        Guidelines for the Report:
        - Provide an "Executive Summary" section outlining the critical highlights.
        - Detail "Detailed Insights" explaining any trends, spikes, or anomalous performance drops (e.g. drop in Q3 revenue, regional variances, cost spikes).
        - Outline "Actionable Recommendations" structured as bullet points for executive leaders.
        - Adopt a formal, professional, enterprise-grade tone. Use clear headings and structured lists.
        - Avoid empty placeholders; extrapolate based on the numbers presented.
        
        Output only the completed report in Markdown format.
        """

        def _run_insights(state_in: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Generate insights
                llm = self.get_model(state_in)
                response = llm.invoke(prompt)
                insights_text = response.content
                
                state_in["insights"] = insights_text
                
                agent_history = state_in.get("agent_history", [])
                agent_history.append({
                    "agent": "insight_generator",
                    "action": "insight_extraction",
                    "result_summary": insights_text[:200] + "..." if len(insights_text) > 200 else insights_text
                })
                state_in["agent_history"] = agent_history
                
            except Exception as e:
                agent_logger.error(f"Insight generator failed: {e}")
                state_in["errors"] = state_in.get("errors", []) + [f"Insight Generator failed: {str(e)}"]
                
            return state_in

        return self.run_with_tracing(state.get("run_id", "default"), state, _run_insights)
