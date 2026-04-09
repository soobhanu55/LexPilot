import argparse
import sys
import time

from ingestion.scraper import scrape_articles
from ingestion.graph_builder import build_graph, save_graph
from ingestion.embedder import run_embedder
import json

def run_pipeline():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scrape-only", action="store_true")
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--skip-embed", action="store_true")
    args = parser.parse_args()

    try:
        if not args.skip_scrape:
            print("=== STEP 1: Scraping EU AI Act ===")
            start_t = time.time()
            scrape_articles(dry_run=False)
            print(f"Scraping completed in {time.time() - start_t:.2f}s")
        else:
            print("=== STEP 1: Skipped ===")

        if args.scrape_only:
            return

        print("=== STEP 2: Building Knowledge Graph ===")
        start_t = time.time()
        with open("ingestion/data/act_chunks.json", "r", encoding="utf-8") as f:
            chunks = json.load(f)
        G = build_graph(chunks)
        save_graph(G, "ingestion/data/act_graph.json")
        print(f"Graph building completed in {time.time() - start_t:.2f}s")

        if not args.skip_embed:
            print("=== STEP 3: Embedding to Qdrant ===")
            start_t = time.time()
            run_embedder()
            print(f"Embedding completed in {time.time() - start_t:.2f}s")
        else:
            print("=== STEP 3: Skipped ===")
            
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
