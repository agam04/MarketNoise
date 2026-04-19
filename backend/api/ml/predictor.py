"""
Model loading and prediction serving for price-impact direction.
"""

import logging
from pathlib import Path

import joblib
import pandas as pd

from .features import extract_features

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / 'ml_models'

# In-memory cache for loaded models
_model_cache: dict = {}


def load_model(algorithm: str = 'random_forest') -> dict | None:
    """Load a trained model from disk. Caches in memory after first load."""
    if algorithm in _model_cache:
        return _model_cache[algorithm]

    model_path = MODELS_DIR / f'{algorithm}_impact_model.joblib'
    if not model_path.exists():
        logger.info(f"No trained model found at {model_path}")
        return None

    try:
        bundle = joblib.load(model_path)
        _model_cache[algorithm] = bundle
        logger.info(f"Loaded {algorithm} model from {model_path}")
        return bundle
    except Exception as e:
        logger.warning(f"Failed to load model: {e}")
        return None


def clear_model_cache():
    """Clear cached models (useful after retraining)."""
    _model_cache.clear()


def predict_impact(narrative) -> dict | None:
    """
    Predict price impact direction for a single narrative.

    Returns dict with:
        - predicted_direction: 'up', 'down', or 'flat'
        - confidence: dict of {class: probability}
    Or None if no model is loaded.
    """
    bundle = load_model()
    if bundle is None:
        return None

    model = bundle['model']
    feature_cols = bundle['feature_cols']

    features = extract_features(narrative)
    feature_df = pd.DataFrame([{col: features.get(col, 0) for col in feature_cols}])

    prediction = model.predict(feature_df)[0]
    probabilities = model.predict_proba(feature_df)[0]
    classes = model.classes_

    return {
        'predicted_direction': prediction,
        'confidence': {cls: round(float(prob), 3) for cls, prob in zip(classes, probabilities)},
    }
