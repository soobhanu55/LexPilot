import json
import uuid
import time
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from config.settings import settings

def run_embedder():
    embeddings = settings.get_embeddings()
    q_client = settings.get_qdrant_client()
    collection_name = settings.qdrant_collection

    print(f"Checking if collection '{collection_name}' exists...")
    try:
        q_client.get_collection(collection_name)
    except (UnexpectedResponse, Exception) as e:
        print(f"Creating collection '{collection_name}'...")
        q_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=768,  # nomic-embed-text size
                distance=models.Distance.COSINE
            )
        )

    with open("ingestion/data/act_chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)

    batch_size = 20
    points = []
    
    print(f"Embedding {len(chunks)} chunks...")
    for i, chunk in enumerate(chunks):
        text_content = f"{chunk.get('title', '')}\n\n{chunk.get('text', '')}"
        text_content = text_content[:2000]  # truncate
        
        # UUID5 for deterministic IDs
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["article_id"]))
        
        vector = embeddings.embed_query(text_content)
        
        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=chunk
            )
        )

        if len(points) >= batch_size or i == len(chunks) - 1:
            # Batch upsert with retry
            attempts = 3
            for attempt in range(attempts):
                try:
                    q_client.upsert(
                        collection_name=collection_name,
                        points=points
                    )
                    print(f"Upserted batch ending at index {i}")
                    points = []
                    break
                except Exception as e:
                    if attempt < attempts - 1:
                        print(f"Qdrant upsert failed: {e}. Retrying in 2 seconds...")
                        time.sleep(2)
                    else:
                        print(f"Failed to upsert batch after {attempts} attempts. Exiting.")
                        raise e

if __name__ == "__main__":
    run_embedder()
