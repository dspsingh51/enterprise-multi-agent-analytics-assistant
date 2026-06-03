import os
import sys

# Ensure the root of the project is in the python search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query as FastAPIQuery
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import modules
from app.config import settings
from app.workflows.analytics import analytics_graph
from app.tools.data_tools import get_dataframe_summary, get_dataframe_metadata
from app.memory.redis_memory import memory_manager
from app.observability.tracer import tracer
from app.observability.logger import logger
from app.agents.base import NoAPIKeyError, get_llm

app = FastAPI(
    title="Enterprise Multi-Agent Analytics Assistant API",
    description="Backend API orchestrating LangGraph multi-agent team workflows.",
    version="1.0.0"
)

# Enable CORS for Streamlit and other frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class QueryRequest(BaseModel):
    query: str
    session_id: str
    file_path: Optional[str] = None
    gemini_api_key: Optional[str] = None

class ClearHistoryResponse(BaseModel):
    session_id: str
    status: str

# Endpoints
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL
    }

@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Ingest business dataset files (CSV/Excel) and extract schema summaries.
    """
    logger.info(f"Ingesting file: {file.filename}")
    try:
        # Create upload path
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        dest_filepath = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Save file to disk
        with open(dest_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File saved to: {dest_filepath}")
        
        # Index schema columns, types, nulls
        summary_text = get_dataframe_summary(dest_filepath)
        metadata = get_dataframe_metadata(dest_filepath)
        
        return {
            "original_name": file.filename,
            "saved_path": dest_filepath,
            "dataframe_summary": summary_text,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Failed to process uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"File ingestion failed: {str(e)}")

@app.post("/api/query")
async def execute_analytics(request: QueryRequest):
    """
    Orchestrate multi-agent LangGraph workflow execution for natural language queries.
    """
    run_id = str(uuid.uuid4())
    logger.info(f"Triggered workflow run {run_id} for session {request.session_id}")
    
    # ── Early API key validation ─────────────────────────────────────
    # Fail fast before wasting compute on the graph if no key is present.
    try:
        get_llm(request.gemini_api_key)
    except NoAPIKeyError as e:
        return {
            "run_id": run_id,
            "response": f"⚠️ **API Key Required**\n\n{str(e)}\n\nPlease enter a valid Google Gemini API key in the **sidebar** to use this assistant.",
            "chart_specs": None,
            "sql_query": None,
            "report_path": None,
            "agent_history": [],
            "errors": [str(e)],
            "llm_mode": "none"
        }

    # Retrieve file summary if path provided
    summary = None
    if request.file_path and os.path.exists(request.file_path):
        summary = get_dataframe_summary(request.file_path)

    # Start Tracing
    dataset_name = os.path.basename(request.file_path) if request.file_path else "No dataset"
    tracer.start_run(run_id, request.query, dataset_name=dataset_name)

    # Add User Message to memory
    memory_manager.add_chat_message(request.session_id, "user", request.query)

    # Load previous state for structural context ONLY (file path, schema)
    prev_state = memory_manager.get_val(f"state:{request.session_id}") or {}

    # Construct Initial State
    # IMPORTANT: Output fields (query_result, chart_specs, insights, etc.) are
    # reset to None on every new query to prevent stale data from prior queries
    # from polluting the current execution and confusing the supervisor.
    initial_state = {
        "run_id": run_id,
        "session_id": request.session_id,
        "gemini_api_key": request.gemini_api_key,
        "messages": memory_manager.get_chat_history(request.session_id),
        "current_query": request.query,
        "selected_agent": "supervisor",
        "agent_history": [],
        # Structural context carries over across queries:
        "data_context": request.file_path or prev_state.get("data_context"),
        "dataframe_summary": summary or prev_state.get("dataframe_summary"),
        # Output fields are RESET for each new query:
        "sql_query": None,
        "query_result": None,
        "chart_specs": None,
        "insights": None,
        "report_path": None,
        "errors": []
    }
    
    try:
        # Execute compiled LangGraph workflow state machine
        logger.info("Invoking LangGraph State Machine...")
        final_state = analytics_graph.invoke(initial_state)
        
        # Extract consolidated text response to append to conversation
        assistant_resp = ""
        if final_state.get("insights"):
            assistant_resp += final_state["insights"] + "\n\n"
        elif final_state.get("query_result"):
            assistant_resp += f"### Query Results:\n{final_state['query_result']}\n\n"
        else:
            assistant_resp += "Analysis completed but no quantitative insights were generated. Please refine your query."
            
        if final_state.get("sql_query"):
            assistant_resp += f"*(Executed Database SQL query: `{final_state['sql_query']}`)*\n\n"
            
        if final_state.get("report_path"):
            assistant_resp += f"*(Generated detailed report report under: `{os.path.basename(final_state['report_path'])}`)*"
            
        # Write response to persistent history
        metadata = {
            "run_id": run_id,
            "chart_specs": final_state.get("chart_specs"),
            "sql_query": final_state.get("sql_query"),
            "report_path": final_state.get("report_path"),
            "agent_history": final_state.get("agent_history")
        }
        memory_manager.add_chat_message(request.session_id, "assistant", assistant_resp.strip(), additional_data=metadata)
        
        # Save final state for follow-up conversational queries
        memory_manager.set_val(f"state:{request.session_id}", {
            "query_result": final_state.get("query_result"),
            "sql_query": final_state.get("sql_query"),
            "chart_specs": final_state.get("chart_specs"),
            "insights": final_state.get("insights"),
            "report_path": final_state.get("report_path"),
            "data_context": final_state.get("data_context"),
            "dataframe_summary": final_state.get("dataframe_summary")
        })
        
        # Complete Trace
        tracer.complete_run(run_id, status="COMPLETED")
        
        # Return state response
        return {
            "run_id": run_id,
            "response": assistant_resp.strip(),
            "chart_specs": final_state.get("chart_specs"),
            "sql_query": final_state.get("sql_query"),
            "report_path": final_state.get("report_path"),
            "agent_history": final_state.get("agent_history"),
            "errors": final_state.get("errors", []),
            "llm_mode": settings.LLM_PROVIDER
        }
        
    except NoAPIKeyError as e:
        logger.error(f"API key error during workflow: {e}")
        tracer.complete_run(run_id, status="FAILED")
        return {
            "run_id": run_id,
            "response": f"⚠️ **API Key Error**\n\n{str(e)}",
            "chart_specs": None,
            "sql_query": None,
            "report_path": None,
            "agent_history": [],
            "errors": [str(e)],
            "llm_mode": "none"
        }
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        tracer.complete_run(run_id, status="FAILED")
        raise HTTPException(status_code=500, detail=f"Multi-agent orchestrator error: {str(e)}")

@app.get("/api/traces/{run_id}")
async def get_execution_trace(run_id: str):
    """
    Retrieve execution step-by-step tracing for a specific workflow execution run.
    """
    trace_data = tracer.get_trace(run_id)
    if not trace_data:
        raise HTTPException(status_code=404, detail="Trace run ID not found.")
    return trace_data

@app.get("/api/traces")
async def list_runs():
    """
    List all recorded workflow execution runs.
    """
    return tracer.list_runs()

@app.get("/api/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Load persistent conversation thread history messages.
    """
    return memory_manager.get_chat_history(session_id)

@app.post("/api/history/{session_id}/clear")
async def clear_session_history(session_id: str):
    """
    Clear conversation thread history messages.
    """
    memory_manager.clear_chat_history(session_id)
    return {"session_id": session_id, "status": "cleared"}

@app.get("/api/download_report")
async def download_analytical_report(path: str = FastAPIQuery(..., description="Absolute path of the report file")):
    """
    Secure download endpoint for markdown summaries.
    """
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report file not found.")
        
    filename = os.path.basename(path)
    return FileResponse(
        path=path,
        media_type="text/markdown",
        filename=filename
    )

if __name__ == "__main__":
    import uvicorn
    # Start the local development server
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

