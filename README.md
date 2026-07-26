<img width="1679" height="1043" alt="react_agent" src="https://github.com/user-attachments/assets/c38a97a9-a688-4dde-ad72-8b9a79f14894" />


ARCHITECTURE
"""mermaid
%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%
flowchart TD
    %% Client/Dashboard Layer
    subgraph Dashboard ["Telemetry UI Dashboard (telemetry.html)"]
        State["Alpine.js Reactive State (x-data)"]
        Console["Standard Output Logger"]
        TraceView["Deep Trace Explorer Waterfall"]
        Plotly["Plotly.js Interactive Canvas"]
    end

    %% API Layer
    subgraph API ["FastAPI Service (app.py)"]
        API_Agent["POST /agent Endpoint"]
        API_Trace["GET /agent/trace/{run_id}"]
    end

    %% Observability
    subgraph Observability ["LangSmith SDK"]
        RunCollector["collect_runs() Context"]
        TraceTree["Trace Tree Parser"]
    end

    %% Agent Core & Guardrails
    subgraph AgentSystem ["ReAct Pipeline (langchain_agent5.py)"]
        AIAgent["Primary / Fallback LLM Loop"]
        Tools["Tool Registry"]
        SQLGuardrail["sqlglot AST Guardrail"]
    end
    
    %% Data Layer
    subgraph Data ["File Storage"]
        SQLite[("SQLite Databases (.db)")]
        Parquet[("PyArrow Cache (.parquet)")]
    end

    %% Interaction Flow
    User((User)) -->|Inputs Query| State
    State -->|Triggers Fetch| API_Agent
    State -->|Polls Run ID| API_Trace
    
    API_Agent --> RunCollector
    RunCollector --> AIAgent
    
    AIAgent <--> Tools
    Tools -->|Validates SQL| SQLGuardrail
    SQLGuardrail -->|Read-only Exec| SQLite
    
    SQLite -->|Raw Rows| Tools
    Tools -->|Save Query Dataset| Parquet
    Tools -->|visualize_query| Parquet
    
    API_Trace --> TraceTree
    TraceTree -.->|Renders JSON Steps| TraceView
    Parquet -.->|Chart JSON via API| Plotly
    AIAgent -.->|Returns Content| Console

<img width="1079" height="1804" alt="Screenshot 2026-07-21 at 16 33 23" src="https://github.com/user-attachments/assets/5129f970-acd0-4927-9443-5fce10f28fd9" />

<img width="1079" height="1804" alt="Screenshot 2026-07-22 at 6 33 23" src="https://github.com/user-attachments/assets/3f2691d3-7d98-40c4-ba35-2ff617ef02bc" />


## 🚀 Run with Docker (Recommended)

### Option A – Pull the pre-built image (fastest)

```bash
docker run -d \
  --name nl2sql-agent \
  -p 8000:8000 \
  -e GROQ_API_KEY=your_groq_api_key \
  -e LANGCHAIN_API_KEY=your_langsmith_api_key \
  -e LANGCHAIN_PROJECT=nl2sql-agent \
  -e LANGCHAIN_TRACING_V2=true \
  YOUR_USERNAME/nl2sql-agent:latest


Option B - Build from source
git clone https://github.com/YOUR_GITHUB_USERNAME/ReAct_Agent.git
cd ReAct_Agent
cp .env.example .env   # then fill in your keys
docker compose up --build -d

FOR BOTH OPTIONS create a .env file with the following variables

# ===========================================
# NL2SQL Agent - Environment Variables
# ===========================================
# Copy this file to .env and fill in your real keys


# Required - Get from https://console.groq.com
GROQ_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional but recommended - Get from https://smith.langchain.com
LANGCHAIN_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
LANGCHAIN_PROJECT=nl2sql-agent
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.
