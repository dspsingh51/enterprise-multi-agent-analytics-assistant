import json
import re
from typing import Any, Dict
from app.agents.base import BaseAgent
from app.observability.logger import agent_logger

class VisualizationAgent(BaseAgent):
    """
    Visualization Agent. Evaluates data aggregates and formats them into
    fully structured Plotly JSON specifications for interactive frontend charting.
    """
    def __init__(self):
        super().__init__("visualization", "Chart Spec Architect")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("current_query", "")
        query_result = state.get("query_result", "")
        dataframe_summary = state.get("dataframe_summary", "")

        prompt = f"""
        You are an expert Frontend Visualization Specialist.
        Your goal is to generate a declarative Plotly chart JSON configuration based on data values and a user request.

        User Request: "{query}"
        Data Results:
        {query_result}
        
        Dataset Schema:
        {dataframe_summary}

        Rules:
        - Determine the most appropriate chart type (e.g. bar, line, pie, scatter) to answer the query.
        - Generate a valid JSON configuration containing both "data" and "layout" properties for Plotly.js.
        - Style the chart for a premium dark enterprise dashboard:
          - Use a high-contrast text color (e.g., set font color to '#F8FAFC' for title, axes labels, and legend).
          - Use a vibrant, modern multi-color palette for data elements (e.g., '#3B82F6' for primary, '#10B981' for secondary, and '#EC4899' or '#F59E0B' for contrast).
          - Make the plot background transparent by setting "paper_bgcolor": "rgba(0,0,0,0)" and "plot_bgcolor": "rgba(0,0,0,0)".
          - Ensure axes titles and tick marks are clearly visible with high-contrast colors (e.g. gridcolor '#334155', tickfont color '#94A3B8').
        - Output ONLY the raw JSON block inside ```json ... ```. No extra conversations.

        Example Output format:
        ```json
        {{
          "data": [
            {{
              "type": "bar",
              "x": ["Q1", "Q2", "Q3"],
              "y": [120, 150, 90],
              "name": "Quarterly Sales"
            }}
          ],
          "layout": {{
            "title": "Corporate Sales Volume",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)"
          }}
        }}
        ```
        """

        def _run_viz(state_in: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Ask LLM for the Plotly JSON config
                llm = self.get_model(state_in)
                response = llm.invoke(prompt)
                llm_output = response.content
                
                # Extract json code block
                json_match = re.search(r"```json(.*?)```", llm_output, re.DOTALL)
                json_str = json_match.group(1).strip() if json_match else llm_output.strip()
                
                # Parse to ensure it is valid JSON
                chart_dict = json.loads(json_str)
                state_in["chart_specs"] = json.dumps(chart_dict)
                
                agent_history = state_in.get("agent_history", [])
                agent_history.append({
                    "agent": "visualization",
                    "action": "plotly_chart_specification",
                    "chart_type": chart_dict.get("data", [{}])[0].get("type", "unknown")
                })
                state_in["agent_history"] = agent_history
                
            except Exception as e:
                agent_logger.error(f"Visualization agent failed: {e}")
                state_in["errors"] = state_in.get("errors", []) + [f"Visualization Agent failed: {str(e)}"]
                
            return state_in

        return self.run_with_tracing(state.get("run_id", "default"), state, _run_viz)
