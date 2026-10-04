"""LLM and Embedding model interfaces and factories for PolicyLens.

Provides provider-agnostic LLM client factories and SentenceTransformer
embedding initialization with manual NumPy cosine similarity.
"""

from functools import lru_cache
from typing import Any, Protocol

import numpy as np
from sentence_transformers import SentenceTransformer

from policylens.config import Settings, get_settings

SAMPLE_SENTENCES = {
    "A": "RBI issued a new circular",
    "B": "The Reserve Bank released fresh guidance",
    "C": "I like playing football",
}


class LLMClient(Protocol):
    """Protocol for provider-agnostic LLM clients."""

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text completion for a prompt."""
        ...


class MockLLM:
    """Mock LLM implementation for offline local testing and development."""

    def __init__(self, model: str = "mock-model") -> None:
        self.model = model

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a simulated response without making external network calls."""
        return f"[MockLLM:{self.model}] Response to: {prompt[:50]}"


class GeminiLLM:
    """Gemini LLM wrapper using google-genai SDK."""

    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None) -> None:
        from google import genai

        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate completion using Gemini API."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            **kwargs,
        )
        return str(response.text)


class OpenAILLM:
    """OpenAI LLM wrapper using official openai SDK."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate completion using OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        choice = response.choices[0]
        return str(choice.message.content or "")


def get_llm(settings: Settings | None = None) -> LLMClient:
    """Instantiate an LLM client driven entirely by configuration and environment.

    Supported providers: 'mock', 'gemini' (or 'google'), 'openai'.
    """
    cfg = settings or get_settings()
    provider = cfg.llm_provider.strip().lower()

    if provider == "mock":
        return MockLLM(model=cfg.llm_model)
    elif provider in ("gemini", "google"):
        api_key = cfg.gemini_api_key.get_secret_value() if cfg.gemini_api_key else None
        return GeminiLLM(model=cfg.llm_model, api_key=api_key)
    elif provider == "openai":
        api_key = cfg.openai_api_key.get_secret_value() if cfg.openai_api_key else None
        return OpenAILLM(model=cfg.llm_model, api_key=api_key)
    else:
        raise ValueError(
            f"Unsupported LLM provider: '{cfg.llm_provider}'. "
            "Supported providers: 'mock', 'gemini', 'openai'."
        )


@lru_cache
def get_embeddings(model_name: str | None = None) -> SentenceTransformer:
    """Load and cache the configured embedding model using SentenceTransformer."""
    name = model_name or get_settings().embedding_model
    return SentenceTransformer(name)


def compute_cosine_similarity(u: np.ndarray, v: np.ndarray) -> float:
    """Compute cosine similarity between two 1D vectors manually using NumPy.

    Formula: cos(u, v) = (u . v) / (||u||_2 * ||v||_2)
    DO NOT use helper utilities; implemented via explicit dot product and norms.
    """
    norm_u = float(np.linalg.norm(u))
    norm_v = float(np.linalg.norm(v))
    if norm_u == 0.0 or norm_v == 0.0:
        return 0.0
    return float(np.dot(u, v) / (norm_u * norm_v))


def demonstrate_embedding_similarity(
    model: SentenceTransformer | None = None,
) -> dict[str, float]:
    """Embed benchmark sentences and compute manual pairwise cosine similarities.

    Validates that semantically related regulatory sentences score significantly
    higher than an unrelated sports sentence.
    """
    embedder = model or get_embeddings()

    sentences = [
        SAMPLE_SENTENCES["A"],
        SAMPLE_SENTENCES["B"],
        SAMPLE_SENTENCES["C"],
    ]

    # Generate embeddings without normalizing so manual norm calculation is verified
    embeddings = embedder.encode(sentences, normalize_embeddings=False)

    emb_a = embeddings[0]
    emb_b = embeddings[1]
    emb_c = embeddings[2]

    sim_ab = compute_cosine_similarity(emb_a, emb_b)
    sim_ac = compute_cosine_similarity(emb_a, emb_c)
    sim_bc = compute_cosine_similarity(emb_b, emb_c)

    results = {
        "sim(A, B) [RBI circular vs Reserve Bank guidance]": sim_ab,
        "sim(A, C) [RBI circular vs football]": sim_ac,
        "sim(B, C) [Reserve Bank guidance vs football]": sim_bc,
    }

    if not (sim_ab > sim_ac):
        raise ValueError(
            f"Expected similarity(A, B) > similarity(A, C), got {sim_ab:.4f} <= {sim_ac:.4f}"
        )

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("PolicyLens -- Embedding Cosine Similarity Demonstration")
    print("Model: BAAI/bge-small-en-v1.5 (SentenceTransformer)")
    print("=" * 60)
    for key, text in SAMPLE_SENTENCES.items():
        print(f"Sentence {key}: '{text}'")
    print("-" * 60)

    scores = demonstrate_embedding_similarity()
    for pair, score in scores.items():
        print(f"{pair}: {score:.4f}")
    print("-" * 60)
    print("Demonstration successful: semantically related sentences score significantly higher.")
