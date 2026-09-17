"""
Evaluates the fine-tuned classifier against the SAME base model with no
fine-tuning, on evals/ground_truth.json -- the 6 classification questions
that were never included in finetune/data/{train,val}.jsonl.

This is the honest comparison: same model, same prompt, only the weights differ.
"""
import json
import re
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_DIR = Path(__file__).parent / "lexpilot-classifier-lora"
GROUND_TRUTH = Path(__file__).parent.parent / "evals" / "ground_truth.json"

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

def load_model(with_adapter: bool):
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb_config, device_map="auto", torch_dtype=torch.bfloat16,
    )
    if with_adapter:
        model = PeftModel.from_pretrained(model, str(ADAPTER_DIR))
    model.eval()
    return model, tokenizer

def classify(model, tokenizer, question: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"User Description: {question}"},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=200, do_sample=False, temperature=None, top_p=None)
    text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    # try to extract JSON even if the model wraps it in text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"tier": "unknown", "articles": [], "raw": text}
    try:
        result = json.loads(match.group(0))
        return {
            "tier": result.get("tier", "unknown"),
            "articles": [a for a in [result.get("matched_article"), result.get("matched_annex_entry")] if a],
            "raw": text,
        }
    except json.JSONDecodeError:
        return {"tier": "parse_error", "articles": [], "raw": text}

def run_eval(model, tokenizer, tasks, label):
    correct_tier = 0
    correct_article = 0
    n_tier = 0
    n_article = 0
    results = []
    for task in tasks:
        res = classify(model, tokenizer, task["question"])
        row = {"question": task["question"], "predicted": res["tier"], "raw": res["raw"]}
        if "expected_tier" in task:
            n_tier += 1
            ok = task["expected_tier"].lower() in res["tier"].lower()
            correct_tier += int(ok)
            row["expected_tier"] = task["expected_tier"]
            row["tier_correct"] = ok
        if task.get("expected_articles"):
            n_article += 1
            found = any(ea in " ".join(res["articles"]) for ea in task["expected_articles"])
            correct_article += int(found)
            row["expected_articles"] = task["expected_articles"]
            row["article_correct"] = found
        results.append(row)

    print(f"\n=== {label} ===")
    print(f"Tier accuracy: {correct_tier}/{n_tier}")
    print(f"Article accuracy: {correct_article}/{n_article}")
    for r in results:
        mark = "OK" if r.get("tier_correct", r.get("article_correct", False)) else "MISS"
        print(f"  [{mark}] {r['question'][:70]}...")
        if "expected_tier" in r:
            print(f"        expected={r['expected_tier']}  got={r['predicted']}")
    return {"label": label, "tier_correct": correct_tier, "tier_total": n_tier,
            "article_correct": correct_article, "article_total": n_article, "results": results}

def main():
    with open(GROUND_TRUTH, encoding="utf-8") as f:
        all_tasks = json.load(f)
    # Match evals/test_classification.py's own methodology: only the 6 questions
    # with an expected_tier are classifier tasks. The other 4 are pure article-
    # lookup questions meant for the retriever agent, not classify_ai_system --
    # scoring the classifier against those would be testing the wrong component.
    tasks = [t for t in all_tasks if "expected_tier" in t]
    print(f"Evaluating on {len(tasks)} classification tasks (of {len(all_tasks)} total ground-truth entries; "
          f"the other {len(all_tasks) - len(tasks)} are retriever-only questions, out of scope here).")

    print("Loading BASE model (no fine-tuning)...")
    base_model, tokenizer = load_model(with_adapter=False)
    base_report = run_eval(base_model, tokenizer, tasks, "BASE (Qwen2.5-1.5B-Instruct, zero-shot)")
    del base_model
    torch.cuda.empty_cache()

    print("\nLoading FINE-TUNED model (same base + LoRA adapter)...")
    ft_model, tokenizer = load_model(with_adapter=True)
    ft_report = run_eval(ft_model, tokenizer, tasks, "FINE-TUNED (Qwen2.5-1.5B-Instruct + QLoRA)")

    out_path = Path(__file__).parent / "eval_comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"base": base_report, "fine_tuned": ft_report}, f, indent=2)

    print(f"\nFull comparison written to {out_path}")
    print(f"\nSummary: base tier accuracy {base_report['tier_correct']}/{base_report['tier_total']}, "
          f"fine-tuned tier accuracy {ft_report['tier_correct']}/{ft_report['tier_total']}")

if __name__ == "__main__":
    main()
