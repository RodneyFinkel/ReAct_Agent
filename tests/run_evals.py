from langchain_agent5 import AIAgent
import os
import sqlite3
import sqlglot
from langsmith import Client, evaluate
from typing import Any

client = Client()
DATASET_NAME = "Text-to-SQL-Edge-Cases=v1"


def predict_text_to_sql(inputs: dict) -> dict:
    user_query = inputs["question"]
    agent = AIAgent(
        api_key=os.getenv("GROQ_API_KEY"),
        working_dir="."
    )
    
    # Trigger react agent masterloop
    response = agent.chat(user_query)
    
    # Extract the generated SQL from response schema
    sql_query = ""
    if isinstance(response, dict) and response.get("type") == "db_result":
        # Access the Piydantic DbQUeryResult Object
        res_obj = response.get("result")
        sql_query = getattr(res_obj, "sql", "")
        
    return {"sql_query": sql_query}

