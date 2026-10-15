"""Format retrieved evidence and run a grounded LCEL RAG chain."""

import argparse
import json
import sys
from operator import itemgetter
from pathlib import Path
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from policylens.bm25 import retrieve_bm25
from policylens.llm import LLMClient, get_llm
from policylens.reranker import ABSTENTION_MESSAGE, decide_abstention, rerank

_CANDIDATE_K = 20
_FINAL_K = 5


def format_evidence(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Format usable chunks in retrieval order without changing their text or metadata.

    Missing, non-string, and whitespace-only text is skipped. Source numbers are
    consecutive among included chunks; they are local labels, not document IDs.
    Each included chunk keeps a distinct source, even for the same document/page.
    """
    blocks: list[str] = []
    sources: list[dict[str, Any]] = []

    for chunk in chunks:
        text = chunk.get("text")
        if not isinstance(text, str) or not text.strip():
            continue

        metadata = chunk.get("metadata") or {}
        tag = f"Source {len(sources) + 1}"
        source = {
            "tag": tag,
            "doc_id": metadata.get("doc_id"),
            "chunk_index": metadata.get("chunk_index"),
            "title": metadata.get("title"),
            "source_file": chunk.get("source_file"),
            "page": chunk.get("page"),
            "circular_no": metadata.get("circular_no"),
            "source_url": metadata.get("source_url"),
        }
        lines = [f"[{tag}]"]
        for label, field in (
            ("Document", "title"),
            ("Circular", "circular_no"),
            ("File", "source_file"),
            ("Page", "page"),
            ("URL", "source_url"),
        ):
            value = source[field]
            lines.append(f"{label}: {value if value is not None else 'unavailable'}")
        lines.extend(["Text:", text, f"[End {tag}]"])
        blocks.append("\n".join(lines))
        sources.append(source)

    return {"context": "\n\n".join(blocks), "sources": sources}


def build_rag_chain(k: int = 5, llm: LLMClient | None = None) -> Runnable:
    """Build the frozen BM25-to-reranker chain with one retrieval per invocation.

    Sources stay in invocation-local accepted evidence, never in model output.
    Rejected evidence skips generation; errors propagate.
    The configured client is initialized at construction unless one is supplied.
    """
    if isinstance(k, bool) or not isinstance(k, int) or k != _FINAL_K:
        raise ValueError("The frozen RAG pipeline requires final k=5")
    client = llm if llm is not None else get_llm()
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "answer_v1.txt"
    prompt_text = prompt_path.read_text(encoding="utf-8")
    system_text, human_text = prompt_text.split("END SYSTEM INSTRUCTIONS", maxsplit=1)
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_text.strip()), ("human", human_text.strip())]
    )
    generate_answer = (
        RunnablePassthrough.assign(
            sources=RunnableLambda(
                lambda evidence: json.dumps(evidence["sources"], ensure_ascii=False, indent=2)
            )
        )
        | prompt
        | RunnableLambda(
            lambda prompt_value: client.generate(prompt_value.to_string(), temperature=0)
        )
        | StrOutputParser()
    )
    answer = RunnableBranch(
        (
            lambda evidence: evidence["abstained"],
            RunnableLambda(lambda _: ABSTENTION_MESSAGE),
        ),
        generate_answer,
    )

    def prepare_evidence(state: dict[str, Any]) -> dict[str, Any]:
        decision = decide_abstention(state["chunks"])
        if decision["abstain"]:
            return {"question": state["question"], "context": "", "sources": [], "abstained": True}
        return {
            "question": state["question"],
            **format_evidence(state["chunks"]),
            "abstained": False,
        }

    def retrieve_and_rerank(question: str) -> list[dict[str, Any]]:
        candidates = retrieve_bm25(question, k=_CANDIDATE_K)
        return rerank(question, candidates, k=_FINAL_K)

    return (
        RunnableParallel(
            question=RunnablePassthrough(),
            chunks=RunnableLambda(retrieve_and_rerank),
        )
        | RunnableLambda(prepare_evidence)
        | RunnableParallel(
            answer=answer,
            sources=RunnableLambda(itemgetter("sources")),
            abstained=RunnableLambda(itemgetter("abstained")),
        )
    )


def main() -> None:
    """Answer a question using the configured chain and print its returned sources."""
    parser = argparse.ArgumentParser(description="PolicyLens grounded RAG")
    parser.add_argument("--query", required=True, help="Question to answer")
    parser.add_argument("--k", type=int, default=5, help="Final evidence depth (fixed at 5)")
    args = parser.parse_args()
    if not args.query.strip():
        parser.error("--query must not be empty or whitespace-only")
    if args.k != _FINAL_K:
        parser.error("--k must be 5 for the frozen RAG pipeline")

    try:
        result = build_rag_chain(k=args.k).invoke(args.query)
    except Exception as exc:
        # SDK error messages can contain credentials or request details; do not echo them.
        failure = type(exc).__name__
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int) and 400 <= status_code <= 599:
            failure += f" (HTTP {status_code})"
        print(
            "RAG error: could not complete retrieval or inference. "
            "Check LLM configuration, credentials, and retrieval/API connectivity. "
            f"Failure: {failure}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    print("Answer:")
    print(result["answer"])
    print("\nSources:")
    if not result["sources"]:
        print("No sources.")
    for source in result["sources"]:
        print(f"[{source['tag']}]")
        for label, field in (("File", "source_file"), ("Page", "page")):
            value = source[field]
            print(f"  {label}: {value if value is not None else 'unavailable'}")
        for label, field in (
            ("Document", "title"),
            ("Document ID", "doc_id"),
            ("Chunk index", "chunk_index"),
            ("Circular", "circular_no"),
            ("URL", "source_url"),
        ):
            value = source[field]
            if value is not None:
                print(f"  {label}: {value}")


if __name__ == "__main__":
    main()
