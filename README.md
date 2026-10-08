# LexPilot — EU AI Act Compliance Assistant

A multi-agent assistant that classifies AI systems against EU AI Act risk tiers and tracks compliance obligations, grounded in a knowledge graph of the actual regulation text.

![Chat UI](docs/screenshots/chat.png)

## How it works

```
Supervisor Agent → Classifier | Retriever (GraphRAG + Qdrant) | Checklist | Memory | Deadlines
```

Retrieval runs over a NetworkX knowledge graph plus Qdrant, so answers pull linked, connected context — not isolated text chunks. A supervisor agent routes each request to the right worker.

**Cost cap and retries.** One user request can trigger several Gemini calls (intent, the worker agent, the final answer). Every call goes through `settings.get_llm()`, which adds up real token usage per request and refuses the next call once the request has spent `MAX_USD_PER_REQUEST` (default $0.01); the user gets a clear "cost cap reached" message instead of a silent bill. Transient API errors are retried twice, and retries count against the same budget. Logic and self-check in [`config/cost_guard.py`](config/cost_guard.py) (`python -m config.cost_guard`).

## Results

- **Classifier (fine-tuned local option), 60-item held-out set:** the QLoRA model does **not** beat its base model overall: base 27/60 (45%), fine-tuned 30/60 (50%), and two more training seeds 29/60 each (95% intervals about 33-62%, McNemar p = 0.74 to 0.86 against the base). What changed is the failure mode: the base model gets every prohibited case right and no high-risk case; the fine-tuned model gets high-risk and minimal-risk right (93%) but calls most prohibited cases high-risk and never predicts limited-risk. The earlier "3/6 vs 2/6" came from 6 questions, which cannot separate models. Gemini (the default) is unchanged and unmeasured here. Details in [`finetune/README.md`](finetune/README.md).
- **Retriever accuracy:** not yet measured — running it needs a Gemini API key that wasn't available when this was last reviewed. Stated here rather than left unclear.

**Corrected note:** earlier versions of this README described a fully local, Ollama-based architecture that was never actually implemented — the code only ever called Gemini. That's now fixed for real: the classifier has a genuinely trained and evaluated local alternative (above), not just aspirational documentation.

## Run it

```bash
pip install -r requirements.txt && cd frontend && npm install && cd ..
cp .env.example .env   # add GOOGLE_API_KEY, or set USE_LOCAL_CLASSIFIER=true
docker-compose up -d    # Qdrant, Postgres, API, frontend

python -m ingestion.run_pipeline   # builds the knowledge graph from EU AI Act text
pytest evals/ -v                    # reproduce the classification eval
```

To use the local fine-tuned classifier instead of Gemini (no API key needed for that step):

```bash
pip install -r finetune/requirements.txt
python finetune/build_training_data.py && python finetune/train_qlora.py
# set USE_LOCAL_CLASSIFIER=true in .env
```

Full architecture, API reference, and enforcement timeline in [`docs/DETAILS.md`](docs/DETAILS.md).

## Observability

Every chat request gets an id (in the stream's final `done` event, with a usage summary: LLM calls, LLM milliseconds, input/output tokens, cost). `GET /traces/{request_id}` returns the span tree behind it: one span per agent (`agent.classifier`, `agent.retriever`, ...) and one `llm.call` span per model call underneath, each with latency, tokens, cost and error status, using the OpenTelemetry GenAI attribute names. Spans are kept in memory for the latest 200 requests; set `OTEL_EXPORTER_OTLP_ENDPOINT` to ship the same spans to Langfuse, Jaeger or Tempo (the OTLP export is not exercised in CI). Cost uses the flat Gemini 1.5 Flash list price the cost cap already assumed; any other model is reported as unpriced (`null`), not guessed. The per-request cost cap and the Article 12 audit log (`/audit`) are unchanged.

## Tests

62 offline tests (scripted LLM, stubbed Qdrant and Postgres, no keys): every agent node, the LangGraph supervisor's streamed events including session memory and the cost cap, the retriever's graph expansion and rerank fallbacks, the FastAPI routes, the data hygiene of the training and evaluation sets, the ingestion graph, and the tracing (agent spans, LLM-call tokens and cost, error spans, nesting, the endpoint). CI fails below 60% line coverage. Writing them found two real defects, both fixed: the API package could not be imported at all (a renamed folder left every import and the Docker commands pointing at `api`), and the chat endpoint double-wrapped its server-sent events (`data: data: {...}`), which the frontend could not parse.
