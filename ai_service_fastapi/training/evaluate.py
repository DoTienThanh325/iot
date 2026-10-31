"""Metrics and confidence intervals clustered by subject (not by window)."""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, log_loss, roc_auc_score)

from app.algorithms.v2.afib import AFibPredictor
from app.config import Settings
from training.data import arrays, load_features


def binary_metrics(y, probabilities, threshold):
    tn, fp, fn, tp = confusion_matrix(y, probabilities >= threshold, labels=[0, 1]).ravel()
    both = len(np.unique(y)) == 2
    return {
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "sensitivity": float(tp / (tp + fn)) if tp + fn else None,
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "precision": float(tp / (tp + fp)) if tp + fp else None,
        "f1": float(f1_score(y, probabilities >= threshold, zero_division=0)),
        "average_precision": float(average_precision_score(y, probabilities)) if both else None,
        "roc_auc": float(roc_auc_score(y, probabilities)) if both else None,
        "brier_score": float(brier_score_loss(y, probabilities)),
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
        "positive_prevalence": float(np.mean(y)), "windows": int(len(y)),
    }


def evaluate(model, part, threshold, bootstrap=200):
    x, y = arrays(part)
    column = list(model.classes_).index(1)
    probabilities = model.predict_proba(x)[:, column]
    result = binary_metrics(y, probabilities, threshold)
    result["subjects"] = int(part["subject_id"].nunique())
    rng = np.random.default_rng(42)
    groups = part["subject_id"].to_numpy()
    subjects = np.unique(groups)
    intervals = {"sensitivity": [], "specificity": []}
    for _ in range(bootstrap):
        sampled = rng.choice(subjects, len(subjects), replace=True)
        indices = np.concatenate([np.flatnonzero(groups == subject) for subject in sampled])
        metrics = binary_metrics(y[indices], probabilities[indices], threshold)
        for key in intervals:
            if metrics[key] is not None:
                intervals[key].append(metrics[key])
    result["subject_bootstrap_95_ci"] = {
        key: np.quantile(values, [.025, .975]).tolist() if values else None
        for key, values in intervals.items()
    }
    result["scope"] = "accepted windows only; quality rejection and temporal event evaluation are separate"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("features")
    parser.add_argument("artifact")
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    predictor = AFibPredictor(Settings(model_dir=args.artifact, model_required=True,
                                      allow_synthetic_model=args.allow_synthetic))
    predictor.load()
    if not predictor.ready:
        raise ValueError("Artifact rejected")
    frame = load_features(args.features)
    result = evaluate(predictor.model, frame[frame["split"] == "test"], predictor.metadata["threshold"])
    result["synthetic_data"] = bool((frame.data_origin == "synthetic").any())
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
