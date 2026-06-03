import re
from typing import Any, Dict
from app.agents.base import BaseAgent
from app.memory.postgres_memory import db_manager
from app.observability.logger import agent_logger

class SQLAssistantAgent(BaseAgent):
    """
    SQL Assistant Agent. Translates natural language queries to database-specific SQL (PostgreSQL/SQLite),
    runs them on the database, and aggregates the results.
    """
    def __init__(self):
        super().__init__("sql_assistant", "Relational Database SQL Assistant")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("current_query", "")
        schema_info = db_manager.get_schema_info()

        prompt = f"""
        You are an expert Enterprise Database SQL Assistant.
        You are given a database schema and a user business question.
        
        Database Schema:
        {schema_info}
        
        User Question:
        "{query}"
        
        Rules:
        - Generate a valid, standard SELECT query that extracts the exact answer.
        - Ensure the SQL query only performs safe SELECT operations. DO NOT execute INSERT, UPDATE, DELETE, or DROP operations.
        - If the query references regions, quarters, or revenue, map them to the table columns correctly.
        - Use clean SQL formatting.
        - Output ONLY the query inside a ```sql ... ``` code block. Do not provide commentary.
        """

        def _run_sql(state_in: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Ask LLM for the SQL query
                llm = self.get_model(state_in)
                response = llm.invoke(prompt)
                llm_output = response.content
                
                # Extract SQL snippet
                sql_match = re.search(r"```sql(.*?)```", llm_output, re.DOTALL)
                sql_query = sql_match.group(1).strip() if sql_match else llm_output.strip()
                
                # Clean up formatting
                sql_query = sql_query.replace(";", "").strip() + ";"
                agent_logger.info(f"Generated SQL Query: {sql_query}")
                
                # Security Check: Ensure only SELECT
                lower_sql = sql_query.lower()
                forbidden_words = ["insert", "update", "delete", "drop", "alter", "truncate", "create table"]
                if any(word in lower_sql for word in forbidden_words):
                    raise ValueError("Security violation: Only SELECT queries are permitted.")
                
                state_in["sql_query"] = sql_query
                
                # Run query
                results = db_manager.execute_query(sql_query)
                
                if not results:
                    output_text = "No records found matching the query criteria."
                else:
                    # Format as Markdown table
                    headers = list(results[0].keys())
                    table_rows = []
                    
                    # Header separator
                    table_rows.append("| " + " | ".join(headers) + " |")
                    table_rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
                    
                    # Rows
                    for row in results:
                        row_vals = []
                        for key in headers:
                            val = row[key]
                            # Clean decimal display
                            if isinstance(val, (int, float)) or str(val).replace('.', '', 1).isdigit():
                                try:
                                    if float(val) > 1000:
                                        row_vals.append(f"${float(val):,.2f}")
                                    else:
                                        row_vals.append(str(val))
                                except ValueError:
                                    row_vals.append(str(val))
                            else:
                                row_vals.append(str(val))
                        table_rows.append("| " + " | ".join(row_vals) + " |")
                        
                    output_text = "\n".join(table_rows)
                
                state_in["query_result"] = output_text
                
                agent_history = state_in.get("agent_history", [])
                agent_history.append({
                    "agent": "sql_assistant",
                    "action": "sql_database_query",
                    "sql": sql_query,
                    "result_summary": output_text[:200] + "..." if len(output_text) > 200 else output_text
                })
                state_in["agent_history"] = agent_history
                
            except Exception as e:
                agent_logger.error(f"SQL execution failed: {e}")
                state_in["errors"] = state_in.get("errors", []) + [f"SQL Assistant failed: {str(e)}"]
                
            return state_in

        return self.run_with_tracing(state.get("run_id", "default"), state, _run_sql)
