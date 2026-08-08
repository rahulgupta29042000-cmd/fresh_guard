"""Train the Phase 1 prototype risk model on the synthetic dataset.

Run generate_dataset.py first. This saves model.pkl (a dict with the
fitted estimator + feature column order) for predict.py and the backend
to load.
"""
import os

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split

from feature_schema import FEATURE_COLUMNS, LABEL_COLUMN

HERE = os.path.dirname(__file__)


def main():
    dataset_path = os.path.join(HERE, "dataset.csv")
    if not os.path.exists(dataset_path):
        raise SystemExit("dataset.csv not found — run generate_dataset.py first")

    df = pd.read_csv(dataset_path)
    X = df[FEATURE_COLUMNS]
    y = df[LABEL_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=150,
        max_depth=3,
        learning_rate=0.08,
        random_state=42,
    )
    model.fit(X_train, y_train)

    bundle = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_version": "v0.1-prototype",
        "trained_on": "synthetic",
    }
    model_path = os.path.join(HERE, "model.pkl")
    joblib.dump(bundle, model_path)
    print(f"Saved model to {model_path}")

    # Keep the held-out split available to evaluate.py without retraining.
    X_test.assign(**{LABEL_COLUMN: y_test}).to_csv(
        os.path.join(HERE, "holdout.csv"), index=False
    )
    print(f"Train rows: {len(X_train)}, holdout rows: {len(X_test)}")


if __name__ == "__main__":
    main()
