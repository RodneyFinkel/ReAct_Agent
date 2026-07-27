import os
import sqlite3
import argparse
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase
from sqlglot import parse_one, exp
from sqlglot.errors import ParseError
from langchain_core.tools import StructuredTool
from langsmith import traceable, get_current_run_tree  # ADDED: Explicit tracing decorator for Python methods
import re
from utils.prompt_loader import load_prompt
#from utils.llm_utils import get_resilient_llm
import pandas as pd
import uuid
import pyarrow as pa
import pyarrow.parquet as pq
import logging
import plotly.express as px


# Configure logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AIAgent")


load_dotenv()

# Tool Input Schemas

class ReadFileSchema(BaseModel):
    file_path: str = Field(description="The relative path to the file to read, including any folder names discovered in previous list_files calls (e.g., 'graph_core/graph.py'). Do not just use the filename if it is inside a subdirectory.")

class ListFilesSchema(BaseModel):
    path: str = Field(description="The directory path to list. Use '.' for the current working directory.")

class QueryDatabaseSchema(BaseModel):
    question: str = Field(description="A natural language question about the student database.")

class SuggestQueriesSchema(BaseModel):
    focus: str = Field(description="Optional focus: general, performance, trends")

class QueryAnyDatabaseSchema(BaseModel):
    db_filename: str = Field(description="Exact filename of the .db file in the working directory (e.g. student_grades.db)")
    question: str = Field(description="Natural language question about this database.")
    
class ListAvailableDatabasesSchema(BaseModel):
    dummy: Optional[str] = Field(
        default="trigger", 
        description="Just pass 'trigger' to execute."
    )

class DbQueryResult(BaseModel):
    sql: str
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    file_path: Optional[str] = None
    error: Optional[str] = None
    
class GetDatabaseSchemaSchema(BaseModel):
    db_filename: str = Field(description="Exact filename of the .db file in the working directory (e.g., student_grades.db)")

# NEW    
class VisualizeQuerySchema(BaseModel):
    question: str = Field(description="The original natural language question that generated the data")
    #data_file: str = Field(description="Path to the parquet file (.parquet) from the current database query. DbQueryResult file_path .")
    chart_type: str = Field(description="Chart type: bar, line, pie, scatter, histogram, or 'auto' for intelligent selection.", 
                       default="auto")
                       
                       
                       


class AIAgent:
    def __init__(self, api_key: str, working_dir: str = "."):
        
        self.primary_llm = ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            temperature=0
        )
        self.fallback_llm = ChatGroq(
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",  # or a known good fallback
            temperature=0
        )
        
        # Primary LLM with fallback capability
        self.primary_with_fallback = self.primary_llm.with_fallbacks([self.fallback_llm])
        
        self.working_dir = os.path.abspath(working_dir)
        self.db_path = os.path.join(self.working_dir, "student_grades.db")
        self.default_db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
        
        system_instruction = load_prompt("db_agent")
        self.system_prompt = [SystemMessage(content=system_instruction)]

        self._setup_tools2()
        # Bind the tools
        self.primary_with_tools = self.primary_with_fallback.bind_tools(self.tools)
        self.fallback_with_tools = self.fallback_llm.bind_tools(self.tools)
        
        print("Tool bindings done...ReAct agent 5 initialized")


    # USING raw JSON schemas directly
    def _setup_tools(self):
        self.langchain_tools = [
            {"type": "function", "function": {"name": "read_file",        "description": "Read the contents of a file.",        "parameters": ReadFileSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "list_files",       "description": "List all files in a directory.",       "parameters": ListFilesSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "query_database",   "description": "Query the default student_grades.db",  "parameters": QueryDatabaseSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "suggest_interesting_queries", "description": "Suggest 4-6 interesting questions.", "parameters": SuggestQueriesSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "query_any_database","description": "Query ANY .db file in the working directory.", "parameters": QueryAnyDatabaseSchema.model_json_schema()}},
            {"type": "function", "function": {
                "name": "list_available_databases", 
                "description": "List only the SQLite .db database files available in the working directory. "
                              "Use this first when the user asks about available databases or doesn't specify which one.",
                "parameters": ListAvailableDatabasesSchema.model_json_schema()}},
        ]
    
    # USING StructuredTool.from_function for tighter langchain coupling  
    def _setup_tools2(self):
        print("NOW USING MODERN TOOL BINDINGS WITH LANGCHAIN!!")
        """Modern and more reliable tool binding"""
   
        self.tools = [
            StructuredTool.from_function(
                func=self.read_file,
                name="read_file",
                description="Read the contents of a file. Use this tool if the user asks what a specific file is, what it does, or asks to read it.",
                args_schema=ReadFileSchema,
            ),
            StructuredTool.from_function(
                func=self.list_files,
                name="list_files",
                description="List all files and directories in the given path.",
                args_schema=ListFilesSchema,
            ),
            StructuredTool.from_function(
                func=self.list_available_databases,
                name="list_available_databases",
                description="List only the SQLite .db database files in the working directory.",
                args_schema=ListAvailableDatabasesSchema,
            ),
            StructuredTool.from_function(
                func=self.query_database,
                name="query_database",
                description="Query the default student_grades.db database using natural language.",
                args_schema=QueryDatabaseSchema,
            ),
            StructuredTool.from_function(
                func=self.query_any_database,
                name="query_any_database",
                description="Query any .db file in the working directory using its exact filename.",
                args_schema=QueryAnyDatabaseSchema,
            ),
            StructuredTool.from_function(
                func=self.suggest_interesting_queries,
                name="suggest_interesting_queries",
                description="Suggest interesting natural language questions about the database.",
                args_schema=SuggestQueriesSchema,
            ),
            StructuredTool.from_function(
                func=self.get_database_schema,
                name="get_database_schema",
                description="Retrieve schema information, tables, and column DDL structures for a specific database.",
                args_schema=GetDatabaseSchemaSchema,
            ),
            StructuredTool.from_function(
                func=self.visualize_query,
                name="visualize_query",
                description=("Generate an interactive Plotly visualization from the most recent database query result."
                    "Call this after a successful query_database or query_any_database call."
                    "No need to pass a file path — the tool automatically uses the latest parquet file."
                    ),
                args_schema=VisualizeQuerySchema,
            )      
        ]

    # Tool implementations
   # @traceable(run_type="tool", name="FileSystem_Read")
    def read_file(self, file_path: str) -> str:
        """
            Read the contents of a file.

            Use when:
            - The user asks to read a file.
            - The user asks what a file does.
            - The user asks for code inspection.

            The file_path must include any discovered subdirectories.
        """
        
        full_path = os.path.join(self.working_dir, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

   # @traceable(run_type="tool", name="List_Files")
    def list_files(self, path: str = ".") -> str:
        full_path = os.path.join(self.working_dir, path)
        try:
            return "\n".join(sorted(os.listdir(full_path)))
        except Exception as e:
            return f"Error listing files: {str(e)}"
 
    #@traceable(run_type="tool", name="List_Available_Databases")    
    def list_available_databases(self, dummy: str = None) -> str:
        """List only .db files in the working directory."""
        try:
            db_files = [
                f for f in sorted(os.listdir(self.working_dir))
                if f.lower().endswith(".db")
            ]
            if not db_files:
                return "No .db files found in the working directory."
            
            result = f"Found {len(db_files)} database(s) in {self.working_dir}:\n\n"
            for db in db_files:
                result += f"• {db}\n"
            return result.strip()
        except Exception as e:
            return f"Error listing databases: {str(e)}"


    def suggest_interesting_queries(self, focus: str = "general") -> str:
        try:
            schema = self.default_db.get_table_info()
            prompt = ChatPromptTemplate.from_template("""
            Schema:
            {schema}

            Suggest 5 diverse, insightful natural language questions a user could ask.
            Focus area: {focus}

            Return only a numbered list, no extra explanation.
            """)
            chain = prompt | self.primary_llm | StrOutputParser()
            return chain.invoke({"schema": schema, "focus": focus})
        except Exception as e:
            return f"Could not generate suggestions: {str(e)}"
        
    #@traceable(run_type="chain", name="Core_DB_Execution_Engine")
    def _execute_db_query(self, db: SQLDatabase, question: str) -> Dict[str, Any]:
        try:
            schema = db.get_table_info()
            prompt = ChatPromptTemplate.from_template("""
            Given the schema, write a correct SQL query to answer the question.
            Return ONLY the SQL query - no explanation, no markdown.

            Schema:
            {schema}

            Question:
            {question}
            """)
            chain = prompt | self.primary_llm | StrOutputParser()

            raw_sql = chain.invoke(
                {"schema": schema, "question": question},
                    config={"run_name": "Text2SQL_Translation_Chain"} # ADDED
                )

            # Clean common markdown fences
            generated_sql = raw_sql.strip()
            cleaned_sql = SQLGuardrail._clean_raw_llm_string(generated_sql)
            
            # INTERCEPT WITH SQLGLOT GUARDRAIL   -----NEW----
            validation = SQLGuardrail.validate_and_optimize(cleaned_sql)
            
            if not validation["valid"]:
                # We return the error *as an observation* to the agent
                return {
                    "sql": cleaned_sql,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "error": f"Guardrail Blocked Execution. Reason: {validation['error']}"
                }
                
            
               
            validated_sql = validation["sql"]   
            print(f"Validated SQL: {validated_sql}")
            results = db._execute(validated_sql)  # returns list of dicts
            
            if not results:
                 return {
                    "sql": validated_sql,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "file_path": None,
                    "error": None
                }
            
            full_rows = [list(row.values()) for row in results]
            # Slice results for Streamlit UI and LangGraoh Pydantic Object AgentState
            display_rows = full_rows[:20]  # Slice to max 50 rows for Streamlit/UI
            print(f"Query returned {len(results)} rows. Displaying first {display_rows} rows.")
            
            # Save FULL dataset to Parquet using PyArrow
            file_name = f"query_{uuid.uuid4().hex[:8]}.parquet"
            file_path = os.path.join(self.working_dir, file_name)
            print(f"Saving Db query to parquet file:{file_path}")
            table = pa.Table.from_pylist(results)
            pq.write_table(table, file_path)

            return {
                "sql": validated_sql,
                "columns": list(results[0].keys()) if results else [],
                "rows": display_rows,
                "row_count": len(results),
                "file_path": file_path,
                "error": None
            }

        except Exception as e:
            return {
                "sql": generated_sql if 'generated_sql' in locals() else "",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "file_path": None,
                "error": str(e)
            }
               
    #@traceable(run_type="tool", name="Tool_Query_Default_DB")
    def query_database(self, question: str) -> Dict[str, Any]:
        """Query the default student_grades.db — returns structured result for frontend rendering."""
        return self._execute_db_query(self.default_db, question)

    #@traceable(run_type="tool", name="Tool_Query_Dynamic_DB")
    def query_any_database(self, db_filename: str, question: str) -> Dict[str, Any]:
        """Query any .db file in the working directory — returns structured result."""
        full_path = os.path.join(self.working_dir, db_filename)
        if not os.path.exists(full_path) or not db_filename.lower().endswith(".db"):
            return {
                "sql": "", "columns": [], "rows": [], "row_count": 0,
                "error": f"File '{db_filename}' not found or is not a .db file."
            }

        try:
            db = SQLDatabase.from_uri(f"sqlite:///{full_path}")
            return self._execute_db_query(db, question)
        except Exception as e:
            return {
                "sql": "", "columns": [], "rows": [], "row_count": 0,
                "error": f"Failed to open database {db_filename}: {str(e)}"
            }
       
    #@traceable(run_type="tool", name="Tool_Schema_Introspection")    
    def get_database_schema(self, db_filename: str) -> str:
        """Safely retrieve table schemas (CREATE TABLE statements) for a database file."""
        full_path = os.path.join(self.working_dir, db_filename)
        if not os.path.exists(full_path) or not db_filename.lower().endswith(".db"):
            return f"Error: Database file '{db_filename}' not found or is not a .db file."
        try:
            # Initialize the SQLDatabase instance on-the-fly for the requested DB
            db = SQLDatabase.from_uri(f"sqlite:///{full_path}", sample_rows_in_table_info=3)
            schema_info = db.get_table_info()
            if not schema_info:
                return f"Database '{db_filename}' is empty or has no tables."
            return schema_info
        except Exception as e:
            return f"Error reading schema metadata for '{db_filename}': {str(e)}"
        
         
    def visualize_query(self, question: str, chart_type: str = "auto") -> Dict[str, Any]:
        """Generate interactive Plotly visualization from parquet query results."""
        
        # Look for the newest .parquet file in the working directory
        try:
            parquet_files = sorted(
                [f for f in os.listdir(self.working_dir) 
                 if f.startswith("query_") and f.endswith(".parquet")],
                key=lambda x: os.path.getmtime(os.path.join(self.working_dir, x)),
                reverse=True
            )
        except Exception as e:
            return {"error": f"Failed to list parquet files: {str(e)}"}
    
        if not parquet_files:
            return {"error": "No previous query result found. Run a database query first."}
        
        data_file = parquet_files[0]
        full_path = os.path.join(self.working_dir, data_file)
        if not os.path.exists(full_path) or not data_file.endswith(".parquet"):
            return {"error": f"Data file '{data_file}' not found or is not a parquet file."}
        
        try:
            df = pd.read_parquet(full_path)
            if df.empty:
                return {"error": "No data available for visualization."}
            
            # Intelligent chart type selection
            if chart_type == "auto":
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0 and len(df.columns) >= 2:
                    chart_type = "bar"
                else:
                    chart_type = "table"

            # Generate figure
            if chart_type == "bar":
                fig = px.bar(df, x=df.columns[0], y=df.columns[1] if len(df.columns) > 1 else numeric_cols[0],
                             title=question[:100], labels={"x": df.columns[0], "y": "Value"})
            elif chart_type == "line":
                fig = px.line(df, x=df.columns[0], y=df.columns[1] if len(df.columns) > 1 else numeric_cols[0],
                              title=question[:100])
            elif chart_type == "pie" and len(df.columns) >= 2:
                fig = px.pie(df, names=df.columns[0], values=df.columns[1], title=question[:100])
            elif chart_type == "histogram":
                fig = px.histogram(df, x=df.columns[0], title=question[:100])
            else:
                fig = px.table(df.head(15), title=question[:100])

            return {
                "type": "visualization",
                "chart_json": fig.to_json(),
                "chart_type": chart_type,
                "data_shape": f"{df.shape[0]} rows x {df.shape[1]} columns",
                "data_preview": df.head(8).to_dict(orient="records"),
                "source_file": data_file
            }

        except Exception as e:
            return {"error": f"Visualization failed: {str(e)}"}

    # Main chat method React loop
    @traceable(run_type="chain", name="ReAct_Agent_Master_Loop")
    def chat(self, user_input: Union[str, List[BaseMessage]], callback_handler=None) -> Dict[str, Any]:
        """
        Returns either:
          - {"type": "text", "content": str}          → normal text answer
          - {"type": "db_result", "result": DbQueryResult}  → database query result to be rendered as table
        """
        
        self.messages = self.system_prompt.copy()
        if isinstance(user_input, str):
            # Terminal/Standalone mode
            self.messages.append(HumanMessage(content=user_input))
        else:
            # LangGraph mode: Extend with the distilled conversational history
            self.messages.extend(user_input)
       
        
        invoke_config = {"run_name": "AIAgent_Inference_Cycle"}
        if callback_handler:
            invoke_config["callbacks"] = [callback_handler]

        while True:
            # Explicit fallback interceptor
            try:
                response: AIMessage = self.primary_with_tools.invoke(self.messages,
                                                                     #config={"run_name": "AIAgent_Inference_Cycle"},
                                                                     config=invoke_config
                                 )
        
            except Exception as e:
                error_str = str(e).lower()
                if any(term in error_str for term in ["429", "rate limit", "503"]):
                    print("⚠️ Primary Groq model rate-limited. Activating secondary Scout safety fallback...")
                    try:
                        response: AIMessage = self.fallback_with_tools.invoke(
                            self.messages,
                            config={"run_name": "AIAgent_Fallback_Inference_Cycle"}
                        )
                    except Exception as fallback_e:
                        
                        # --- THE DEGRADED SYNTHESIS RESCUE BLOCK ---
                        # If the fallback throws a 400 tool error AND the last message was a ToolMessage,
                        # it means the model is just trying to output text/code but tripped the strict Groq parser.
                        if "400" in str(fallback_e) and len(self.messages) > 0 and isinstance(self.messages[-1], ToolMessage):
                            print("🛡️ Fallback tripped the tool parser during synthesis. Unbinding tools and retrying pure text...")
                            unbound_llm = self.fallback_llm.bind(tools=[]) # Properly unbind
                            # Invoke the base LLM *without* the bound tools so Groq's parser ignores it
                            response: AIMessage = unbound_llm.invoke(self.messages,
                                                                     {"run_name": "Degraded_Synthesis_Rescue"})
                            
                        else:
                            print(f"❌ Fallback Model Failed: {str(fallback_e)}")
                            return {"type": "text", "content": f"System critically overloaded. Primary: 429. Fallback: {str(fallback_e)}"}
                else:
                    # Not a rate limit/overload error, raise normally
                    raise e
            
            
            self.messages.append(response)
            
            if not response.tool_calls:
                return {"type": "text", "content": response.content}

            db_output_to_render = None

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                args = tool_call["args"]
                tool_id = tool_call["id"]
                
                # Fetch the current run tree established by app.py's collect_runs()
                parent_run = get_current_run_tree()
                logger.debug(f"Executing tool: {tool_name} | Run tree: {parent_run}")
                
                method = getattr(self, tool_name)
                tool_result = method(**args)
                

                if tool_name in ("query_database", "query_any_database"):
                    # Process structured DB results (ensure result_dict is captured)
                    result_dict = tool_result 
                    # Make the path extremely clear for the LLM
                    file_path = result_dict.get('file_path')
                    short_note = (
                        f"Query executed successfully.\n"
                        f"Total Rows: {result_dict.get('row_count', 0)}\n"
                        f"File saved to: {result_dict.get('file_path', 'N/A')}\n"
                        f"IMPORTANT: Full results saved to this exact file path → {file_path}\n"
                        f"When calling visualize_query, you MUST use this exact path as the data_file argument."
                    )

                    self.messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        content=short_note
                    ))

                    db_output_to_render = {
                        "type": "db_result",
                        "result": DbQueryResult(**result_dict) 
                    }
                elif tool_name == "visualize_query":
                    # Process visualization results
                    viz_result = tool_result                 
                    self.messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        content=f"Visualization generated successfully. Chart type: {viz_result.get('chart_type', 'N/A')}"
                    ))
                    return {"type": "visualization", "result": viz_result}
                
                else:
                    self.messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        content=str(tool_result)
                    ))
                    
            # Return the DB result to the UI if one was generated during this tool-call batch
            if db_output_to_render:
                return db_output_to_render

        # Fallback (should not reach here)
        return {"type": "text", "content": "Finished processing."}
    
# Static Utility Class (holds no state of its own)  
# @classmethod -> no need for guard = SQLGuardrail() instead use SQLGuardrail.validate_query(...)
class SQLGuardrail:
    FORBIDDEN_NODES = (exp.Drop, exp.Delete, exp.Update, exp.Insert, exp.Alter)
    
    @classmethod
    def _clean_raw_llm_string(cls, sql_str: str) -> str:
        """Strips markdown code fences, leading 'sql' blocks, and extra whitespace."""
        cleaned = sql_str.strip()
        
        # 1. Strip markdown fences if they exist (e.g., ```sql ... ``` or ``` ... ```)
        cleaned = re.sub(r"^```(?:sql)?\s*","", cleaned,flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        
        # 2. Check if the string starts with the literal prefix "sql" and strip it
        if cleaned.lower().startswith("sql"):
                cleaned = cleaned[3:].strip()
        
        # 3. Detect and strip wrapping double or single quotes around the entire output
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
                cleaned = cleaned[1:-1].strip()
        
        return cleaned.strip()         

    
    @classmethod
    def validate_and_optimize(cls, sql_str: str) -> dict:
        """
        Parses and verifies the AST of a generated SQL string.
        Returns a dict indicating validity, errors or the sanitized SQL.
        """
        try:
            # Parse into an Abstrat Syntax Tree (AST)
            ast = parse_one(sql_str, read="sqlite")
        except ParseError as e:
            return {"valid": False, "error": f"SQL Syntax Error: {str(e)}"}
        
        # Enforce Read_only Boundaries using expression types
        for forbidden_type in cls.FORBIDDEN_NODES:
            if list(ast.find_all(forbidden_type)):
                return {
                    "valid": False,
                    "error": f"Security Violation: Mutating operation '{forbidden_type.__name__}' detected."
                }
                
        # Programmatically inject a LIMIT clause if it doesn't exist
        # We look for a Select expression node in the AST
        select_node = ast.find(exp.Select)
        
        # if select_node and not ast.find(exp.Limit):
            # Mutate the AST to add a Limit node safely
            # ast = ast.limit(100)  Removed for real db results

        return {
            "valid": True,
            "sql": ast.sql(dialect="sqlite")
        }
        
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".")
    args = parser.parse_args()

    agent = AIAgent(api_key=os.getenv("GROQ_API_KEY"), working_dir=args.directory)
    print("Agent ready. Type 'exit' to quit.")
    while True:
        inp = input("You: ")
        if inp.lower() in ["exit", "quit"]:
            break
        result = agent.chat(inp)
        if result["type"] == "text":
            print(f"Agent: {result['content']}")
        else:
            print(f"Database result received:  {result} (would be rendered in UI)")