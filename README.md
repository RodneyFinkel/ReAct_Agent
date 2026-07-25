<img width="1679" height="1043" alt="react_agent" src="https://github.com/user-attachments/assets/c38a97a9-a688-4dde-ad72-8b9a79f14894" />

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
