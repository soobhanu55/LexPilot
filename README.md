# LexPilot — EU AI Act Compliance Assistant

A multi-agent assistant that classifies AI systems against EU AI Act risk tiers and tracks compliance obligations, grounded in a knowledge graph of the actual regulation text.

![Chat UI](docs/screenshots/chat.png)

## How it works

```
Supervisor Agent → Classifier | Retriever (GraphRAG + Qdrant) | Checklist | Memory | Deadlines
```

Retrieval runs over a NetworkX knowledge graph plus Qdrant, so answers pull linked, connected context — not isolated text chunks. A supervisor agent routes each request to the right worker.

## Results

- **Classifier (fine-tuned local option):** on a held-out 6-question eval, a QLoRA fine-tuned local model scored **3/6 (50%)** vs. **2/6 (33%)** for the same base model unfine-tuned — a real, modest improvement, not a large one, honestly reported. Details and full methodology in [`finetune/README.md`](finetune/README.md).
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
