import json
import networkx as nx
from networkx.readwrite import json_graph

def build_graph(chunks: list[dict]) -> nx.DiGraph:
    G = nx.DiGraph()

    # Add nodes
    for chunk in chunks:
        node_id = chunk["article_id"]
        # Make a copy without 'text'
        attrs = {k: v for k, v in chunk.items() if k != "text"}
        G.add_node(node_id, **attrs)

    # Add extracted edges
    for chunk in chunks:
        src = chunk["article_id"]
        for target in chunk.get("cross_references", []):
            if target != src:
                G.add_edge(src, target, type="references")

    # Add semantic edges manually
    semantic_edges_map = {
        "Article 6": ["Article 9", "Article 10", "Article 11", "Article 12", "Article 13", "Article 14", "Article 15"],
        "Article 5": ["Article 6"],
        "Article 99": ["Article 5", "Article 6"]
    }
    
    # 9-15 to 17
    for i in range(9, 16):
        if f"Article {i}" in G.nodes:
            G.add_edge(f"Article {i}", "Article 17", type="semantic_requirement")

    for src, targets in semantic_edges_map.items():
        for t in targets:
            G.add_edge(src, t, type="semantic")

    return G

def get_neighbors(graph: nx.DiGraph, article_id: str, depth: int = 2) -> list[str]:
    if article_id not in graph:
        return []
    
    neighbors = set()
    current_level = {article_id}
    
    for _ in range(depth):
        next_level = set()
        for node in current_level:
            # We want both incoming and outgoing for cross-references
            next_level.update(graph.successors(node))
            next_level.update(graph.predecessors(node))
        neighbors.update(next_level)
        current_level = next_level
        
    if article_id in neighbors:
        neighbors.remove(article_id)
    return list(neighbors)

def save_graph(graph: nx.DiGraph, path: str):
    data = json_graph.node_link_data(graph)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_graph(path: str) -> nx.DiGraph:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return json_graph.node_link_graph(data)

if __name__ == "__main__":
    with open("ingestion/data/act_chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    G = build_graph(chunks)
    print(f"Built graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    save_graph(G, "ingestion/data/act_graph.json")
