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
COPY prompts.yaml .
COPY llm_utils.py .
COPY prompt_loader.py .

# Create expected directories
RUN mkdir -p static config utils

# Copy frontend
COPY telemetry.html static/telemetry.html

# Copy prompts into the location expected by prompt_loader
COPY prompts.yaml config/prompts.yaml

# Copy database files
COPY student_grades.db .
COPY stocks.db .
COPY ecommerce.db .

# Create a simple utils package so the import works
RUN touch utils/__init__.py
COPY prompt_loader.py utils/prompt_loader.py

# Environment
ENV PYTHONUNBUFFERED=1
ENV LANGCHAIN_TRACING_V2=true

EXPOSE 8000

# Start command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]