"""Evaluate the trained prototype model on the held-out synthetic split.

IMPORTANT: these metrics describe performance on SYNTHETIC validation
data only. They validate that the modeling pipeline works end-to-end —
they are not a claim about real-world damage-prediction accuracy.
"""
import json
import os

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from feature_schema import FEATURE_COLUMNS, LABEL_COLUMN

HERE = os.path.dirname(__file__)


def main():
    holdout_path = os.path.join(HERE, "holdout.csv")
    model_path = os.path.join(HERE, "model.pkl")
    if not os.path.exists(holdout_path) or not os.path.exists(model_path):
        raise SystemExit("Run train_model.py first to produce model.pkl and holdout.csv")

    bundle = joblib.load(model_path)
    model = bundle["model"]

    df = pd.read_csv(holdout_path)
    X = df[FEATURE_COLUMNS]
    y = df[LABEL_COLUMN]

    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]

    metrics = {
        "note": "Prototype model performance on synthetic validation data. Not a real-world accuracy claim.",
        "accuracy": round(accuracy_score(y, y_pred), 4),
        "precision": round(precision_score(y, y_pred), 4),
        "recall": round(recall_score(y, y_pred), 4),
        "f1": round(f1_score(y, y_pred), 4),
        "roc_auc": round(roc_auc_score(y, y_proba), 4),
        "confusion_matrix": {
            "labels": ["no_issue", "had_issue"],
            "matrix": confusion_matrix(y, y_pred).tolist(),
        },
        "holdout_rows": len(df),
    }

    out_path = os.path.join(HERE, "metrics.json")
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))
    print(f"\nSaved metrics to {out_path}")


if __name__ == "__main__":
    main()
