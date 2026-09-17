"""
Local, fine-tuned classifier for the EU AI Act risk-tier task.

Base model: Qwen2.5-1.5B-Instruct, QLoRA fine-tuned on 145 programmatically
generated scenarios (finetune/build_training_data.py), evaluated against the
6 classification questions in evals/ground_truth.json that were never in the
training set.

Measured result (finetune/eval_comparison.json): base model 2/6 (33%) tier
accuracy -> fine-tuned 3/6 (50%) on that held-out set. A real, modest
improvement on a genuinely small sample, not a large one -- reported as-is.
Article-field accuracy did not improve (0/5 for both). This is an optional,
local, no-API-key alternative to the Gemini classifier in classifier.py, not
a wholesale replacement -- see README for when to use which.
"""
import json
import re
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

from agents.state import LexAgentState

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_DIR = Path(__file__).parent.parent / "finetune" / "lexpilot-classifier-lora"

SYSTEM_PROMPT = (
    "You must respond with ONLY valid JSON. No explanation, no markdown, no preamble.\n"
    'Schema: {"tier": "prohibited|high-risk|limited-risk|minimal-risk", '
    '"matched_article": "Article X or null", "matched_annex_entry": "string or null", '
    '"reasoning": "string", "confidence": "high|medium|low"}\n'
    "You are analyzing an AI system to classify it under the EU AI Act.\n"
    "Rules:\n"
    "1. Prohibited (Article 5): Social scoring, real-time remote biometric id in public, "
    "cognitive behavioral manipulation, untargeted facial recognition scraping, emotion "
    "inference in workplace/education, biometric categorization based on sensitive traits "
    "(political/religious/sexual), predictive policing.\n"
    "2. High-Risk (Annex III): Biometric identification and categorisation; Critical "
    "infrastructure management; Education and vocational training; Employment, HR, and "
    "access to self-employment; Access to essential private/public services; Law "
    "enforcement; Migration, asylum, border control; Justice and democratic processes. "
    "ALSO: Safety component of a product under Annex I.\n"
    "3. Limited-Risk: Chatbot, emotion recognition (outside workplace/ed), deep fakes "
    "(with disclosure), general-purpose AI.\n"
    "4. Minimal-Risk: Everything else (e.g. spam filters, video games, inventory management)."
)

_model = None
_tokenizer = None

def _load():
    global _model, _tokenizer
    if _model is not None:
        return
    if not ADAPTER_DIR.exists():
        raise RuntimeError(
            f"Fine-tuned adapter not found at {ADAPTER_DIR}. "
            "Run finetune/build_training_data.py then finetune/train_qlora.py first."
        )
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    _tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb_config, device_map="auto", torch_dtype=torch.bfloat16,
    )
    _model = PeftModel.from_pretrained(base, str(ADAPTER_DIR))
    _model.eval()

async def classify_ai_system_local(state: LexAgentState) -> LexAgentState:
    """Same interface/output shape as agents.classifier.classify_ai_system,
    but runs entirely locally on the fine-tuned model, no API key, no network call."""
    start_t = time.time()
    _load()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"User Description: {state['user_message']}"},
    ]
    prompt = _tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)

    try:
        with torch.no_grad():
            out = _model.generate(**inputs, max_new_tokens=200, do_sample=False, temperature=None, top_p=None)
        text = _tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        result = json.loads(match.group(0)) if match else {}
        state["classification_result"] = {
            "tier": result.get("tier", "minimal-risk"),
            "articles": [a for a in [result.get("matched_article"), result.get("matched_annex_entry")] if a],
            "reasoning": result.get("reasoning", "No reasoning provided."),
        }
    except Exception as e:
        state["error"] = f"Local classification failed: {e}"
        state["classification_result"] = {"tier": "unknown", "articles": [], "reasoning": str(e)}

    latency = int((time.time() - start_t) * 1000)
    trace = state.get("agent_trace", [])
    trace.append({
        "agent": "classifier_local_finetuned",
        "action": "classify",
        "input": {"message": state["user_message"]},
        "output": state["classification_result"],
        "latency_ms": latency,
    })
    state["agent_trace"] = trace
    return state
