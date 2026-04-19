"""
FinBERT sentiment analyzer.

ProsusAI/finbert is a BERT model fine-tuned on the Financial PhraseBank
dataset. It understands financial language that VADER misses:
  - "missed estimates but raised guidance" → correctly mixed/neutral
  - "earnings beat by 12%" → correctly positive
  - "downgraded to underperform" → correctly negative

Interface mirrors VADER so the rest of the codebase needs minimal changes:
    result = analyze("Apple beats earnings estimates")
    # {'compound': 0.91, 'pos': 0.95, 'neg': 0.02, 'neu': 0.03, 'label': 'positive'}

The model is downloaded once (~440MB) to ~/.cache/huggingface on first call.
Subsequent calls use the in-memory singleton — no reload overhead.
Uses Apple MPS (Metal GPU) when available, falls back to CPU.
"""

import logging
import threading
from typing import Optional

import torch

logger = logging.getLogger(__name__)

# Max tokens FinBERT (BERT-based) supports
_MAX_TOKENS = 512

# Lazy singleton — loaded on first call, reused thereafter
_pipeline = None
_lock = threading.Lock()


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    with _lock:
        if _pipeline is not None:  # double-checked locking
            return _pipeline

        from transformers import pipeline as hf_pipeline

        # Pick best available device
        if torch.backends.mps.is_available():
            device = "mps"
            logger.info("FinBERT: using Apple MPS (Metal GPU)")
        elif torch.cuda.is_available():
            device = "cuda"
            logger.info("FinBERT: using CUDA GPU")
        else:
            device = "cpu"
            logger.info("FinBERT: using CPU (no GPU found)")

        logger.info("Loading ProsusAI/finbert — first call downloads ~440MB to ~/.cache/huggingface")
        _pipeline = hf_pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None,       # return scores for all 3 classes
            device=device,
            truncation=True,
            max_length=_MAX_TOKENS,
        )
        logger.info("FinBERT loaded and ready.")

    return _pipeline


def _scores_to_result(raw: list[dict]) -> dict:
    """
    Convert FinBERT raw output to a VADER-compatible result dict.

    FinBERT labels: 'positive', 'negative', 'neutral'
    compound = pos_prob - neg_prob  →  range [-1, +1], same sign as VADER
    label    = argmax of the three probabilities
    """
    scores = {item["label"].lower(): item["score"] for item in raw}
    pos = scores.get("positive", 0.0)
    neg = scores.get("negative", 0.0)
    neu = scores.get("neutral", 0.0)

    compound = round(pos - neg, 4)

    if pos >= neg and pos >= neu:
        label = "positive"
    elif neg >= pos and neg >= neu:
        label = "negative"
    else:
        label = "neutral"

    return {
        "compound": compound,
        "pos": pos,
        "neg": neg,
        "neu": neu,
        "label": label,
    }


def analyze(text: str) -> dict:
    """
    Analyze a single piece of text.

    Returns:
        {
            'compound': float,   # -1 to +1  (pos_prob - neg_prob)
            'pos':      float,   # 0 to 1
            'neg':      float,   # 0 to 1
            'neu':      float,   # 0 to 1
            'label':    str,     # 'positive' | 'negative' | 'neutral'
        }
    """
    pipe = _get_pipeline()
    # pipeline returns a list of lists when given a single string
    result = pipe(text or "")[0]
    return _scores_to_result(result)


def analyze_batch(texts: list[str], batch_size: int = 32) -> list[dict]:
    """
    Analyze a list of texts efficiently using batching.
    Much faster than calling analyze() in a loop.

    Returns a list of result dicts in the same order as input.
    """
    if not texts:
        return []

    pipe = _get_pipeline()
    # Replace empty strings so FinBERT doesn't choke
    safe_texts = [t if t and t.strip() else "no content" for t in texts]

    raw_results = pipe(safe_texts, batch_size=batch_size)
    return [_scores_to_result(r) for r in raw_results]


def is_available() -> bool:
    """Check if transformers + torch are importable (model not yet loaded)."""
    try:
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False
