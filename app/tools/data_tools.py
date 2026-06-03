import os
import pandas as pd
from typing import Dict, Any

def get_dataframe_summary(file_path: str) -> str:
    """
    Parses a CSV or Excel file and returns a structured string summary
    of columns, data types, description, and samples.
    """
    try:
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
            
        columns = df.columns.tolist()
        dtypes = df.dtypes.astype(str).tolist()
        null_counts = df.isnull().sum().tolist()
        
        summary = []
        filename = os.path.basename(file_path)
        summary.append(f"Dataset File: {filename}")
        summary.append(f"Total Rows: {len(df)} | Total Columns: {len(columns)}")
        summary.append("\n--- Column Schema ---")
        
        for col, dtype, nulls in zip(columns, dtypes, null_counts):
            summary.append(f"- Column: `{col}` | Type: `{dtype}` | Missing Values: `{nulls}`")
            
        summary.append("\n--- Sample Records (First 3 Rows) ---")
        sample_rows = df.head(3).to_dict(orient='records')
        for i, row in enumerate(sample_rows):
            row_str = ", ".join([f"`{k}`: {v}" for k, v in row.items()])
            summary.append(f"{i+1}. {row_str}")
            
        summary.append("\n--- Summary Statistics ---")
        # Numerical summary
        numerical_summary = df.describe(include='all').transpose()
        # Drop columns not relevant to general counts to keep output brief
        if 'unique' in numerical_summary.columns:
            stats_cols = ['count', 'unique', 'mean', 'min', 'max']
        else:
            stats_cols = ['count', 'mean', 'std', 'min', 'max']
            
        # Standardize matching
        valid_cols = [c for c in stats_cols if c in numerical_summary.columns]
        try:
            summary.append(numerical_summary[valid_cols].head(10).to_markdown())
        except ImportError:
            summary.append(numerical_summary[valid_cols].head(10).to_string())
        
        return "\n".join(summary)
        
    except Exception as e:
        return f"Error indexing dataset summary: {str(e)}"


def get_dataframe_metadata(file_path: str) -> Dict[str, Any]:
    """
    Reads the dataset and returns a dictionary of column names,
    types, row counts, and summary metrics to send to the frontend.
    """
    try:
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
            
        columns = df.columns.tolist()
        
        # Calculate dynamic metrics for display
        total_rows = len(df)
        total_cols = len(columns)
        
        # Find numeric columns for averages
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        avg_metric_label = "Avg Value"
        avg_metric_val = "N/A"
        sec_metric_label = "Top Category"
        sec_metric_val = "N/A"
        
        # Determine average metrics
        protein_col = next((c for c in columns if "protein" in c.lower()), None)
        calories_col = next((c for c in columns if "calorie" in c.lower()), None)
        revenue_col = next((c for c in columns if "revenue" in c.lower() or "sales" in c.lower()), None)
        cost_col = next((c for c in columns if "cost" in c.lower() or "expense" in c.lower()), None)
        
        if protein_col:
            avg_metric_val = f"{df[protein_col].mean():.1f}g"
            avg_metric_label = f"Avg {protein_col}"
        elif revenue_col:
            try:
                avg_metric_val = f"${df[revenue_col].sum()/1e6:.2f}M"
            except Exception:
                avg_metric_val = f"${df[revenue_col].mean():,.2f}"
            avg_metric_label = f"Total {revenue_col}"
            
        if calories_col:
            sec_metric_val = f"{df[calories_col].mean():.0f} kcal"
            sec_metric_label = f"Avg {calories_col}"
        elif cost_col:
            try:
                sec_metric_val = f"${df[cost_col].sum()/1e6:.2f}M"
            except Exception:
                sec_metric_val = f"${df[cost_col].mean():,.2f}"
            sec_metric_label = f"Total {cost_col}"
        elif len(categorical_cols) > 0:
            top_val = df[categorical_cols[0]].mode().iloc[0] if not df[categorical_cols[0]].mode().empty else "N/A"
            sec_metric_val = str(top_val)[:18]
            sec_metric_label = f"Top {categorical_cols[0]}"
            
        return {
            "total_rows": total_rows,
            "total_cols": total_cols,
            "avg_metric_label": avg_metric_label,
            "avg_metric_val": avg_metric_val,
            "sec_metric_label": sec_metric_label,
            "sec_metric_val": sec_metric_val,
            "columns": columns,
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols
        }
    except Exception as e:
        return {
            "error": str(e),
            "columns": [],
            "numeric_columns": [],
            "categorical_columns": []
        }

