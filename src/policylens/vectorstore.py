"""Qdrant vector store management, batch embedding, and point upsertion.

Provides collection initialization with dense and sparse named vectors,
deterministic UUIDv5 point IDs for idempotent ingestion, and batch embedding.
"""

import uuid
from typing import Any

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from policylens.config import get_settings
from policylens.ingestion.chunker import Chunk
from policylens.llm import get_embeddings


def get_qdrant_client(
    url: str | None = None,
    api_key: str | None = None,
) -> QdrantClient:
    """Instantiate a Qdrant client driven by configuration or parameters."""
    settings = get_settings()
    target_url = url or settings.qdrant_url
    target_key = (
        api_key
        if api_key is not None
        else (settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None)
    )
    return QdrantClient(url=target_url, api_key=target_key)


def get_embedding_dimension(embedder: SentenceTransformer) -> int:
    """Retrieve vector dimension dynamically from the embedding model."""
    dim = embedder.get_embedding_dimension()
    if dim is None:
        raise ValueError("Unable to determine embedding dimension from model.")
    return int(dim)


def generate_point_id(doc_id: str, chunk_index: int) -> str:
    """Generate a deterministic UUIDv5 point ID from document ID and chunk index."""
    key = f"{doc_id}:{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))


def init_collection(
    client: QdrantClient | None = None,
    collection_name: str | None = None,
    embedder: SentenceTransformer | None = None,
) -> None:
    """Initialize Qdrant collection with named dense and sparse vectors and payload indexes."""
    settings = get_settings()
    q_client = client or get_qdrant_client()
    c_name = collection_name or settings.qdrant_collection
    model = embedder or get_embeddings()

    if not q_client.collection_exists(c_name):
        dim = get_embedding_dimension(model)
        q_client.create_collection(
            collection_name=c_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=dim,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={"sparse": models.SparseVectorParams()},
        )

        payload_fields = ["regulator", "issue_date", "status", "access_level"]
        for field in payload_fields:
            q_client.create_payload_index(
                collection_name=c_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )


def embed_chunks(
    chunks: list[Chunk],
    embedder: SentenceTransformer | None = None,
    batch_size: int | None = None,
) -> list[list[float]]:
    """Generate normalized dense embeddings for chunks in batches."""
    if not chunks:
        return []

    settings = get_settings()
    model = embedder or get_embeddings()
    b_size = batch_size or settings.embedding_batch_size
    texts = [c.text for c in chunks]

    embeddings = model.encode(
        texts,
        batch_size=b_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [vec.tolist() for vec in embeddings]


def upsert_chunks(
    chunks: list[Chunk],
    client: QdrantClient | None = None,
    collection_name: str | None = None,
    embedder: SentenceTransformer | None = None,
    batch_size: int | None = None,
) -> int:
    """Embed and upsert chunks into Qdrant using deterministic point IDs and batching."""
    if not chunks:
        return 0

    settings = get_settings()
    q_client = client or get_qdrant_client()
    c_name = collection_name or settings.qdrant_collection
    model = embedder or get_embeddings()
    b_size = batch_size or settings.embedding_batch_size

    init_collection(client=q_client, collection_name=c_name, embedder=model)

    vectors = embed_chunks(chunks, embedder=model, batch_size=b_size)

    points: list[models.PointStruct] = []
    for chunk, vec in zip(chunks, vectors, strict=True):
        meta = chunk.to_metadata().model_dump()
        point_id = generate_point_id(doc_id=meta["doc_id"], chunk_index=meta["chunk_index"])
        payload: dict[str, Any] = {
            "text": chunk.text,
            **meta,
        }
        points.append(
            models.PointStruct(
                id=point_id,
                vector={"dense": vec},
                payload=payload,
            )
        )

    for i in range(0, len(points), b_size):
        batch = points[i : i + b_size]
        q_client.upsert(collection_name=c_name, points=batch)

    return len(points)


def search_chunks(
    query: str,
    client: QdrantClient | None = None,
    collection_name: str | None = None,
    embedder: SentenceTransformer | None = None,
    limit: int = 5,
) -> list[models.ScoredPoint]:
    """Execute a dense vector search query against the Qdrant collection."""
    settings = get_settings()
    q_client = client or get_qdrant_client()
    c_name = collection_name or settings.qdrant_collection
    model = embedder or get_embeddings()

    query_vector = model.encode(query, normalize_embeddings=True).tolist()
    res = q_client.query_points(
        collection_name=c_name,
        query=query_vector,
        using="dense",
        limit=limit,
    )
    return res.points
