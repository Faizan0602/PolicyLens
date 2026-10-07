"""Unit tests for PolicyLens LLM and embedding factories."""

import os
from unittest.mock import patch

import numpy as np
import pytest

from policylens.config import Settings
from policylens.llm import (
    MockLLM,
    compute_cosine_similarity,
    demonstrate_embedding_similarity,
    get_embeddings,
    get_llm,
)


def test_mock_llm_generation():
    """Verify MockLLM returns simulated text without network calls."""
    llm = MockLLM(model="test-model")
    res = llm.generate("Hello world")
    assert "[MockLLM:test-model]" in res
    assert "Hello world" in res


def test_get_llm_mock_provider():
    """Verify get_llm instantiates MockLLM when provider is set to 'mock'."""
    settings = Settings(llm_provider="mock", llm_model="test-mock")
    llm = get_llm(settings)
    assert isinstance(llm, MockLLM)
    assert llm.model == "test-mock"


def test_get_llm_provider_switching():
    """Verify get_llm dynamically switches provider based on settings."""
    from policylens.config import get_settings

    get_settings.cache_clear()
    with patch.dict(
        os.environ, {"POLICYLENS_LLM_PROVIDER": "mock", "POLICYLENS_LLM_MODEL": "custom-mock"}
    ):
        llm = get_llm()
        assert isinstance(llm, MockLLM)
        assert llm.model == "custom-mock"
    get_settings.cache_clear()


def test_get_llm_unsupported_provider():
    """Verify get_llm raises ValueError for unsupported provider."""
    settings = Settings(llm_provider="unsupported_provider_xyz")
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_llm(settings)


def test_manual_cosine_similarity_math():
    """Verify compute_cosine_similarity adheres to manual mathematical formula."""
    # Identical vectors -> 1.0
    u = np.array([1.0, 2.0, 3.0])
    assert pytest.approx(compute_cosine_similarity(u, u), rel=1e-5) == 1.0

    # Orthogonal vectors -> 0.0
    v = np.array([-2.0, 1.0, 0.0])  # dot product = -2 + 2 + 0 = 0
    assert pytest.approx(compute_cosine_similarity(u, v), abs=1e-6) == 0.0

    # Opposing vectors -> -1.0
    w = np.array([-1.0, -2.0, -3.0])
    assert pytest.approx(compute_cosine_similarity(u, w), rel=1e-5) == -1.0

    # Zero vector handling -> 0.0
    z = np.array([0.0, 0.0, 0.0])
    assert compute_cosine_similarity(u, z) == 0.0


def test_embedding_factory_and_demonstration():
    """Verify BGE embedding model loads and semantic similarity holds."""
    model = get_embeddings("BAAI/bge-small-en-v1.5")
    assert model is not None

    scores = demonstrate_embedding_similarity(model)
    sim_ab = scores["sim(A, B) [RBI circular vs Reserve Bank guidance]"]
    sim_ac = scores["sim(A, C) [RBI circular vs football]"]

    # Semantic check: regulatory sentences must score significantly higher than football
    assert sim_ab > sim_ac
    assert sim_ab > 0.65
    assert sim_ac < 0.50
