import os
import sys
import pandas as pd
from io import StringIO
from typing import Any, Dict
from app.agents.base import BaseAgent
from app.observability.logger import agent_logger
from app.config import settings

class DataAnalystAgent(BaseAgent):
    """
    Data Analysis Agent. Executes pandas operations on uploaded datasets
    to calculate KPIs, perform aggregations, and query columns.
    """
    def __init__(self):
        super().__init__("data_analyst", "DataFrame & Local KPI Analyst")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("current_query", "")
        data_path = state.get("data_context", "")
        dataframe_summary = state.get("dataframe_summary", "")
        
        if not data_path or not os.path.exists(data_path):
            agent_logger.warning("No data file path available in context. Data Analyst cannot run.")
            state["errors"] = state.get("errors", []) + ["No dataset uploaded for analysis. Please upload a file."]
            return state

        # Compile chat history context
        messages = state.get("messages", [])
        history_context = ""
        if messages:
            history_context = "\nConversation History:\n"
            for msg in messages[-settings.CONVERSATION_HISTORY_LIMIT:]:
                history_context += f"- {msg['role'].capitalize()}: {msg['content']}\n"

        # Prompt the LLM to generate standard Pandas code to answer the query
        prompt = f"""
        You are an expert Data Analyst Agent. You are provided with:
        1. A user query: "{query}"
        {history_context}
        2. A CSV/Excel file path: "{data_path}"
        3. A summary of the dataset:
        {dataframe_summary}

        Your task is to write a single Python script that processes a pandas DataFrame named `df` to answer the query.
        
        Rules:
        - The DataFrame `df` is already loaded from the dataset.
        - You must write Python code that calculates the answer and prints the output using `print()`.
        - Format the printed output nicely (e.g. as a clean markdown table, list of key-value metrics, or bullet points).
        - Do NOT import plotly or generate charts. Only calculate the raw statistics, rankings, groupings, or aggregate numbers.
        - Keep the script short, simple, and self-contained.
        - Output ONLY the raw Python code block enclosed in ```python ... ```. Do not add any explanatory text.

        Example Output format:
        ```python
        # Calculate regional revenue
        regional_rev = df.groupby('region')['revenue'].sum().reset_index()
        print(regional_rev.to_markdown(index=False))
        ```
        """

        def _run_analyst(state_in: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Get Pandas script from LLM
                llm = self.get_model(state_in)
                response = llm.invoke(prompt)
                code_content = response.content
                
                # Extract python block
                code = ""
                if "```python" in code_content:
                    code = code_content.split("```python")[1].split("```")[0].strip()
                elif "```" in code_content:
                    code = code_content.split("```")[1].split("```")[0].strip()
                else:
                    code = code_content.strip()
                
                agent_logger.info(f"Generated Python Code for Analysis:\n{code}")
                
                # Load the dataframe
                if data_path.endswith('.xlsx') or data_path.endswith('.xls'):
                    df = pd.read_excel(data_path)
                else:
                    df = pd.read_csv(data_path)
                
                # Execute the code capturing stdout
                old_stdout = sys.stdout
                redirected_output = sys.stdout = StringIO()
                
                # Define sandbox variables
                local_vars = {"df": df, "pd": pd}
                
                try:
                    exec(code, {}, local_vars)
                    sys.stdout = old_stdout
                    output_text = redirected_output.getvalue()
                except Exception as eval_err:
                    sys.stdout = old_stdout
                    output_text = f"Execution error in Pandas Script: {eval_err}"
                    agent_logger.error(output_text)
                    
                agent_logger.info(f"Execution Output:\n{output_text}")
                
                # Update state
                state_in["query_result"] = output_text
                
                agent_history = state_in.get("agent_history", [])
                agent_history.append({
                    "agent": "data_analyst",
                    "action": "dataframe_computation",
                    "result_summary": output_text[:200] + "..." if len(output_text) > 200 else output_text
                })
                state_in["agent_history"] = agent_history
                
            except Exception as e:
                agent_logger.error(f"Data analyst execution failed: {e}")
                state_in["errors"] = state_in.get("errors", []) + [f"Data Analyst failed: {str(e)}"]
                
            return state_in

        return self.run_with_tracing(state.get("run_id", "default"), state, _run_analyst)
