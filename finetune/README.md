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

## Evaluation

### 60-item held-out set (`eval_set.jsonl`, `evaluate_set.py`, `eval_large.json`)

15 hand-written descriptions per tier (8 in German), labelled against the Act's text (Art. 5 prohibited practices, Annex III areas, Art. 50
transparency duties) and disjoint from the training data (a test checks this). Written by the assistant that built the repo, not by a lawyer, and
emotion recognition outside work and school was left out because the Act and LexPilot's rubric disagree on it. Same base model, same prompt, only the
adapter differs; the shipped adapter plus two extra training seeds (`python finetune/train_qlora.py --seed N --out DIR`) to show run-to-run spread.

| Model | Correct | Accuracy (95% Wilson interval) | prohibited | high-risk | limited-risk | minimal-risk | McNemar p vs base |
|---|---|---|---|---|---|---|---|
| Base, zero-shot | 27/60 | 45.0% (33.1 to 57.5) | 100% | 0% | 20% | 60% | n/a |
| Fine-tuned (shipped adapter) | 30/60 | 50.0% (37.7 to 62.3) | 13% | 93% | 0% | 93% | 0.74 |
| Fine-tuned (seed 1) | 29/60 | 48.3% (36.2 to 60.7) | 13% | 87% | 0% | 93% | 0.86 |
| Fine-tuned (seed 2) | 29/60 | 48.3% (36.2 to 60.7) | 13% | 87% | 0% | 93% | 0.86 |

Chance is 25%. **Fine-tuning did not improve overall accuracy beyond noise**, and the three seeds agree with each other, so this is not a bad seed.
It changed which errors the model makes: it learned that most inputs are high-risk or minimal-risk, loses the base model's perfect prohibited recall
(13 of 15 prohibited cases become high-risk) and never outputs limited-risk (chatbots and generators become minimal-risk). The training set (145
templated examples built from one prompt pattern) is probably too narrow in phrasing for the new descriptions; more varied training data, more
limited-risk and prohibited examples, and a larger model are the obvious next experiments. Until then the Gemini classifier stays the default and
this local one is an experiment, not a replacement.

### The original 6 questions (`evaluate.py`, `eval_comparison.json`)

On the 6 classification questions in `evals/ground_truth.json` the base model scored 2/6 and the fine-tuned one 3/6; with six items that difference is
meaningless, which is why the 60-item set above was added. Article-citation accuracy was 0/5 for both.

## Using it

Set `USE_LOCAL_CLASSIFIER=true` in `.env` to route the classifier node through the local fine-tuned model (`agents/local_classifier.py`) instead of Gemini. No API key needed for this path; it does need the extra dependencies in `finetune/requirements.txt` and a CUDA GPU with 4-bit quantization support. Gemini remains the default — this is an optional, local, honestly-evaluated alternative for one specific step, not a wholesale replacement of the pipeline.
