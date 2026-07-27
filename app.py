from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import asyncio
import uvicorn
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_agent5 import AIAgent
import uuid
import logging


## FRONTEND
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

# Langchain context tracer and Langsmith SDK client
from langchain_core.tracers.context import collect_runs
from langsmith import Client, get_current_run_tree

# Logging for monitoring the server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Telemetry-Server")


load_dotenv()

app = FastAPI(
    title="NL2SQL Standalone Debugger",
    description="Isolated ReAct Agent runtime featuring custom AST validation and programmatic LangSmith trace tracking.",
    version="2.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace "*" with your specific Render static frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # This explicitly allows POST, OPTIONS, GET, etc.
    allow_headers=["*"],
)

# Langsmith SDK client
try:
    ls_client = Client()
    logger.info("LangSmith SDK client succesfully initialized.")
except Exception as e:
    ls_client = None
    logger.warning(f"LangSmith credentials unpopulated or invalid. SDK operations will use fallback telemetry: {str(e)}") 

# Mount static and UI files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_root_interface():
    """Serves the unified, programmatic tracing console directly."""
    return FileResponse("static/telemetry.html")

# Request Schema for the standalone execution target
class AgentExecutionRequest(BaseModel):
    message: str = Field(..., description="Natural language question or database mutation command.")
    working_dir: str = Field(".", description="The relative excecution directory or file-system operations.")
    
# Cached Agent instance helper
_agent_instance = None    
# Global instance of the AIAgent to ensure consistent LangSmith trace context across requests - NOT USING   
def get_standalone_agent(working_dir: str = "."):
    global _agent_instance
    resolved_path = os.path.abspath(working_dir)
    if _agent_instance is None or _agent_instance.working_dir != resolved_path:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is unpopulated.")
        logger.info(f"Instantiating AIAgent instance at: {resolved_path}") 
        _agent_instance = AIAgent(api_key=api_key, working_dir=resolved_path)
    return _agent_instance


@app.post("/agent")
async def execute_agent(req: AgentExecutionRequest):
    """Executes the ReAct agent within a run-collection block,
    capturing the exact LangSmith execution ID to route telemetry down the line
    """
    
    try:
        #agent = get_standalone_agent(req.working_dir)
        agent = AIAgent(
            api_key=os.getenv("GROQ_API_KEY"), 
            working_dir=req.working_dir
        )
        
        run_id = None
        result = None

        # Primary attempt: Use collect_runs (most reliable for root trace)
        with collect_runs() as run_collector:
            # Pass the run_collector.cb explicitly into the chat method via the thread args
            result = await asyncio.to_thread(
                agent.chat, 
                req.message, 
                run_collector,
                
                )
            
            if run_collector.traced_runs:
                run_id = str(run_collector.traced_runs[0].trace_id)
                logger.info(f"✅ Trace captured via collect_runs: {run_id}")
            else:
                logger.warning("collect_runs did not capture any traces")

        # Fallback: Try context
        if not run_id:
            try:
                current_run = get_current_run_tree()
                if current_run:
                    run_id = str(current_run.id)
                    logger.info(f"✅ Trace captured via get_current_run_tree: {run_id}")
            except Exception as e:
                logger.warning(f"get_current_run_tree failed: {e}")

        if not run_id:
            logger.error("Failed to capture any trace ID!")           
     
        
        # Format polymorphic outputs
        if isinstance(result, dict) and result.get("type") == "db_result":
            res = result.get("result")
            return {
                "type": "db_result",
                "run_id": run_id,
                "sql": getattr(res, "sql", "Unknown SQL Query"),
                "row_count": getattr(res, "row_count", 0),
                "error": getattr(res, "error", None),
                "columns": getattr(res, "columns", []),
                "rows_preview": getattr(res, "rows", [])[:10] if hasattr(res, "rows") else [],
                "file_path": getattr(res, "file_path", None)
            }
            
        elif isinstance(result, dict) and result.get("type") == "visualization":
            # Pass visualization results through cleanly
            return {
                "type": "visualization",
                "run_id": run_id,
                "result": result.get("result")
            }
            
        else:
            # Catch plain string fallbacks or text responses
            content = result.get("content", str(result)) if isinstance(result, dict) else str(result)
            return {
                "type": "text",
                "run_id": run_id,
                "content": content
            }
            
    except Exception as e:
        logger.error(f"Execution Error within agent loop: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    

@app.get("/agent/trace/{run_id}")
async def get_agent_trace(run_id: str):
    """Improved trace fetching with better retry logic."""
    if not ls_client:
        return {"run_id": run_id, "status": "unavailable", "steps": [], 
                "message": "LangSmith client not configured"}
        
    # FIX 1: Explicitly pass the project name. list_runs defaults to "default" without it.
    project_name = os.getenv("LANGCHAIN_PROJECT", "default")

    # for attempt in range(20):  # Up to ~50 seconds
    try:
        run = ls_client.read_run(run_id)
        child_runs = list(ls_client.list_runs(
            trace_id=run_id,
            project_name=project_name              
            ))
        print(f"Found {len(child_runs)} runs")
        
        steps = []
        for child in sorted(child_runs, key=lambda x: x.start_time or 0):
            if str(getattr(child, 'id', '')) == run_id:
                continue
                
            steps.append({
                "name": child.name,
                "type": child.run_type or "unknown",
                "status": "error" if child.error else "success",
                "latency_ms": ((child.end_time - child.start_time).total_seconds() * 1000 
                                if child.end_time and child.start_time else 0),
                "inputs": child.inputs or {},
                "outputs": child.outputs or {},
                "error": child.error
            })
            
        # FIX 2: Prevent premature "success" states.
        # If LangSmith hasn't indexed the children yet, force a "pending" status 
        # so the frontend UI knows to keep polling.
        if not getattr(run, 'end_time', None) or len(steps) == 0:
            return {
                "run_id": run_id,
                "status": "pending",
                "steps": []
            }

        print(f"Returning {len(steps)} steps to UI")
        return {
            "run_id": run_id,
            "name": getattr(run, 'name', 'Unknown'),
            "status": "error" if getattr(run, 'error', None) else "success",
            "latency_ms": ((run.end_time - run.start_time).total_seconds() * 1000 
                            if run.end_time and run.start_time else 0),
            "error": getattr(run, 'error', None),
            "steps": steps
        }
        
    except Exception as e:
        error_str = str(e).lower()
        if ("404" in error_str or "not found" in error_str):
            return {"run_id": run_id, "status": "pending", "steps": []}
        #     await asyncio.sleep(2)
        #     continue
        # else:
        #     logger.warning(f"Trace fetch attempt {attempt} failed: {e}")
        #     if attempt >= 12:
        #         break
        logger.warning(f"Trace fetch failed: {e}")
        return {"run_id": run_id, "status": "error", "steps": []}
# Fallback
# return {"run_id": run_id, "status": "pending", "steps": [], 
#         "message": "Trace still being indexed by LangSmith"}



if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
        
    
    
    
    
    

    

    
    
