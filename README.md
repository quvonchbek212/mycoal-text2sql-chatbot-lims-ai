# 🔬 MyCoal.uz LIMS AI Assistant · Text-to-SQL & Analytics Engine

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![vLLM](https://img.shields.io/badge/Inference-vLLM%20%28OpenAI%20API%29-purple.svg)](https://vllm.ai)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%28Read--Only%29-336791.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Deployment-Docker-2496ED.svg)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An intelligent conversational analytics microservice built for the **MyCoal.uz** platform and the central **Laboratory Information Management System (LIMS)** of **O'zbekko'mir** (Uzbekistan State Coal Corporation).

Enables laboratory technicians, quality dispatchers, and executive leadership to query complex coal quality metrics, chemical assay results, and shipment logistics in natural language (Uzbek, Russian, or English) with automated translation into verified, high-performance PostgreSQL queries.

---

## 🌟 Key Capabilities

* **Natural Language Text-to-SQL:** Seamlessly converts domain-specific questions (*e.g., "Qaysi ko'mir omborida kul miqdori 15% dan past bo'lgan zaxira bor?"*) into optimized SQL queries.
* **Multi-Stage LangGraph Orchestration:**
  1. *Intent Screening:* Filters out-of-scope or ungrounded queries.
  2. *Schema Mapping:* Pinpoints relevant laboratory tables, assay metrics, and warehouse indices.
  3. *SQL Generation:* Synthesizes dialeted PostgreSQL statements using few-shot domain exemplars.
  4. *AST Security Linter:* Strictly forbids destructive operations (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `GRANT`).
  5. *Self-Correction Loop:* Automatically diagnoses database execution errors and refines SQL syntax up to 3 iterations.
  6. *Synthesized Synthesis:* Returns both human-readable analytical summaries and raw tabular data.
* **Strict Read-Only Isolation:** Connects via least-privilege read-only database roles, preventing any state modification.
* **Contextual Multi-Turn Memory:** Retains conversational context for iterative drill-down exploration.

---

## 🏛 LangGraph Workflow Architecture

```text
       [User Inquiry]
             │
             ▼
    ┌─────────────────┐
    │ 1. Guardrail    │ ──(Irrelevant / Unsafe)──► [Friendly Rejection]
    │    Intent Check │
    └────────┬────────┘
             │ (Valid Query)
             ▼
    ┌─────────────────┐
    │ 2. Schema       │
    │    Pruning      │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 3. SQL Engine   │ <───────────────────────┐
    │    (LLM Gen)    │                         │
    └────────┬────────┘                         │ (Self-Correction Loop)
             │                                  │
             ▼                                  │
    ┌─────────────────┐                         │
    │ 4. AST Security │ ──(Unsafe Token)──► [Blocked]
    │    Validation   │                         │
    └────────┬────────┘                         │
             │ (Safe Read-Only)                 │
             ▼                                  │
    ┌─────────────────┐                         │
    │ 5. Execution &  │ ──(Database Error)──────┘
    │    Data Fetch   │
    └────────┬────────┘
             │ (Data Received)
             ▼
    ┌─────────────────┐
    │ 6. Analytical   │
    │    Synthesis    │ ──► [Structured Text & JSON Table Output]
    └─────────────────┘
```

---

## 🚀 API Endpoints

### Chat Completion & Query
`POST /api/v1/chat/completions`
```json
{
  "message": "Oxirgi 7 kundagi Angren koni bo'yicha o'rtacha namlik va kul miqdorini ko'rsat",
  "session_id": "lab-session-9021"
}
```

### Health & Readiness
`GET /health`
Verifies database connectivity, vLLM endpoint availability, and vector schema index status.

---

## 🛠 Quickstart

```bash
# Clone the repository
git clone https://github.com/quvonchbek212/mycoal-text2sql-chatbot-lims-ai.git
cd mycoal-text2sql-chatbot-lims-ai

# Configure environment
cp .env.example .env

# Launch with Docker Compose
docker compose up -d --build
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
