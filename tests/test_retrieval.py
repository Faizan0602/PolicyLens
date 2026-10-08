"""Deterministic tests of the dense retrieval wrapper and terminal output."""

from unittest.mock import Mock

import pytest
from qdrant_client.models import ScoredPoint

from policylens import retrieval
from policylens.ingestion.metadata import ChunkMetadata


@pytest.fixture
def search(monkeypatch):
    mock = Mock(return_value=[])
    monkeypatch.setattr(retrieval, "search_chunks", mock)
    return mock


@pytest.mark.parametrize("query", [None, 123, True, ["question"]])
def test_non_string_query(query, search):
    with pytest.raises(TypeError, match="query must be a string"):
        retrieval.retrieve(query)
    search.assert_not_called()


@pytest.mark.parametrize("query", ["", " ", "\n\t"])
def test_blank_query(query, search):
    with pytest.raises(ValueError, match="query must not be empty"):
        retrieval.retrieve(query)
    search.assert_not_called()


@pytest.mark.parametrize("k", [None, "5", 5.0, True, False])
def test_non_integer_k(k, search):
    with pytest.raises(TypeError, match="k must be an integer"):
        retrieval.retrieve("question", k)
    search.assert_not_called()


@pytest.mark.parametrize("k", [0, -1])
def test_non_positive_k(k, search):
    with pytest.raises(ValueError, match="k must be greater than zero"):
        retrieval.retrieve("question", k)
    search.assert_not_called()


@pytest.mark.parametrize("k", [1, 3, 5])
def test_delegation_and_empty_results(k, search):
    assert retrieval.retrieve(" question ", k) == []
    search.assert_called_once_with(query=" question ", limit=k)


def test_default_k(search):
    assert retrieval.retrieve("question") == []
    search.assert_called_once_with(query="question", limit=5)


def test_result_mapping_preserves_order_scores_and_metadata(search):
    metadata = {
        "doc_id": "document-id",
        "title": "Test circular",
        "regulator": "RBI",
        "circular_no": "RBI/test",
        "issue_date": "Oct 01, 2026",
        "effective_date": None,
        "status": None,
        "supersedes": ["previous-circular"],
        "section": "1. Scope",
        "page": 2,
        "access_level": "public",
        "source_url": "https://example.com/circular",
        "content_hash": "chunk-hash",
        "chunk_index": 1,
    }
    assert set(metadata) == set(ChunkMetadata.model_fields)
    payload = {"text": "Actual chunk text", "source_file": "test.pdf", **metadata, "extra": 42}
    # Deliberately use ascending scores to detect any wrapper re-sorting.
    search.return_value = [
        ScoredPoint(id=2, version=1, score=0.123456789, payload=payload),
        ScoredPoint(id=1, version=1, score=0.9, payload={"text": "Second chunk"}),
    ]
    results = retrieval.retrieve("question", 2)
    assert results[0] == {
        "text": "Actual chunk text",
        "score": 0.123456789,
        "source_file": "test.pdf",
        "page": 2,
        "metadata": metadata,
    }
    assert [result["text"] for result in results] == ["Actual chunk text", "Second chunk"]
    assert [result["score"] for result in results] == [0.123456789, 0.9]
    assert payload["extra"] == 42
    assert payload["effective_date"] is None


@pytest.mark.parametrize("payload", [None, {}, {"text": "Body", "status": None}])
def test_missing_metadata(payload, search):
    search.return_value = [ScoredPoint(id=1, version=1, score=0.2, payload=payload)]
    result = retrieval.retrieve("question")[0]
    assert result["source_file"] is None
    assert result["page"] is None
    assert result["text"] == (payload or {}).get("text")
    assert result["metadata"] == ({"status": None} if payload else {})
    assert "access_level" not in result["metadata"]


def test_terminal_output(search, capsys):
    search.return_value = [
        ScoredPoint(
            id=1,
            version=1,
            score=0.7654321,
            payload={
                "text": "First line\nSecond line",
                "source_file": "circular.pdf",
                "page": 3,
                "title": "Circular title",
                "regulator": "SEBI",
                "status": None,
            },
        ),
        ScoredPoint(id=2, version=1, score=0.1, payload=None),
    ]
    retrieval.print_results(retrieval.retrieve("question"))
    output = capsys.readouterr().out
    for expected in (
        "Rank 1 | Similarity score: 0.765432",
        "Source document: circular.pdf",
        "Page: 3",
        "title: Circular title",
        "regulator: SEBI",
        "status: unavailable",
        "First line\nSecond line",
        "Rank 2",
        "Source document: unavailable",
        "Page: unavailable",
    ):
        assert expected in output
    assert output.index("Rank 1") < output.index("Rank 2")


def test_empty_terminal_output(capsys):
    retrieval.print_results([])
    assert capsys.readouterr().out == "No results.\n"


def test_cli_arguments(search, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["retrieval", "--query", "question", "--k", "3"])
    retrieval.main()
    search.assert_called_once_with(query="question", limit=3)
    assert "No results." in capsys.readouterr().out


def test_cli_search_error(search, monkeypatch, capsys):
    search.side_effect = RuntimeError("Search unavailable")
    monkeypatch.setattr("sys.argv", ["retrieval", "--query", "question"])
    with pytest.raises(SystemExit) as exc:
        retrieval.main()
    assert exc.value.code == 1
    assert "Retrieval error: Search unavailable" in capsys.readouterr().err
