"""Offline tests for development-only dense and BM25 evaluation."""

import json
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from eval import run_retrieval


@pytest.fixture
def evaluation_data(tmp_path, monkeypatch):
    def record(question_id, question_type, sources):
        return {
            "id": question_id,
            "question": question_id,
            "type": question_type,
            "gold_sources": sources,
            "reference_answer": "reference",
            "answerable": bool(sources),
            "verified": True,
        }

    def source(question_id, page=1):
        return {"doc_id": question_id, "page": page}

    holdout_ids = [f"H{number:02}" for number in range(1, 13)]
    records = [record(question_id, "factoid", [source(question_id)]) for question_id in holdout_ids]
    records += [
        record("D01", "factoid", [source("D01")]),
        record("D02", "factoid", [source("D02")]),
        record("D03", "multi-section", [source("D03"), source("D03", 2)]),
        record("D04", "table_lookup", [source("D04")]),
        record("D05", "date_version", [source("D05")]),
        record("D06", "unanswerable", []),
    ]
    golden_path = tmp_path / "golden.jsonl"
    golden_path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
    holdout_path = tmp_path / "holdout_ids.txt"
    holdout_path.write_text("\n".join(holdout_ids) + "\n", encoding="utf-8")
    monkeypatch.setattr(run_retrieval, "GOLDEN_PATH", golden_path)
    monkeypatch.setattr(run_retrieval, "HOLDOUT_PATH", holdout_path)
    monkeypatch.setattr(run_retrieval, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(
        run_retrieval,
        "get_settings",
        lambda: SimpleNamespace(
            embedding_model="BAAI/bge-small-en-v1.5",
            qdrant_collection="policylens_chunks",
            bm25_collection="policylens_bm25",
        ),
    )

    def result(question_id, page=1):
        return {"metadata": source(question_id, page)}

    responses = {
        "D01": [result("D01")],
        "D02": [],
        "D03": [result("other"), result("D03")],
        "D04": [result("D04")],
        "D05": [result("other"), result("D05")],
    }
    dense = Mock(side_effect=lambda question, k: responses[question])
    bm25 = Mock(side_effect=lambda question, k: responses[question])
    monkeypatch.setattr(run_retrieval, "retrieve", dense)
    monkeypatch.setattr(run_retrieval, "retrieve_bm25", bm25)
    return dense, bm25


def test_method_selection_and_frozen_holdout_exclusion(evaluation_data):
    dense, bm25 = evaluation_data

    dense_report = run_retrieval.evaluate(5)
    bm25_report = run_retrieval.evaluate(5, method="bm25")

    expected = [call(question_id, k=5) for question_id in ("D01", "D02", "D03", "D04", "D05")]
    assert dense.call_args_list == expected
    assert bm25.call_args_list == expected
    assert dense_report["method"] == "dense"
    assert dense_report["configuration"] == {
        "k": 5,
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "qdrant_collection": "policylens_chunks",
    }
    assert dense_report["configuration_hash"] == (
        "af6558ebe4a5bce1f853b19340b8acdfe77ea87db78f6dd033f4fb3c73a9c58f"
    )
    assert bm25_report["configuration"] == {
        "method": "bm25",
        "k": 5,
        "qdrant_collection": "policylens_bm25",
        "bm25_model": "qdrant/bm25",
        "sparse_vector": "bm25",
        "modifier": "idf",
    }
    assert bm25_report["configuration_hash"] != dense_report["configuration_hash"]
    assert bm25_report["counts"] == {
        "golden_questions": 18,
        "holdout_questions": 12,
        "development_questions": 6,
        "answerable_evaluated": 5,
        "unanswerable_excluded": 1,
    }


def test_bm25_overall_and_question_type_metrics(evaluation_data):
    report = run_retrieval.evaluate(5, method="bm25")

    assert report["metrics"] == {"hit_at_k": 0.8, "recall_at_k": 0.7, "mrr": 0.6}
    assert report["metrics_by_type"] == {
        "factoid": {"count": 2, "hit_at_k": 0.5, "recall_at_k": 0.5, "mrr": 0.5},
        "multi-section": {"count": 1, "hit_at_k": 1.0, "recall_at_k": 0.5, "mrr": 0.5},
        "table_lookup": {"count": 1, "hit_at_k": 1.0, "recall_at_k": 1.0, "mrr": 1.0},
        "date_version": {"count": 1, "hit_at_k": 1.0, "recall_at_k": 1.0, "mrr": 0.5},
    }
    assert [row["id"] for row in report["per_question"]] == ["D01", "D02", "D03", "D04", "D05"]
    assert report["per_question"][2] == {
        "id": "D03",
        "type": "multi-section",
        "hit_at_k": 1.0,
        "recall_at_k": 0.5,
        "reciprocal_rank": 0.5,
    }


def test_cli_writes_separate_bm25_json_without_touching_dense_report(
    evaluation_data, monkeypatch, capsys
):
    baseline = run_retrieval.RESULTS_DIR / "retrieval_existing_dense_baseline.json"
    baseline.parent.mkdir(parents=True)
    baseline.write_text("existing baseline\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["run_retrieval", "--method", "bm25", "--k", "5"])

    run_retrieval.main()

    reports = list(run_retrieval.RESULTS_DIR.glob("retrieval_bm25_*.json"))
    assert len(reports) == 1
    saved = json.loads(reports[0].read_text(encoding="utf-8"))
    assert saved["method"] == "bm25"
    assert saved["metrics"]["hit_at_k"] == 0.8
    assert len(saved["per_question"]) == 5
    assert baseline.read_text(encoding="utf-8") == "existing baseline\n"
    output = capsys.readouterr().out
    assert "method=bm25" in output
    assert "By question type:" in output
    assert "multi-section" in output


def test_existing_dense_report_shape_keeps_dense_filename(evaluation_data):
    report = run_retrieval.evaluate(5)
    report.pop("method")

    path = run_retrieval.save_results(report)

    assert path.name.startswith("retrieval_")
    assert not path.name.startswith("retrieval_bm25_")


def test_invalid_method_is_rejected_before_retrieval(evaluation_data):
    dense, bm25 = evaluation_data

    with pytest.raises(ValueError, match="method must be"):
        run_retrieval.evaluate(5, method="hybrid")

    dense.assert_not_called()
    bm25.assert_not_called()
