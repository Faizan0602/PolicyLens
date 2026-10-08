"""Naive dense retrieval and a terminal demonstration using the existing vector store."""

import argparse
import sys
from typing import Any

from policylens.ingestion.metadata import ChunkMetadata
from policylens.vectorstore import search_chunks


def retrieve(query: str, k: int = 5) -> list[dict[str, Any]]:
    """Return up to k chunks, preserving Qdrant ranking, scores, and available metadata."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not query.strip():
        raise ValueError("query must not be empty or whitespace-only")
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer, excluding booleans")
    if k <= 0:
        raise ValueError("k must be greater than zero")

    results: list[dict[str, Any]] = []
    for point in search_chunks(query=query, limit=k):
        payload = point.payload or {}
        results.append(
            {
                "text": payload.get("text"),
                "score": point.score,
                "source_file": payload.get("source_file"),
                "page": payload.get("page"),
                "metadata": {
                    field: payload[field]
                    for field in ChunkMetadata.model_fields
                    if field in payload
                },
            }
        )
    return results


def print_results(results: list[dict[str, Any]]) -> None:
    """Print evidence for manual inspection; scores do not classify relevance."""
    if not results:
        print("No results.")
        return

    for rank, result in enumerate(results, start=1):
        print(f"Rank {rank} | Similarity score: {result['score']:.6f}")
        source = result["source_file"]
        page = result["page"]
        print(f"Source document: {source if source is not None else 'unavailable'}")
        print(f"Page: {page if page is not None else 'unavailable'}")
        print("Metadata:")
        if not result["metadata"]:
            print("  unavailable")
        for field, value in result["metadata"].items():
            print(f"  {field}: {value if value is not None else 'unavailable'}")
        print("Chunk text:")
        text = result["text"]
        print(text if text is not None else "unavailable")
        print()


def main() -> None:
    """Run read-only retrieval against the configured existing collection."""
    parser = argparse.ArgumentParser(description="PolicyLens naive dense retrieval")
    parser.add_argument("--query", required=True, help="Question to search for")
    parser.add_argument("--k", type=int, default=5, help="Maximum chunks to return (default: 5)")
    args = parser.parse_args()
    try:
        print_results(retrieve(args.query, args.k))
    except Exception as exc:
        print(f"Retrieval error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
