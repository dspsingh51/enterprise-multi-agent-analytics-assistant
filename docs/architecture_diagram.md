# Enterprise Multi-Agent Analytics Assistant: Architecture Documentation

This document describes the architectural specifications, data flows, and routing workflows of the platform.

---

## 1. System Topology & Deployment Structure

The platform is designed to run in a modular, containerized environment, with microservices communicating over HTTP APIs. If PostgreSQL or Redis are not detected, the backend dynamically falls back to SQLite and local thread-safe In-Memory dictionary blocks.

```mermaid
graph TD
    Client[Browser Streamlit UI] -- HTTP / WebSockets --> Gateway[FastAPI Backend Server]
    
    subgraph Core_Orchestration ["Core Orchestration"]
        Gateway --> Router[LangGraph Agent Graph]
        Router --> AgentBase[Agent Core & LLM Abstraction]
    end
    
    subgraph Data_Memory_Services ["Data & Memory Services"]
        Gateway -- Checkpoints & Session Cache --> RedisCheck[{Redis Cache / Local In-Memory Fallback}]
        Gateway -- Analytical Tables --> PGDB[(PostgreSQL Warehouse / SQLite Fallback)]
    end
    
    subgraph LLM_Services ["LLM Services"]
        AgentBase -- API Invocations --> Gemini[Google Gemini Client]
        AgentBase -- Fallback API --> OpenAI[OpenAI Compatible API]
    end
```

---

## 2. Multi-Agent Workflow Sequence

The LangGraph workflow implements a stateful routing model. The **Supervisor Agent** acts as the central orchestrator, analyzing the user request and intermediate results, then delegating work to specialist agents until a final summary report is compiled.

```mermaid
sequenceDiagram
    autonumber
    actor User as Enterprise Client
    participant Sup as Supervisor Agent
    participant Analyst as Data Analyst Agent
    participant SQL as SQL Assistant Agent
    participant Viz as Visualization Agent
    participant Gen as Insight Generator Agent
    participant Rep as Reporter Agent

    User->>Sup: NL Query e.g. "Why did Q3 revenue drop?"
    activate Sup
    Note over Sup: Evaluates state. Selects Insight Generator
    Sup-->>Gen: Run Insight Extraction
    deactivate Sup
    activate Gen
    Note over Gen: Analyzes Q3 data tables & aggregates
    Gen->>Sup: Return Qualitative Narrative Summary
    deactivate Gen
    activate Sup
    Note over Sup: Evaluates state. Selects Reporter Agent
    Sup-->>Rep: Compile Executive PDF/Markdown Report
    deactivate Sup
    activate Rep
    Note over Rep: Write output reports/report_uuid.md to disk
    Rep->>Sup: Return saved file path
    deactivate Rep
    activate Sup
    Note over Sup: Evaluates state. Ready to terminate
    Sup->>User: Deliver response (insights + charts + report link)
    deactivate Sup
```

---

## 3. Data Flow & Sandboxed Code Execution

The **Data Analyst Agent** evaluates local datasets (CSV/Excel) by safely executing generated Pandas statements:

```mermaid
flowchart TD
    Ingest[User Uploads CSV] --> Main[FastAPI Upload API]
    Main --> Index[Index Schema & Sample Rows]
    Index --> State[Save Summary in LangGraph State]
    
    Query[User Asks Question] --> Supervisor[Supervisor Agent]
    Supervisor --> Analyst[Data Analyst Agent]
    
    Analyst --> LLM[Ask LLM for Python Snippet]
    LLM --> Exec[Run exec in controlled Sandbox namespace]
    Exec --> Cache[Capture stdout string stream]
    Cache --> Result[Store markdown result in query_result state]
    Result --> Return[Supervisor decides next step]
```
