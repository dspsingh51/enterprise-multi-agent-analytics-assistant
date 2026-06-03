import time
from typing import Any, Dict, List
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from app.config import settings
from app.observability.logger import db_logger

class DatabaseManager:
    """
    Manages connections to PostgreSQL or SQLite.
    Automatically falls back to SQLite if PostgreSQL is unavailable.
    """
    def __init__(self):
        self.engine = None
        self.is_sqlite = False
        self._init_database()

    def _init_database(self):
        # Try connecting to PostgreSQL
        if settings.ENVIRONMENT == "docker" or settings.POSTGRES_HOST != "localhost":
            db_logger.info("Attempting connection to PostgreSQL...")
            pg_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            try:
                self.engine = create_engine(pg_url, pool_pre_ping=True)
                # Test connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                db_logger.info("Successfully connected to PostgreSQL database.")
                self.is_sqlite = False
                self._seed_data()
                return
            except (OperationalError, Exception) as e:
                db_logger.warning(f"PostgreSQL connection failed: {e}. Falling back to SQLite.")

        # Fallback to SQLite
        db_logger.info("Initializing SQLite database as fallback...")
        sqlite_url = "sqlite:///analytics_assistant_fallback.db"
        self.engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        self.is_sqlite = True
        self._seed_data()

    def _seed_data(self):
        """
        Seeds the relational database with mock corporate sales data if it's empty.
        """
        try:
            with self.engine.begin() as conn:
                # Create table
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS corporate_sales (
                    id INTEGER PRIMARY KEY,
                    region VARCHAR(50),
                    quarter VARCHAR(10),
                    year INTEGER,
                    revenue DECIMAL(12, 2),
                    operational_cost DECIMAL(12, 2),
                    sales_channel VARCHAR(50)
                );
                """
                # For sqlite/postgres syntax normalization
                if not self.is_sqlite:
                    create_table_sql = create_table_sql.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")
                
                conn.execute(text(create_table_sql))
                
                # Check if data already exists
                result = conn.execute(text("SELECT COUNT(*) FROM corporate_sales"))
                count = result.scalar()
                
                if count == 0:
                    db_logger.info("Database is empty. Seeding corporate sales records...")
                    records = [
                        ("North America", "Q1", 2025, 4500000.00, 3100000.00, "Direct"),
                        ("North America", "Q2", 2025, 4800000.00, 3200000.00, "Direct"),
                        ("North America", "Q3", 2025, 4100000.00, 3400000.00, "Direct"), # revenue drop
                        ("North America", "Q4", 2025, 5200000.00, 3300000.00, "Direct"),
                        ("Europe", "Q1", 2025, 3200000.00, 2400000.00, "Partner"),
                        ("Europe", "Q2", 2025, 3500000.00, 2500000.00, "Partner"),
                        ("Europe", "Q3", 2025, 2900000.00, 2700000.00, "Partner"), # revenue drop & high cost
                        ("Europe", "Q4", 2025, 3800000.00, 2600000.00, "Partner"),
                        ("Asia Pacific", "Q1", 2025, 2100000.00, 1500000.00, "Online"),
                        ("Asia Pacific", "Q2", 2025, 2300000.00, 1600000.00, "Online"),
                        ("Asia Pacific", "Q3", 2025, 2500000.00, 1750000.00, "Online"),
                        ("Asia Pacific", "Q4", 2025, 3000000.00, 1900000.00, "Online"),
                        ("Latin America", "Q1", 2025, 1200000.00, 950000.00, "Direct"),
                        ("Latin America", "Q2", 2025, 1300000.00, 1000000.00, "Direct"),
                        ("Latin America", "Q3", 2025, 1100000.00, 1050000.00, "Direct"),
                        ("Latin America", "Q4", 2025, 1500000.00, 1100000.00, "Direct")
                    ]
                    
                    insert_query = """
                    INSERT INTO corporate_sales (region, quarter, year, revenue, operational_cost, sales_channel)
                    VALUES (:region, :quarter, :year, :revenue, :operational_cost, :sales_channel)
                    """
                    for rec in records:
                        conn.execute(text(insert_query), {
                            "region": rec[0],
                            "quarter": rec[1],
                            "year": rec[2],
                            "revenue": rec[3],
                            "operational_cost": rec[4],
                            "sales_channel": rec[5]
                        })
                    db_logger.info(f"Seeded {len(records)} sales records successfully.")
                else:
                    db_logger.info(f"Database already contains {count} records. Seeding skipped.")
        except Exception as e:
            db_logger.error(f"Error seeding database: {e}")

    def execute_query(self, sql_str: str) -> List[Dict[str, Any]]:
        """
        Execute raw SQL statement and return results as list of dicts.
        """
        db_logger.info(f"Executing SQL query: {sql_str}")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_str))
                # If query returns rows (like SELECT)
                if result.returns_rows:
                    keys = result.keys()
                    return [dict(zip(keys, row)) for row in result.fetchall()]
                return [{"rows_affected": result.rowcount}]
        except Exception as e:
            db_logger.error(f"SQL execution error: {e}")
            raise e

    def get_schema_info(self) -> str:
        """
        Returns text representation of the schema for LLM context.
        """
        return """
        Table: corporate_sales
        Columns:
          - id: INTEGER (Primary Key)
          - region: VARCHAR(50) (e.g., 'North America', 'Europe', 'Asia Pacific', 'Latin America')
          - quarter: VARCHAR(10) (e.g., 'Q1', 'Q2', 'Q3', 'Q4')
          - year: INTEGER (e.g., 2025)
          - revenue: DECIMAL(12,2) (Sales income generated)
          - operational_cost: DECIMAL(12,2) (Expenditures to run operations)
          - sales_channel: VARCHAR(50) (e.g., 'Direct', 'Partner', 'Online')
        """

# Global database manager
db_manager = DatabaseManager()
