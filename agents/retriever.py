import time
import json
import asyncio
from qdrant_client.http import models

from agents.state import LexAgentState
from config.settings import settings
from ingestion.graph_builder import load_graph, get_neighbors

# In-memory singletons for graph and chunks
GRAPH = None
CHUNKS_DICT = None

def init_resources():
    global GRAPH, CHUNKS_DICT
    if GRAPH is None:
        try:
            GRAPH = load_graph("ingestion/data/act_graph.json")
        except:
            pass # Graph might not be built yet
    if CHUNKS_DICT is None:
        try:
            with open("ingestion/data/act_chunks.json", "r", encoding="utf-8") as f:
                chunks = json.load(f)
                CHUNKS_DICT = {c["article_id"]: c for c in chunks}
        except:
            pass

async def retrieve_articles(state: LexAgentState) -> LexAgentState:
    start_t = time.time()
    init_resources()
    
    embeddings = settings.get_embeddings()
    q_client = settings.get_async_qdrant_client()
    llm = settings.get_llm()
    
    query = state["user_message"]
    
    candidates = []
    
    # Step 1: Dense Retrieval
    try:
        vector = await embeddings.aembed_query(query)
        search_result = await q_client.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector,
            limit=5,
            score_threshold=0.65
        )
        for hit in search_result:
            candidates.append({
                "article_id": hit.payload["article_id"],
                "title": hit.payload["title"],
                "text": hit.payload["text"],
                "score": hit.score
            })
    except Exception as e:
        state["error"] = f"Dense retrieval failed: {e}"

    # Step 2 & 3: Graph Expansion
    graph_neighbors = set()
    initial_ids = {c["article_id"] for c in candidates}
    
    if GRAPH and CHUNKS_DICT:
        for article_id in initial_ids:
            neighbors = get_neighbors(GRAPH, article_id, depth=2)
            graph_neighbors.update(neighbors)
            
        state["graph_neighbors"] = list(graph_neighbors)
        
        for n_id in graph_neighbors:
            if n_id not in initial_ids and n_id in CHUNKS_DICT:
                chunk = CHUNKS_DICT[n_id]
                candidates.append({
                    "article_id": chunk["article_id"],
                    "title": chunk["title"],
                    "text": chunk.get("text", ""),
                    "score": 0.5 # Default score for graph neighbors
                })
    
    # Step 4: Parallel Re-ranking
    async def rank_candidate(c):
        prompt = f"""Rate relevance of this text to the query from 0-10 (ONLY OUTPUT THE NUMBER, nothing else): 
query={query} 
text={c['text'][:300]}"""
        try:
            res = await llm.ainvoke(prompt)
            c["rerank_score"] = float(res.content.strip())
        except:
            c["rerank_score"] = c["score"] * 10
        return c

    reranked = await asyncio.gather(*[rank_candidate(c) for c in candidates])
        
    reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    top_6 = reranked[:6]
    
    state["retrieved_articles"] = top_6
    
    latency = int((time.time() - start_t) * 1000)
    trace = state.get("agent_trace", [])
    trace.append({
        "agent": "retriever",
        "action": "hybrid_search",
        "input": {"query": query},
        "output": {"retrieved": [c["article_id"] for c in top_6]},
        "latency_ms": latency
    })
    state["agent_trace"] = trace

    return state
