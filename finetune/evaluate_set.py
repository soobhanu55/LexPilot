"""Evaluates base vs fine-tuned classifiers on the 60-item held-out set (finetune/eval_set.jsonl).

    python finetune/evaluate_set.py --adapters finetune/lexpilot-classifier-lora /path/seed1 /path/seed2

Same base model, same prompt, only the adapter differs. Reports exact tier accuracy with a 95% Wilson interval,
per-tier recall, unparseable-output rate, and an exact McNemar test of each adapter against the base model.
The 6-question set in evals/ground_truth.json was the only evaluation before; 6 items cannot separate models.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
TIERS = ["prohibited", "high-risk", "limited-risk", "minimal-risk"]


def normalise(tier: str) -> str:
    """Canonical tier name, or 'invalid' when the model's string is not one of the four tiers."""
    t = re.sub(r"[\s_]+", "-", str(tier).strip().lower())
    return t if t in TIERS else "invalid"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def mcnemar_exact(only_a: int, only_b: int) -> float:
    n = only_a + only_b
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(only_a, only_b) + 1)) / 2 ** n)


def summarise(name: str, items: list[dict], preds: list[str]) -> dict:
    correct = [normalise(p) == it["tier"] for p, it in zip(preds, items)]
    k, n = sum(correct), len(items)
    lo, hi = wilson(k, n)
    support = {t: sum(it["tier"] == t for it in items) for t in TIERS}
    recall = {t: sum(c for c, it in zip(correct, items) if it["tier"] == t) / support[t] for t in TIERS if support[t]}
    return {"name": name, "correct": k, "n": n, "accuracy": k / n, "ci95": [lo, hi], "recall": recall,
            "invalid_outputs": sum(normalise(p) == "invalid" for p in preds),
            "confusion": {t: dict(Counter(normalise(p) for p, it in zip(preds, items) if it["tier"] == t)) for t in TIERS},
            "per_item_correct": correct, "predictions": preds}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapters", nargs="+", required=True)
    ap.add_argument("--set", default=str(HERE / "eval_set.jsonl"))
    ap.add_argument("--out", default=str(HERE / "eval_large.json"))
    args = ap.parse_args()

    sys.path.insert(0, str(HERE))
    import torch  # noqa: E402
    from peft import PeftModel  # noqa: E402

    import evaluate as ev  # noqa: E402  (finetune/evaluate.py: same prompt and generation as the 6-question run)

    items = [json.loads(line) for line in Path(args.set).read_text(encoding="utf-8").splitlines() if line.strip()]
    runs = []

    def run(label, model, tok):
        preds = [ev.classify(model, tok, it["text"])["tier"] for it in items]
        runs.append(summarise(label, items, preds))
        r = runs[-1]
        print(f"{label}: {r['correct']}/{r['n']} = {r['accuracy']:.1%} (95% CI {r['ci95'][0]:.1%} to {r['ci95'][1]:.1%}), invalid {r['invalid_outputs']}", flush=True)

    base, tok = ev.load_model(with_adapter=False)
    run("base (zero-shot)", base, tok)
    for adapter in args.adapters:
        # reload a fresh quantised base for each adapter so adapters never stack
        del base
        torch.cuda.empty_cache()
        base, tok = ev.load_model(with_adapter=False)
        model = PeftModel.from_pretrained(base, adapter)
        model.eval()
        run(f"fine-tuned ({Path(adapter).name})", model, tok)
        base = model.unload()
    base_correct = runs[0]["per_item_correct"]
    for r in runs[1:]:
        only_ft = sum(c and not b for c, b in zip(r["per_item_correct"], base_correct))
        only_base = sum(b and not c for c, b in zip(r["per_item_correct"], base_correct))
        r["vs_base"] = {"only_fine_tuned_right": only_ft, "only_base_right": only_base, "mcnemar_p": mcnemar_exact(only_base, only_ft)}
    Path(args.out).write_text(json.dumps({"items": len(items), "runs": runs}, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
