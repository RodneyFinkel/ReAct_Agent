# Graph Report - .  (2026-07-01)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 58 nodes · 92 edges · 9 communities (7 shown, 2 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_langchain_agent5.py|langchain_agent5.py]]
- [[_COMMUNITY_AIAgent|AIAgent]]
- [[_COMMUNITY_app.py|app.py]]
- [[_COMMUNITY_._execute_db_query|._execute_db_query]]
- [[_COMMUNITY_.chat|.chat]]
- [[_COMMUNITY_SQLGuardrail|SQLGuardrail]]
- [[_COMMUNITY_Telemetry Dashboard|Telemetry Dashboard]]
- [[_COMMUNITY_load_prompt|load_prompt]]
- [[_COMMUNITY_Claude Project Rules|Claude Project Rules]]

## God Nodes (most connected - your core abstractions)
1. `AIAgent` - 17 edges
2. `AgentExecutionRequest` - 4 edges
3. `execute_agent()` - 4 edges
4. `load_prompt()` - 4 edges
5. `get_standalone_agent()` - 3 edges
6. `ReadFileSchema` - 3 edges
7. `ListFilesSchema` - 3 edges
8. `QueryDatabaseSchema` - 3 edges
9. `SuggestQueriesSchema` - 3 edges
10. `QueryAnyDatabaseSchema` - 3 edges

## Surprising Connections (you probably didn't know these)
- `Telemetry Dashboard` --semantically_similar_to--> `Project Requirements`  [INFERRED] [semantically similar]
  static/telemetry.html → requirements.txt
- `AgentExecutionRequest` --uses--> `AIAgent`  [INFERRED]
  app.py → langchain_agent5.py
- `get_standalone_agent()` --calls--> `AIAgent`  [EXTRACTED]
  app.py → langchain_agent5.py
- `DB Agent Prompt` --conceptually_related_to--> `Telemetry Dashboard`  [INFERRED]
  config/prompts.yaml → static/telemetry.html
- `Claude Project Rules` --references--> `Graphify Skill Definition`  [EXTRACTED]
  CLAUDE.md → .claude/skills/graphify/SKILL.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Ecosystem** — claude_md, claude_skills_graphify_skill_md, requirements_txt [EXTRACTED 1.00]

## Communities (9 total, 2 thin omitted)

### Community 0 - "langchain_agent5.py"
Cohesion: 0.33
Nodes (10): BaseModel, DbQueryResult, GetDatabaseSchemaSchema, ListAvailableDatabasesSchema, ListFilesSchema, QueryAnyDatabaseSchema, QueryDatabaseSchema, ReadFileSchema (+2 more)

### Community 1 - "AIAgent"
Cohesion: 0.18
Nodes (4): AIAgent, Read the contents of a file.              Use when:             - The user asks, List only .db files in the working directory., Safely retrieve table schemas (CREATE TABLE statements) for a database file.

### Community 2 - "app.py"
Cohesion: 0.24
Nodes (8): AgentExecutionRequest, execute_agent(), get_agent_trace(), get_root_interface(), get_standalone_agent(), Interrogates the LangSmith platform API programmatically using the SDK client., Serves the unified, programmatic tracing console directly., Executes the ReAct agent within a run-collection block,     capturing the exact

### Community 3 - "._execute_db_query"
Cohesion: 0.50
Nodes (3): Any, Query any .db file in the working directory — returns structured result., SQLDatabase

### Community 4 - ".chat"
Cohesion: 0.40
Nodes (3): BaseMessage, Query the default student_grades.db — returns structured result for frontend ren, Returns either:           - {"type": "text", "content": str}          → normal t

### Community 5 - "SQLGuardrail"
Cohesion: 0.40
Nodes (3): Strips markdown code fences, leading 'sql' blocks, and extra whitespace., Parses and verifies the AST of a generated SQL string.         Returns a dict in, SQLGuardrail

### Community 6 - "Telemetry Dashboard"
Cohesion: 0.67
Nodes (3): DB Agent Prompt, Project Requirements, Telemetry Dashboard

## Knowledge Gaps
- **2 isolated node(s):** `Project Requirements`, `Claude Project Rules`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AIAgent` connect `AIAgent` to `langchain_agent5.py`, `app.py`, `._execute_db_query`, `.chat`?**
  _High betweenness centrality (0.481) - this node is a cross-community bridge._
- **Why does `SQLGuardrail` connect `SQLGuardrail` to `langchain_agent5.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **What connects `Executes the ReAct agent within a run-collection block,     capturing the exact`, `Interrogates the LangSmith platform API programmatically using the SDK client.`, `Serves the unified, programmatic tracing console directly.` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._