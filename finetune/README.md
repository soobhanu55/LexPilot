# Local fine-tuned classifier

The main README previously described a "local, Ollama-based" architecture that was never actually implemented — `config/settings.py` only ever called Gemini, no Ollama code path existed anywhere in the codebase. That gap has been corrected here: this is a real, working local classifier, trained and measured, not aspirational documentation.

## What this is

QLoRA fine-tunes `Qwen/Qwen2.5-1.5B-Instruct` (4-bit, r=16 LoRA adapter, 18.5M trainable params) on the EU AI Act risk-tier classification task — the same task `agents/classifier.py` does by calling Gemini. Runs entirely on a single consumer GPU (developed and trained on a 6GB RTX 4050 laptop GPU).

## Training data

`build_training_data.py` generates 165 labeled examples (145 train / 20 val) programmatically across the four risk tiers, using varied industries and phrasings — **strictly disjoint from `evals/ground_truth.json`**, which is held out for evaluation only and never appears in training.

```bash
python finetune/build_training_data.py
```

## Training

```bash
pip install -r finetune/requirements.txt
python finetune/train_qlora.py
```

3 epochs, ~107 seconds on the RTX 4050. Saves a LoRA adapter to `finetune/lexpilot-classifier-lora/`.

## Evaluation — the honest result

`evaluate.py` compares the **same base model, with and without the fine-tuned adapter**, on the 6 classification questions in `evals/ground_truth.json` (the other 4 ground-truth entries are retriever-only questions, out of scope for a classifier and correctly excluded, matching `evals/test_classification.py`'s own methodology).

```bash
python finetune/evaluate.py
```

**Measured result** (`finetune/eval_comparison.json`):

| Model | Tier accuracy | Article-field accuracy |
|---|---|---|
| Base (zero-shot) | 2/6 (33%) | 0/5 |
| **Fine-tuned (QLoRA)** | **3/6 (50%)** | 0/5 |

A real, modest improvement — not a large one, and on a genuinely small sample (6 questions). One case that the base model got right, the fine-tuned model got wrong (the real-time-facial-recognition prohibited case), while two others flipped from wrong to right. Article-field accuracy (matching the specific Article/Annex citation) did not improve at all for either model — the fine-tuning helped tier classification, not citation precision. Reported here as it measured, not rounded up or cherry-picked.

## Using it

Set `USE_LOCAL_CLASSIFIER=true` in `.env` to route the classifier node through the local fine-tuned model (`agents/local_classifier.py`) instead of Gemini. No API key needed for this path; it does need the extra dependencies in `finetune/requirements.txt` and a CUDA GPU with 4-bit quantization support. Gemini remains the default — this is an optional, local, honestly-evaluated alternative for one specific step, not a wholesale replacement of the pipeline.
