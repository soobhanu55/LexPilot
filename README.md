# LexAgent - EU AI Act Compliance Assistant

LexAgent is an AI-powered compliance assistant designed specifically for the German and broader European market. It helps companies classify their AI systems against the newly active EU AI Act risk tiers (Prohibited, High-Risk, Limited-Risk, Minimal-Risk) and systematically tracks compliance obligations across a centralized, auditable dashboard. By replacing manual reading of complex legal texts with an agentic approach, LexAgent directly minimizes legal exposure and accelerates AI deployment time.

The platform utilizes a state-of-the-art multi-agent architecture powered by LangGraph, where a supervisor orchestrates specialized workers (Classifier, Retriever, Checklist Generator, Memory Maintainer) to yield highly accurate and locally verifiable answers using Ollama. All interactions, data, and knowledge graphs remain fully isolated and run locally (Qdrant + PostgreSQL), providing the zero-data-leakage guarantee demanded by enterprise and governmental clients under the GDPR and EU AI Act constraints.

## Architecture

```text
User Request --> FastAPI / SSE
                      |
                 Supervisor Agent
                 /    |   \     \
       Classifier    ...  Memory  Deadlines
       (Ollama)           (PostgreSQL DB)
             |
         Retriever
     (GraphRAG + Qdrant)
```

## Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Ollama running locally with `mistral:7b-instruct` and `nomic-embed-text` pulled.

## Setup Steps

1. Install Dependencies
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install && cd ..
   ```
2. Pull Models
   ```bash
   ollama pull mistral:7b-instruct
   ollama pull nomic-embed-text
   ```
3. Prepare Environment
   ```bash
   cp .env.example .env
   ```
4. Start Infrastructure
   ```bash
   docker-compose up -d
   ```
   *(This launches Qdrant, Postgres locally, and will start the API and Frontend)*

## Ingestion Pipeline

To initialize the GraphRAG base with the EU AI Act text:

```bash
python -m ingestion.run_pipeline
```
This scrapes EUR-Lex, builds the NetworkX knowledge graph, and upserts text chunks into Qdrant.

## Running Evals

To evaluate retrieval speed and agent classification accuracy against the ground truth:

```bash
pytest evals/ -v
```

## API Endpoint Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/chat` | Streams agent responses & citations (SSE) |
| GET | `/inventory/{company_id}` | Lists all AI systems |
| POST | `/inventory/{company_id}` | Add a new AI system |
| PATCH| `/inventory/{company_id}/{sys_id}` | Updates compliance status |
| GET | `/audit/{company_id}` | Returns structured audit log (Article 12) |
| GET | `/audit/{company_id}/export`| Exports logs to JSON |

## EU AI Act Enforcement Timeline

| Milestone | Date | Applicable Articles |
|---|---|---|
| Prohibited AI practices ban | 2025-02-02 | Article 5 |
| GPAI model obligations | 2025-08-02 | Articles 51-56 |
| Full Act enforcement | 2026-08-02 | All | 
| High-risk (Annex III) | 2027-12-02 | Article 6, Annex III |
| High-risk (Annex I) | 2028-08-02 | Annex I |

## Tech Stack

| Layer | Technology |
|---|---|
| Models | Ollama Mistral / Nomic |
| Database | PostgreSQL 15 |
| Vector DB | Qdrant |
| Graph | NetworkX |
| Agents | LangGraph |
| Backend | FastAPI |
| Frontend | Next.js 14 |
| Evaluation| RAGAs / Pytest |

![Chat UI](docs/screenshots/chat.png)
