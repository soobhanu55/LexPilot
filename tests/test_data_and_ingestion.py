"""Training/eval data hygiene, evaluation statistics, and the ingestion graph (no models, no network)."""
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

from ingestion import graph_builder, scraper

ROOT = Path(__file__).resolve().parent.parent
TIERS = {"prohibited", "high-risk", "limited-risk", "minimal-risk"}


def jsonl(path):
    return [json.loads(line) for line in (ROOT / path).read_text(encoding="utf-8").splitlines() if line.strip()]


# --- data hygiene -----------------------------------------------------------------------------------

def test_training_completions_are_valid_json_with_known_tiers():
    for row in jsonl("finetune/data/train.jsonl") + jsonl("finetune/data/val.jsonl"):
        assert json.loads(row["completion"])["tier"] in TIERS


def test_training_data_covers_all_tiers_roughly_evenly():
    counts = Counter(json.loads(r["completion"])["tier"] for r in jsonl("finetune/data/train.jsonl"))
    assert set(counts) == TIERS and min(counts.values()) >= 0.15 * sum(counts.values())


def test_eval_set_is_well_formed_and_balanced():
    items = jsonl("finetune/eval_set.jsonl")
    assert len(items) == 60 and len({i["id"] for i in items}) == 60
    assert Counter(i["tier"] for i in items) == {t: 15 for t in TIERS}
    assert sum(i["lang"] == "de" for i in items) == 8 and all(i["basis"] and i["text"] for i in items)


def test_eval_set_is_disjoint_from_training_and_the_six_question_set():
    seen = {r["prompt"].lower() for r in jsonl("finetune/data/train.jsonl") + jsonl("finetune/data/val.jsonl")}
    seen |= {t["question"].lower() for t in json.loads((ROOT / "evals/ground_truth.json").read_text(encoding="utf-8"))}
    for item in jsonl("finetune/eval_set.jsonl"):
        text = item["text"].lower()
        assert not any(text in s or s in text for s in seen), item["text"]


# --- evaluation statistics ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def evaluate_set():
    spec = importlib.util.spec_from_file_location("evaluate_set", ROOT / "finetune" / "evaluate_set.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tier_normalisation_is_strict(evaluate_set):
    n = evaluate_set.normalise
    assert n("High Risk") == "high-risk" and n("minimal_risk") == "minimal-risk" and n(" prohibited ") == "prohibited"
    assert n("minimallimitedrisk") == "invalid" and n("unknown") == "invalid" and n(None) == "invalid"


def test_wilson_interval_properties(evaluate_set):
    lo, hi = evaluate_set.wilson(30, 60)
    assert lo < 0.5 < hi and 0.37 < lo < 0.39 and 0.61 < hi < 0.63
    lo, hi = evaluate_set.wilson(60, 60)
    assert hi == pytest.approx(1.0) and lo > 0.93


def test_mcnemar_known_value(evaluate_set):
    assert evaluate_set.mcnemar_exact(10, 2) == pytest.approx(158 / 4096)
    assert evaluate_set.mcnemar_exact(0, 0) == 1.0


def test_summarise_counts_and_recall(evaluate_set):
    items = [{"tier": "high-risk"}, {"tier": "high-risk"}, {"tier": "minimal-risk"}, {"tier": "prohibited"}]
    r = evaluate_set.summarise("m", items, ["high-risk", "minimal-risk", "minimal-risk", "garbage"])
    assert r["correct"] == 2 and r["invalid_outputs"] == 1
    assert r["recall"]["high-risk"] == 0.5 and r["recall"]["minimal-risk"] == 1.0 and r["recall"]["prohibited"] == 0.0
    assert r["confusion"]["high-risk"] == {"high-risk": 1, "minimal-risk": 1}


# --- ingestion ---------------------------------------------------------------------------------------------

CHUNKS = [
    {"article_id": "Article 6", "title": "t", "text": "x", "cross_references": ["Article 9", "Article 6"]},
    {"article_id": "Article 9", "title": "t", "text": "x", "cross_references": []},
    {"article_id": "Article 10", "title": "t", "text": "x", "cross_references": []},
    {"article_id": "Article 17", "title": "t", "text": "x", "cross_references": []},
]


def test_graph_has_reference_semantic_and_requirement_edges():
    g = graph_builder.build_graph(CHUNKS)
    assert g.has_edge("Article 6", "Article 9") and not g.has_edge("Article 6", "Article 6")
    assert g.has_edge("Article 9", "Article 17") and g.has_edge("Article 10", "Article 17")  # 9-15 -> 17 requirement edges
    assert "text" not in g.nodes["Article 6"]


def test_neighbours_respect_depth_and_exclude_self():
    g = graph_builder.build_graph(CHUNKS)
    one = set(graph_builder.get_neighbors(g, "Article 6", depth=1))
    two = set(graph_builder.get_neighbors(g, "Article 6", depth=2))
    assert "Article 6" not in two and "Article 9" in one and "Article 17" in two
    assert graph_builder.get_neighbors(g, "Article 999") == []


def test_graph_roundtrips_through_json(tmp_path):
    g = graph_builder.build_graph(CHUNKS)
    path = tmp_path / "g.json"
    graph_builder.save_graph(g, str(path))
    assert set(graph_builder.load_graph(str(path)).edges) == set(g.edges)


def test_shipped_graph_links_high_risk_article_to_its_requirements():
    g = graph_builder.load_graph(str(ROOT / "ingestion/data/act_graph.json"))
    assert {"Article 9", "Article 15"} <= set(g.successors("Article 6"))


def test_scraper_extracts_cross_references_and_keywords():
    refs = scraper.extract_cross_references("See article 12 and Annex iii; recital 4 too. Article 12 again.")
    assert sorted(refs) == ["Annex Iii", "Article 12", "Recital 4"]
    assert scraper.extract_keywords("The provider of a High-Risk system must run a conformity assessment.") == \
        ["high-risk", "conformity assessment", "provider"]
