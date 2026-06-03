from typing import Any, Dict, List
from app.memory.postgres_memory import db_manager

def get_database_schema() -> str:
    """
    Returns relational database schema metadata.
    """
    return db_manager.get_schema_info()

def query_database(sql: str) -> List[Dict[str, Any]]:
    """
    Executes a SELECT query on the database.
    """
    return db_manager.execute_query(sql)
