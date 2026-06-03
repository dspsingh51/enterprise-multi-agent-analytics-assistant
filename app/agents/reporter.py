import os
import time
from typing import Any, Dict
from app.config import settings
from app.agents.base import BaseAgent
from app.observability.logger import agent_logger

class ReporterAgent(BaseAgent):
    """
    Reporter Agent. Aggregates all insights, tables, and system diagnostics
    into a comprehensive, publication-grade markdown document.
    """
    def __init__(self):
        super().__init__("reporter", "Executive Briefing Compiler")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        run_id = state.get("run_id", "default")
        query = state.get("current_query", "")
        query_result = state.get("query_result", "")
        insights = state.get("insights", "")
        sql_query = state.get("sql_query", "")
        
        # Build prompt
        prompt = f"""
        You are an expert Executive Rapporteur.
        Your job is to compile a formal enterprise-grade business briefing report.
        
        Inputs:
        - Report Title based on: "{query}"
        - Query Result Data:
        {query_result}
        - Strategic Insights:
        {insights}
        - Generated SQL Query (if any):
        {sql_query}
        
        Formatting Requirements:
        - Include an executive title block with "Author: Enterprise Analytics Multi-Agent Platform" and a simulated timestamp.
        - Structure sections clearly with dividers (`---`), headings (`##`), and neat lists.
        - Merge the data table and qualitative insights into a cohesive narrative structure.
        - Format code blocks nicely.
        
        Output only the completed briefing document in Markdown format.
        """

        def _run_report(state_in: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Ask LLM to format the report
                llm = self.get_model(state_in)
                response = llm.invoke(prompt)
                report_content = response.content
                
                # Ensure reports directory exists
                os.makedirs(settings.REPORTS_DIR, exist_ok=True)
                
                report_filename = f"report_{run_id}.md"
                report_filepath = os.path.join(settings.REPORTS_DIR, report_filename)
                
                # Save report file
                with open(report_filepath, "w", encoding="utf-8") as f:
                    f.write(report_content)
                    
                agent_logger.info(f"Report successfully compiled and written to: {report_filepath}")
                
                # Update state
                state_in["report_path"] = report_filepath
                
                agent_history = state_in.get("agent_history", [])
                agent_history.append({
                    "agent": "reporter",
                    "action": "report_generation",
                    "file_path": report_filepath
                })
                state_in["agent_history"] = agent_history
                
            except Exception as e:
                agent_logger.error(f"Reporter execution failed: {e}")
                state_in["errors"] = state_in.get("errors", []) + [f"Reporter failed: {str(e)}"]
                
            return state_in

        return self.run_with_tracing(run_id, state, _run_report)
