FROM python:3.12-slim

# System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# INSTALL PYTHON DEPENDENCIES
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY langchain_agent5.py .
# Copy config
COPY config/prompts.yaml config/prompts.yaml

# Copy utils
COPY utils/prompt_loader.py utils/prompt_loader.py
COPY utils/llm_utils.py utils/llm_utils.py
RUN touch utils/__init__.py

# Copy frontend
COPY static/telemetry.html static/telemetry.html
COPY static/splash.html static/splash.html
COPY static/system_architecture.svg static/system_architecture.svg

# Copy database files
COPY student_grades.db .
COPY databases/stocks.db .
COPY databases/ecommerce.db .
COPY databases/stock_database_fin.db .
COPY databases/stock_database2.db .


# Environment
ENV PYTHONUNBUFFERED=1
ENV LANGCHAIN_TRACING_V2=true

EXPOSE 8000

# Start command
CMD ["python3", "app.py"]