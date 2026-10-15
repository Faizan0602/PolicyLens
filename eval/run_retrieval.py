"""Evaluate dense, BM25, or hybrid retrieval on verified development questions only."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from policylens.bm25 import retrieve_bm25
from policylens.config import get_settings
from policylens.hybrid import retrieve_hybrid
from policylens.retrieval import retrieve

if __package__:
    from .metrics import hit_at_k, recall_at_k, reciprocal_rank
else:
    from metrics import hit_at_k, recall_at_k, reciprocal_rank

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "data" / "eval" / "golden.jsonl"
HOLDOUT_PATH = ROOT / "data" / "eval" / "holdout_ids.txt"
RESULTS_DIR = ROOT / "eval" / "results"
REQUIRED_FIELDS = {
    "id",
    "question",
    "type",
    "gold_sources",
    "reference_answer",
    "answerable",
    "verified",
}


def load_golden() -> list[dict[str, Any]]:
    """Read and validate the golden JSONL before any retrieval calls."""
    if not GOLDEN_PATH.is_file():
        raise FileNotFoundError(f"Golden dataset not found: {GOLDEN_PATH}")

    records = []
    seen_ids = set()
    for line_number, line in enumerate(GOLDEN_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank golden record at line {line_number}")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid golden JSON at line {line_number}: {exc.msg}") from exc
        if not isinstance(record, dict) or set(record) != REQUIRED_FIELDS:
            raise ValueError(f"Invalid golden fields at line {line_number}")
        if not isinstance(record["id"], str) or not record["id"].strip():
            raise ValueError(f"Invalid golden ID at line {line_number}")
        if record["id"] in seen_ids:
            raise ValueError(f"Duplicate golden ID: {record['id']}")
        if not isinstance(record["question"], str) or not record["question"].strip():
            raise ValueError(f"Invalid question for {record['id']}")
        if not isinstance(record["type"], str) or not isinstance(record["reference_answer"], str):
            raise ValueError(f"Invalid type or reference answer for {record['id']}")
        if type(record["answerable"]) is not bool or type(record["verified"]) is not bool:
            raise ValueError(f"Invalid answerable or verified flag for {record['id']}")
        sources = record["gold_sources"]
        if not isinstance(sources, list) or record["answerable"] != bool(sources):
            raise ValueError(f"Invalid gold_sources for {record['id']}")
        for source in sources:
            if (
                not isinstance(source, dict)
                or set(source) != {"doc_id", "page"}
                or not isinstance(source["doc_id"], str)
                or not source["doc_id"].strip()
                or type(source["page"]) is not int
                or source["page"] < 1
            ):
                raise ValueError(f"Invalid gold source for {record['id']}")
        seen_ids.add(record["id"])
        records.append(record)

    if not records:
        raise ValueError("Golden dataset is empty")
    return records


def load_holdout(golden_ids: set[str]) -> set[str]:
    """Validate the frozen twelve-question hold-out split."""
    if not HOLDOUT_PATH.is_file():
        raise FileNotFoundError(f"Hold-out IDs not found: {HOLDOUT_PATH}")
    ids = HOLDOUT_PATH.read_text(encoding="utf-8").splitlines()
    if len(ids) != 12 or any(not item or item != item.strip() for item in ids):
        raise ValueError("Hold-out file must contain exactly 12 nonblank IDs, one per line")
    if len(set(ids)) != len(ids):
        raise ValueError("Hold-out IDs must be unique")
    unknown = set(ids) - golden_ids
    if unknown:
        raise ValueError(f"Hold-out IDs missing from golden dataset: {', '.join(sorted(unknown))}")
    return set(ids)


def _average_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    count = len(rows)
    return {
        "hit_at_k": sum(row["hit_at_k"] for row in rows) / count,
        "recall_at_k": sum(row["recall_at_k"] for row in rows) / count,
        "mrr": sum(row["reciprocal_rank"] for row in rows) / count,
    }


def evaluate(k: int, method: str = "dense") -> dict[str, Any]:
    """Run one ordered development-only retrieval evaluation."""
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer")
    if method not in ("dense", "bm25", "hybrid"):
        raise ValueError("method must be 'dense', 'bm25', or 'hybrid'")
    if method == "hybrid" and k > 5:
        raise ValueError("hybrid k must not exceed candidate_k=5")
    golden = load_golden()
    holdout_ids = load_holdout({record["id"] for record in golden})
    development = [record for record in golden if record["id"] not in holdout_ids]
    eligible = [record for record in development if record["answerable"]]
    if not eligible:
        raise ValueError("No answerable development questions to evaluate")
    if any(record["verified"] is not True for record in eligible):
        raise ValueError("All evaluated questions must have verified=true")

    settings = get_settings()
    retrieval_kwargs = {"k": k}
    if method == "dense":
        configuration = {
            "k": k,
            "embedding_model": settings.embedding_model,
            "qdrant_collection": settings.qdrant_collection,
        }
        retriever = retrieve
    elif method == "bm25":
        configuration = {
            "method": "bm25",
            "k": k,
            "qdrant_collection": settings.bm25_collection,
            "bm25_model": "qdrant/bm25",
            "sparse_vector": "bm25",
            "modifier": "idf",
        }
        retriever = retrieve_bm25
    else:
        configuration = {
            "method": "hybrid",
            "k": k,
            "candidate_k": 5,
            "qdrant_collection": settings.hybrid_collection,
            "embedding_model": settings.embedding_model,
            "bm25_model": "qdrant/bm25",
            "dense_vector": "dense",
            "sparse_vector": "bm25",
            "modifier": "idf",
            "rrf_smoothing": 60,
            "rrf_k": 61,
        }
        retriever = retrieve_hybrid
        retrieval_kwargs["candidate_k"] = 5
    canonical = json.dumps(configuration, sort_keys=True, separators=(",", ":"))
    configuration_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    per_question = []
    for record in eligible:
        results = retriever(record["question"], **retrieval_kwargs)
        sources = record["gold_sources"]
        per_question.append(
            {
                "id": record["id"],
                "type": record["type"],
                "hit_at_k": hit_at_k(results, sources, k),
                "recall_at_k": recall_at_k(results, sources, k),
                "reciprocal_rank": reciprocal_rank(results, sources, k),
            }
        )

    count = len(per_question)
    metrics_by_type = {}
    for question_type in dict.fromkeys(row["type"] for row in per_question):
        rows = [row for row in per_question if row["type"] == question_type]
        metrics_by_type[question_type] = {"count": len(rows), **_average_metrics(rows)}
    now = datetime.now(timezone.utc)
    return {
        "timestamp_utc": now.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "method": method,
        "configuration_hash": configuration_hash,
        "configuration": configuration,
        "counts": {
            "golden_questions": len(golden),
            "holdout_questions": len(holdout_ids),
            "development_questions": len(development),
            "answerable_evaluated": count,
            "unanswerable_excluded": len(development) - count,
        },
        "metrics": _average_metrics(per_question),
        "metrics_by_type": metrics_by_type,
        "per_question": per_question,
    }


def save_results(report: dict[str, Any]) -> Path:
    """Create the results directory only after evaluation has completed."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = report["timestamp_utc"].replace("-", "").replace(":", "").replace(".", "")
    method = report.get("method", "dense")
    prefix = f"retrieval_{method}" if method in ("bm25", "hybrid") else "retrieval"
    path = RESULTS_DIR / f"{prefix}_{timestamp}_{report['configuration_hash']}.json"
    with path.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, ensure_ascii=False)
        output.write("\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval on development questions")
    parser.add_argument("--k", type=int, default=5, help="Number of retrieved chunks (default: 5)")
    parser.add_argument("--method", choices=("dense", "bm25", "hybrid"), default="dense")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("--k must be a positive integer")
    if args.method == "hybrid" and args.k > 5:
        parser.error("hybrid --k must not exceed candidate_k=5")

    report = evaluate(args.k, method=args.method)
    output_path = save_results(report)
    config = report["configuration"]
    counts = report["counts"]
    metrics = report["metrics"]
    if args.method == "dense":
        configuration_text = (
            f"k={config['k']}, embedding_model={config['embedding_model']}, "
            f"qdrant_collection={config['qdrant_collection']}"
        )
    elif args.method == "bm25":
        configuration_text = (
            f"method=bm25, k={config['k']}, bm25_model={config['bm25_model']}, "
            f"qdrant_collection={config['qdrant_collection']}, vector={config['sparse_vector']}"
        )
    else:
        configuration_text = (
            f"method=hybrid, k={config['k']}, candidate_k={config['candidate_k']}, "
            f"qdrant_collection={config['qdrant_collection']}, "
            f"embedding_model={config['embedding_model']}, bm25_model={config['bm25_model']}, "
            f"rrf_k={config['rrf_k']}"
        )
    rows = [
        ("Configuration", configuration_text),
        ("Development questions", counts["development_questions"]),
        ("Answerable evaluated", counts["answerable_evaluated"]),
        ("Unanswerable excluded", counts["unanswerable_excluded"]),
        (f"Hit@{args.k}", f"{metrics['hit_at_k']:.4f}"),
        (f"Recall@{args.k}", f"{metrics['recall_at_k']:.4f}"),
        ("MRR", f"{metrics['mrr']:.4f}"),
    ]
    print(f"{'Retrieval evaluation':<24} Value")
    for label, value in rows:
        print(f"{label:<24} {value}")
    print("By question type:")
    print(f"{'Type':<16} {'Count':>5} {f'Hit@{args.k}':>8} {f'Recall@{args.k}':>10} {'MRR':>8}")
    for question_type, values in report["metrics_by_type"].items():
        print(
            f"{question_type:<16} {values['count']:>5} "
            f"{values['hit_at_k']:>8.4f} {values['recall_at_k']:>10.4f} "
            f"{values['mrr']:>8.4f}"
        )
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
