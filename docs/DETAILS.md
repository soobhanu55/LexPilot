# LexPilot — Full Details

LexPilot is an AI-powered compliance assistant designed specifically for the German and broader European market. It helps companies classify their AI systems against the EU AI Act risk tiers (Prohibited, High-Risk, Limited-Risk, Minimal-Risk) and systematically tracks compliance obligations across a centralized, auditable dashboard.

The platform uses a multi-agent architecture powered by LangGraph, where a supervisor orchestrates specialized workers (Classifier, Retriever, Checklist Generator, Memory Maintainer). Retrieval runs over a NetworkX knowledge graph plus Qdrant, so answers stay grounded in linked source material rather than isolated text fragments.

**Corrected note (2026-09):** earlier versions of this README described a fully local, Ollama-based architecture. That was aspirational documentation, not the actual state of the code — `config/settings.py` only ever called Google Gemini, and no Ollama code path existed anywhere in this repo. This has since been fixed for real: see `finetune/README.md` for a QLoRA fine-tuned local classifier, actually trained and measured, that can now genuinely replace the Gemini call for the classification step.

## Architecture

```text
User Request --> FastAPI / SSE
                      |
                 Supervisor Agent
                 /    |   \     \
       Classifier    ...  Memory  Deadlines
    (Gemini, or local  |         (PostgreSQL DB)
     QLoRA -- see       |
     finetune/)     Retriever
                 (GraphRAG + Qdrant)
```

## Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- A Google Gemini API key (free tier available), or the local fine-tuned classifier (see `finetune/README.md`) if you want to run the classification step without one.

## Setup Steps

1. Install Dependencies
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install && cd ..
   ```
2. Prepare Environment
   ```bash
   cp .env.example .env
   # add GOOGLE_API_KEY, or set USE_LOCAL_CLASSIFIER=true to skip it for classification
   ```
3. Start Infrastructure
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

A real, hand-labeled 10-question ground-truth set already exists (`evals/ground_truth.json`: 6 questions with an expected EU AI Act risk tier, 8 with expected source articles), evaluable via:

```bash
pytest evals/ -v
```

**Not run yet, disclosed honestly rather than left unclear:** both the classifier (`agents/classifier.py`) and the retriever's reranking step (`agents/retriever.py`) call Google Gemini directly with no local/offline fallback in this path — there's no rule-based path in this codebase to substitute for the retriever. Running this eval for real requires a Google Gemini API key (Gemini has a genuinely free tier with no credit card required, similar to Groq) which wasn't available when this repo was last reviewed. No accuracy number is reported here because none has actually been measured — that's the honest state, not a guess dressed up as a result. **The classification step specifically now has a measured local alternative** — see `finetune/README.md` for the actual trained-and-evaluated numbers (base model 2/6, fine-tuned 3/6 on this same held-out set).

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
| Models | Google Gemini (default), or a local QLoRA-fine-tuned Qwen2.5-1.5B for classification (`finetune/`) |
| Database | PostgreSQL 15 |
| Vector DB | Qdrant |
| Graph | NetworkX |
| Agents | LangGraph |
| Backend | FastAPI |
| Frontend | Next.js 14 |
| Evaluation| RAGAs / Pytest |
