"""Group-aware RF baseline, independent calibration and validation threshold."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold

from app.algorithms.v2.ecg import EXTRACTOR_VERSION, FEATURES
from app.config import Settings
from training.data import arrays, load_features
from training.evaluate import evaluate


def choose_threshold(y, probabilities, target):
    candidates = []
    for threshold in np.linspace(.01, .99, 99):
        tn, fp, fn, tp = confusion_matrix(y, probabilities >= threshold, labels=[0, 1]).ravel()
        if tp / (tp + fn) >= target:
            candidates.append((tn / (tn + fp), float(threshold)))
    if not candidates:
        raise ValueError("Validation sensitivity target not met; artifact not exported")
    return max(candidates)[1]


def train(features_path, output, *, allow_synthetic=False, folds=3, trees=200,
          target=.95, model_version="rf-v2.0", bootstrap=200):
    if not 0 < target <= 1 or folds < 2 or trees < 10:
        raise ValueError("Invalid training configuration")
    frame = load_features(features_path)
    synthetic = bool((frame["data_origin"] == "synthetic").any())
    if synthetic and not allow_synthetic:
        raise ValueError("Synthetic demonstration data requires --allow-synthetic")
    output = Path(output)
    if output.exists():
        raise ValueError("Output directory already exists; choose a new model version")
    parts = {split: frame[frame["split"] == split] for split in frame["split"].unique()}
    x, y = arrays(parts["train"])
    groups = parts["train"]["subject_id"].to_numpy()
    cv = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=42)
    splits = list(cv.split(x, y, groups))
    for fit, validation in splits:
        if len(np.unique(y[fit])) < 2 or len(np.unique(y[validation])) < 2:
            raise ValueError("A CV fold lacks a class; redesign the group split")
    search = GridSearchCV(
        RandomForestClassifier(n_estimators=trees, class_weight="balanced_subsample",
                               random_state=42, n_jobs=1),
        {"max_depth": [8, None], "min_samples_leaf": [2, 5], "max_features": ["sqrt", 1.0]},
        cv=splits, scoring="average_precision", n_jobs=1, error_score="raise",
    )
    search.fit(x, y)
    calibration_x, calibration_y = arrays(parts["calibration"])
    model = CalibratedClassifierCV(FrozenEstimator(search.best_estimator_), method="sigmoid")
    model.fit(calibration_x, calibration_y)
    validation_x, validation_y = arrays(parts["validation"])
    column = list(model.classes_).index(1)
    probabilities = model.predict_proba(validation_x)[:, column]
    threshold = choose_threshold(validation_y, probabilities, target)
    report = evaluate(model, parts["test"], threshold, bootstrap=bootstrap)
    report.update(synthetic_data=synthetic, clinical_validation=False)
    config = Settings()
    metadata = {
        "model_version": model_version, "extractor_version": EXTRACTOR_VERSION,
        "feature_order": FEATURES, "classes": list(map(int, model.classes_)),
        "threshold": threshold, "calibrated": True, "calibration_method": "sigmoid",
        "synthetic_data": synthetic, "clinical_validation": False,
        "extractor_config": {name: getattr(config, name) for name in
                             ["ecg_low_hz", "ecg_high_hz", "ecg_min_seconds"]},
        "best_params": search.best_params_, "random_seed": 42,
        "validation_sensitivity_target": target,
        "dataset_sha256": hashlib.sha256(Path(features_path).read_bytes()).hexdigest(),
        "split_subject_counts": {name: int(part.subject_id.nunique()) for name, part in parts.items()},
        "python_version": platform.python_version(),
        "package_versions": {name: importlib.metadata.version(name) for name in
                             ["numpy", "scipy", "scikit-learn", "joblib", "pandas"]},
    }
    output.mkdir(parents=True)
    model_path = output / "afib_rf_model.pkl"
    joblib.dump(model, model_path)
    metadata["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    for filename, value in [("metadata.json", metadata), ("evaluation_report.json", report),
                            ("feature_schema.json", {"order": FEATURES, "extractor_version": EXTRACTOR_VERSION}),
                            ("preprocessing_config.json", metadata["extractor_config"])]:
        (output / filename).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    frame[["subject_id", "record_id", "split", "label", "data_origin"]].to_csv(output / "split_manifest.csv", index=False)
    (output / "requirements.lock.txt").write_text("\n".join(
        f"{name}=={version}" for name, version in metadata["package_versions"].items()) + "\n")
    (output / "model_card.md").write_text(
        f"# {model_version}\n\nSynthetic demo: {synthetic}. Clinical validation: false.\n\n"
        "Binary AFib/non-AFib research classifier on accepted ECG windows. "
        "Non-AFib does not imply normal sinus rhythm. No stroke-risk estimation.\n\n"
        "Review data provenance, quality rejection audit, external-device performance, "
        "temporal false alarms and subject confidence intervals before deployment.\n",
        encoding="utf-8")
    checksums = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
                 for path in sorted(output.iterdir()) if path.is_file()]
    (output / "checksums.sha256").write_text("\n".join(checksums) + "\n")
    return metadata, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("features")
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--trees", type=int, default=200)
    parser.add_argument("--target-sensitivity", type=float, default=.95)
    parser.add_argument("--model-version", default="rf-v2.0")
    args = parser.parse_args()
    metadata, report = train(args.features, args.output, allow_synthetic=args.allow_synthetic,
                             folds=args.folds, trees=args.trees, target=args.target_sensitivity,
                             model_version=args.model_version)
    print(json.dumps({"metadata": metadata, "test": report}, indent=2))


if __name__ == "__main__":
    main()
