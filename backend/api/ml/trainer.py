"""
Model training for price-impact prediction.
Supports Random Forest and XGBoost classifiers.
"""

import logging
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report

from .features import build_training_dataframe, FEATURE_COLUMNS

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / 'ml_models'

MIN_SAMPLES = 50


def train_model(algorithm: str = 'random_forest') -> dict:
    """
    Train a price-impact direction classifier and save to disk.

    Args:
        algorithm: 'random_forest' or 'xgboost'

    Returns:
        dict with training metrics, or error message if not enough data.
    """
    df = build_training_dataframe()

    if len(df) < MIN_SAMPLES:
        return {
            'error': (
                f'Not enough training data. Have {len(df)} labeled samples, '
                f'need at least {MIN_SAMPLES}. '
                f'Run: python manage.py backfill_prices --all-stocks --limit 100'
            ),
            'samples': len(df),
            'min_required': MIN_SAMPLES,
        }

    # Separate features and target
    X = df[FEATURE_COLUMNS]
    y = df['direction_24h']

    # Check class distribution
    class_counts = y.value_counts().to_dict()

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Build model
    if algorithm == 'xgboost':
        from xgboost import XGBClassifier
        model = XGBClassifier(
            n_estimators=100, max_depth=5, random_state=42,
            use_label_encoder=False, eval_metric='mlogloss',
        )
    else:
        model = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42,
        )

    # Train
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    cv_scores = cross_val_score(model, X, y, cv=min(5, len(df) // 10 or 2), scoring='accuracy')

    # Feature importance
    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_))
    top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]

    # Save model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f'{algorithm}_impact_model.joblib'
    joblib.dump({
        'model': model,
        'feature_cols': FEATURE_COLUMNS,
        'algorithm': algorithm,
    }, model_path)

    return {
        'algorithm': algorithm,
        'samples': len(df),
        'train_size': len(X_train),
        'test_size': len(X_test),
        'class_distribution': class_counts,
        'test_accuracy': round(report['accuracy'], 4),
        'cv_accuracy_mean': round(cv_scores.mean(), 4),
        'cv_accuracy_std': round(cv_scores.std(), 4),
        'top_features': top_features,
        'classification_report': report,
        'model_path': str(model_path),
    }



