import os
import json
import requests
import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any, List

# Load environment configuration
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# Setup Page Configuration
st.set_page_config(
    page_title="Enterprise Multi-Agent Analytics Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern CSS style tokens
st.markdown("""
<style>
    /* Custom background gradient */
    .reportview-container {
        background: #0F172A;
    }
    
    /* Premium Title styling */
    .main-title {
        font-family: 'Outfit', 'Inter', sans-serif;
        background: linear-gradient(135deg, #3B82F6 0%, #10B981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-family: 'Inter', sans-serif;
        color: #64748B;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Styled container cards */
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Custom scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0F172A;
    }
    ::-webkit-scrollbar-thumb {
        background: #334155;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #475569;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to check backend health
def check_backend_health() -> bool:
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def render_plotly_chart(chart_specs, key=None):
    """Render a Plotly chart from JSON specs with premium dark styling."""
    try:
        if isinstance(chart_specs, str):
            chart_dict = json.loads(chart_specs)
        else:
            chart_dict = chart_specs

        traces = []
        for trace in chart_dict.get("data", []):
            trace_copy = dict(trace)
            chart_type = trace_copy.pop("type", "bar")
            if chart_type == "bar":
                traces.append(go.Bar(**trace_copy))
            elif chart_type == "pie":
                traces.append(go.Pie(**trace_copy))
            elif chart_type == "scatter":
                traces.append(go.Scatter(**trace_copy))
            elif chart_type == "line":
                trace_copy["mode"] = trace_copy.get("mode", "lines+markers")
                traces.append(go.Scatter(**trace_copy))
            else:
                traces.append(go.Bar(**trace_copy))

        fig = go.Figure(data=traces, layout=go.Layout(**chart_dict.get("layout", {})))

        # Apply styling overrides for premium look and high visibility on dark background
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F8FAFC", family="Inter, sans-serif"),
            title=dict(font=dict(color="#F8FAFC", size=18)),
            legend=dict(font=dict(color="#94A3B8")),
            margin=dict(t=50, b=50, l=50, r=50)
        )
        fig.update_xaxes(
            gridcolor="#334155",
            linecolor="#334155",
            tickfont=dict(color="#94A3B8"),
            title_font=dict(color="#F8FAFC")
        )
        fig.update_yaxes(
            gridcolor="#334155",
            linecolor="#334155",
            tickfont=dict(color="#94A3B8"),
            title_font=dict(color="#F8FAFC")
        )
        st.plotly_chart(fig, use_container_width=True, key=key)
        return True
    except Exception as e:
        st.error(f"Could not render chart: {e}")
        return False


# Initialize Session States
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())
if "uploaded_file_path" not in st.session_state:
    st.session_state.uploaded_file_path = None
if "dataset_summary" not in st.session_state:
    st.session_state.dataset_summary = None
if "dataset_metadata" not in st.session_state:
    st.session_state.dataset_metadata = None
if "original_filename" not in st.session_state:
    st.session_state.original_filename = None
if "active_run_id" not in st.session_state:
    st.session_state.active_run_id = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Title Section
st.markdown('<div class="main-title">Enterprise Analytics Multi-Agent Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time business dataset analysis, relational data querying, and visualization using LangGraph & Gemini.</div>', unsafe_allow_html=True)

# Sidebar configurations
st.sidebar.markdown("### ⚙️ System Settings")

# Backend Health Banner
is_healthy = check_backend_health()
if is_healthy:
    st.sidebar.success("🟢 API Server Connected")
else:
    st.sidebar.error("🔴 API Server Offline\nPlease run `docker-compose up` or start `app/main.py` directly.")

# API Keys Configuration
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 Gemini API Key (Required)")
gemini_key_val = st.sidebar.text_input(
    "Google Gemini API Key",
    type="password",
    value=st.session_state.get("gemini_api_key", ""),
    placeholder="AIzaSy...",
    help="Your Gemini API key is required to use this assistant. Get one at https://aistudio.google.com/apikey"
)
if gemini_key_val:
    st.session_state.gemini_api_key = gemini_key_val
else:
    st.session_state.gemini_api_key = None

# API Key Status Indicator
has_api_key = bool(st.session_state.get("gemini_api_key"))
if has_api_key:
    st.sidebar.success("🟢 Gemini API Key Entered")
else:
    st.sidebar.warning("⚠️ No API Key — Enter your Gemini key above to start analyzing data.")

# Session Thread Manager
st.sidebar.markdown("---")
st.sidebar.markdown("### 💬 Conversational Session")
st.sidebar.text(f"Session ID: {st.session_state.session_id[:8]}...")
if st.sidebar.button("Clear Chat History", use_container_width=True):
    if is_healthy:
        try:
            requests.post(f"{BACKEND_URL}/api/history/{st.session_state.session_id}/clear")
        except Exception:
            pass
    st.session_state.chat_messages = []
    st.session_state.active_run_id = None
    st.success("Session chat history cleared!")
    st.rerun()

# Dataset File Upload Section
st.sidebar.markdown("---")
st.sidebar.markdown("### 📂 Upload Dataset")
uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    if st.session_state.original_filename != uploaded_file.name:
        with st.spinner("Processing file schema..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                response = requests.post(f"{BACKEND_URL}/api/upload", files=files)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.uploaded_file_path = data.get("saved_path")
                    st.session_state.dataset_summary = data.get("dataframe_summary")
                    st.session_state.dataset_metadata = data.get("metadata")
                    st.session_state.original_filename = uploaded_file.name
                    st.sidebar.success(f"Successfully loaded: {uploaded_file.name}")
                else:
                    st.sidebar.error("Failed to parse uploaded dataset.")
            except Exception as e:
                st.sidebar.error(f"Error connecting to backend upload API: {e}")

if st.session_state.uploaded_file_path:
    st.sidebar.info(f"Active File: `{st.session_state.original_filename}`")
    with st.sidebar.expander("📊 File Schema Preview"):
        st.text(st.session_state.dataset_summary)


# Main Application Layout: Split into Tabs
tab_chat, tab_dashboard, tab_tracing = st.tabs([
    "💬 Business Analyst Chat", 
    "📊 KPI Dashboard & Visualizations", 
    "🔍 Enterprise Execution Tracer"
])

# -----------------
# TAB 1: Chat interface
# -----------------
with tab_chat:
    st.markdown("### 💬 Ask Business Analytics Questions")
    
    # Show setup requirements if needed
    if not has_api_key:
        st.warning("🔑 **Please enter your Gemini API Key** in the sidebar to start asking questions.")
    elif not st.session_state.uploaded_file_path:
        st.info("📂 **Upload a dataset** in the sidebar to begin analysis, or ask questions about the corporate database.")
    
    # Dynamic suggested prompts based on uploaded schema
    uploaded_path = st.session_state.uploaded_file_path
    
    p1_label = "Compare region-wise revenue and costs"
    p1_query = "Compare region-wise performance and show revenue against operational costs."
    
    p2_label = "Find Q3 sales revenue drops"
    p2_query = "Why did sales revenue drop in Q3? Generate insights and recommendations."
    
    p3_label = "Generate executive report"
    p3_query = "Generate an executive report for corporate sales."
    
    metadata = st.session_state.get("dataset_metadata")
    if metadata:
        try:
            cols = metadata.get("columns", [])
            dish_col = next((c for c in cols if "dish" in c.lower() or "name" in c.lower() or "food" in c.lower() or "item" in c.lower()), None)
            protein_col = next((c for c in cols if "protein" in c.lower()), None)
            calories_col = next((c for c in cols if "calorie" in c.lower()), None)
            revenue_col = next((c for c in cols if "revenue" in c.lower() or "sales" in c.lower()), None)
            cost_col = next((c for c in cols if "cost" in c.lower() or "expense" in c.lower()), None)
            
            if dish_col and protein_col:
                p1_label = f"Rank by {protein_col}"
                p1_query = f"Show me top 5 {dish_col} according to {protein_col}"
            elif revenue_col:
                p1_label = "Regional Performance"
                p1_query = "Compare region-wise performance and show revenue against operational costs."
                
            if dish_col and calories_col:
                p2_label = f"Highest {calories_col} items"
                p2_query = f"Show me the top 5 {dish_col} with the highest {calories_col}"
            elif revenue_col:
                p2_label = "Sales Revenue Drop"
                p2_query = "Why did sales revenue drop in Q3? Generate insights and recommendations."
                
            if len(cols) > 2:
                p3_label = "Dataset general summary"
                p3_query = "Describe the dataset and generate a brief executive summary."
        except Exception:
            pass
            
    st.markdown("**Suggested Quick Prompts:**")
    col_p1, col_p2, col_p3 = st.columns(3)
    p_choice = None
    if col_p1.button(p1_label, use_container_width=True, disabled=not has_api_key):
        p_choice = p1_query
    if col_p2.button(p2_label, use_container_width=True, disabled=not has_api_key):
        p_choice = p2_query
    if col_p3.button(p3_label, use_container_width=True, disabled=not has_api_key):
        p_choice = p3_query

    # Load existing history if empty
    if not st.session_state.chat_messages and is_healthy:
        try:
            hist_res = requests.get(f"{BACKEND_URL}/api/history/{st.session_state.session_id}")
            if hist_res.status_code == 200:
                st.session_state.chat_messages = hist_res.json()
        except Exception:
            pass

    # Display conversational thread
    for idx, msg in enumerate(st.session_state.chat_messages):
        role = msg.get("role")
        content = msg.get("content")
        with st.chat_message(role):
            st.markdown(content)
            # Check for metadata
            meta = msg.get("metadata")
            if meta:
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        pass
                
                # Show SQL details
                if meta.get("sql_query"):
                    st.code(meta["sql_query"], language="sql")
                # Show downloadable report button
                if meta.get("report_path"):
                    report_path = meta["report_path"]
                    filename = os.path.basename(report_path)
                    try:
                        dl_url = f"{BACKEND_URL}/api/download_report?path={report_path}"
                        st.markdown(f"[📥 Download Official Report: `{filename}`]({dl_url})")
                    except Exception:
                        pass
                # Render inline chart if present in this message
                if meta.get("chart_specs"):
                    render_plotly_chart(meta["chart_specs"], key=f"chat_chart_{idx}")



# -----------------
# TAB 2: KPI Metrics and Plotly Charts
# -----------------
with tab_dashboard:
    st.markdown("### 📊 Executive Metrics & Visualizations")
    
    # Load dataset metrics dynamically if file is uploaded
    m_cards = []
    metadata = st.session_state.get("dataset_metadata")
    
    if metadata:
        m_cards = [
            {"label": "Total Records", "value": f"{metadata.get('total_rows', 0):,}"},
            {"label": "Total Columns", "value": f"{metadata.get('total_cols', 0)}"},
            {"label": metadata.get("avg_metric_label", "Avg Value"), "value": metadata.get("avg_metric_val", "N/A")},
            {"label": metadata.get("sec_metric_label", "Secondary Value"), "value": metadata.get("sec_metric_val", "N/A")}
        ]
    else:
        m_cards = [
            {"label": "Total Records", "value": "—"},
            {"label": "Total Columns", "value": "—"},
            {"label": "Avg Value", "value": "—"},
            {"label": "Status", "value": "Upload a dataset"}
        ]
        
    # Render KPI metrics row
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    cols = [col_m1, col_m2, col_m3, col_m4]
    
    for col, card in zip(cols, m_cards):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{card['label']}</div>
                <div class="metric-value">{card['value']}</div>
            </div>
            """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Retrieve last generated chart specs from chat history
    chart_specs = None
    for msg in reversed(st.session_state.chat_messages):
        meta = msg.get("metadata")
        if meta and meta.get("chart_specs"):
            chart_specs = meta["chart_specs"]
            break
            
    if chart_specs:
        st.markdown("#### 📈 Interactive Analytics Chart")
        render_plotly_chart(chart_specs, key="dashboard_chart")
    else:
        st.info("No visualizations generated yet. Upload a dataset and ask a graphing question like 'Plot top 10 protein-rich foods'.")

# -----------------
# TAB 3: Execution Tracing Panel
# -----------------
with tab_tracing:
    st.markdown("### 🔍 Live Agent Workflow Trace Logs")
    
    if st.session_state.active_run_id and is_healthy:
        try:
            # Query tracer endpoint
            trace_url = f"{BACKEND_URL}/api/traces/{st.session_state.active_run_id}"
            res = requests.get(trace_url)
            
            if res.status_code == 200:
                trace_data = res.json()
                
                # Render metadata
                col_t1, col_t2, col_t3 = st.columns(3)
                col_t1.metric("Current Run ID", trace_data.get("run_id")[:8] + "...")
                col_t2.metric("Workflow Duration", f"{trace_data.get('duration', 'N/A')} seconds")
                col_t3.metric("Overall Status", trace_data.get("status", "RUNNING"))
                
                st.markdown("#### Node Step Execution Sequence:")
                
                # Loop through steps
                for step in trace_data.get("steps", []):
                    step_index = step.get("step_index")
                    agent_name = step.get("agent_name").upper()
                    duration = step.get("duration", "N/A")
                    status = step.get("status")
                    
                    # Style badges
                    status_color = "green" if status == "SUCCESS" else "orange" if status == "RUNNING" else "red"
                    
                    with st.expander(f"Step {step_index}: Agent `{agent_name}` — Duration: {duration}s | Status: :{status_color}[{status}]"):
                        col_l, col_r = st.columns(2)
                        with col_l:
                            st.markdown("**Input Metadata Context:**")
                            st.text_area(f"Input {step_index}", step.get("input"), height=100, disabled=True)
                        with col_r:
                            st.markdown("**Output Response:**")
                            st.text_area(f"Output {step_index}", step.get("output"), height=100, disabled=True)
            else:
                st.error("Trace records not found for this execution.")
        except Exception as e:
            st.error(f"Error loading trace execution: {e}")
    else:
        st.info("Trigger a business question query to see real-time LangGraph multi-agent execution traces.")

# -----------------
# Root-Level Chat Input (Pinned to the bottom of the screen across all tabs)
# -----------------
chat_prompt = st.chat_input(
    "Enter your analytics question..." if has_api_key else "⚠️ Enter a Gemini API Key in the sidebar first...",
    disabled=not has_api_key
)
if p_choice:
    chat_prompt = p_choice

if chat_prompt:
    # Add user message locally
    st.session_state.chat_messages.append({"role": "user", "content": chat_prompt})
    
    # Render user query and assistant response inside the Tab Chat container
    with tab_chat:
        with st.chat_message("user"):
            st.markdown(chat_prompt)
            
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("🧠 *Supervisor Agent routing request to Gemini...*")
            
            if not is_healthy:
                response_placeholder.error("Cannot query. FastAPI Server is offline.")
            else:
                try:
                    # Trigger query workflow API
                    payload = {
                        "query": chat_prompt,
                        "session_id": st.session_state.session_id,
                        "file_path": st.session_state.uploaded_file_path,
                        "gemini_api_key": st.session_state.get("gemini_api_key") or None
                    }
                    res = requests.post(f"{BACKEND_URL}/api/query", json=payload, timeout=180)
                    
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.active_run_id = data.get("run_id")
                        response_placeholder.markdown(data.get("response", ""))
                        
                        # Store assistant message metadata
                        msg_metadata = {
                            "run_id": data.get("run_id"),
                            "chart_specs": data.get("chart_specs"),
                            "sql_query": data.get("sql_query"),
                            "report_path": data.get("report_path"),
                            "agent_history": data.get("agent_history"),
                            "llm_mode": data.get("llm_mode")
                        }
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": data.get("response", ""),
                            "metadata": msg_metadata
                        })
                        
                        # Show SQL if generated
                        if data.get("sql_query"):
                            st.code(data["sql_query"], language="sql")
                            
                        if data.get("report_path"):
                            report_path = data["report_path"]
                            dl_url = f"{BACKEND_URL}/api/download_report?path={report_path}"
                            st.markdown(f"[📥 Download Official Briefing Report]({dl_url})")

                        # Render chart inline in chat if generated
                        if data.get("chart_specs"):
                            st.info("📊 **Chart generated!** Also available in the **KPI Dashboard** tab.")
                            render_plotly_chart(data["chart_specs"], key="new_msg_chart")
                            
                        st.rerun()
                    else:
                        response_placeholder.error(f"Error running agent pipeline: {res.text}")
                except requests.exceptions.Timeout:
                    response_placeholder.error("⏱️ Request timed out. The LLM may be overloaded — please try again.")
                except Exception as e:
                    response_placeholder.error(f"Failed to communicate with API server: {e}")
