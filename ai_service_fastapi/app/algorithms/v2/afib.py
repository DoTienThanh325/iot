"""Versioned artifact adapter. Only load trusted, explicitly configured artifacts."""
import hashlib
import json
import logging
import importlib.metadata
from pathlib import Path

import joblib
import numpy as np

from app.algorithms.v2.ecg import EXTRACTOR_VERSION, FEATURES

logger = logging.getLogger(__name__)


class AFibPredictor:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.metadata = None
        self.load_error = "not_configured"
        self.positive_index = None

    def load(self):
        if not self.config.model_dir:
            return
        try:
            folder = Path(self.config.model_dir)
            metadata = json.loads((folder / "metadata.json").read_text())
            if metadata["extractor_version"] != EXTRACTOR_VERSION or metadata["feature_order"] != FEATURES:
                raise ValueError("Incompatible feature schema")
            expected_config = {name: getattr(self.config, name) for name in
                               ["ecg_low_hz", "ecg_high_hz", "ecg_min_seconds"]}
            if metadata["extractor_config"] != expected_config:
                raise ValueError("Extractor configuration differs from training")
            for name in ["numpy", "scipy", "scikit-learn", "joblib"]:
                if metadata["package_versions"].get(name) != importlib.metadata.version(name):
                    raise ValueError("Artifact runtime package version mismatch")
            if metadata["synthetic_data"] and not self.config.allow_synthetic_model:
                raise ValueError("Synthetic demo model is disabled")
            if not isinstance(metadata["calibrated"], bool):
                raise ValueError("Invalid calibration metadata")
            threshold = metadata["threshold"]
            if not np.isfinite(threshold) or not 0 < threshold < 1:
                raise ValueError("Invalid decision threshold")
            model_file = folder / "afib_rf_model.pkl"
            if hashlib.sha256(model_file.read_bytes()).hexdigest() != metadata["model_sha256"]:
                raise ValueError("Artifact checksum mismatch")
            model = joblib.load(model_file)
            if model.n_features_in_ != len(FEATURES):
                raise ValueError("Wrong feature count")
            labels = list(model.classes_)
            if len(labels) != 2 or set(labels) != {0, 1} or metadata["classes"] != labels:
                raise ValueError("Binary labels must match metadata and be 0/1")
            positive = labels.index(1)
            probe = np.asarray(model.predict_proba([[75, 30, 10, 0.05, 1.0]]))
            if probe.shape != (1, 2) or not np.isfinite(probe).all() or np.any((probe < 0) | (probe > 1)) or not np.allclose(probe.sum(axis=1), 1):
                raise ValueError("Invalid probability output")
            if not metadata.get("model_version"):
                raise ValueError("Missing model version")
            self.model, self.metadata, self.positive_index = model, metadata, positive
            self.load_error = None
        except Exception:
            self.model = self.metadata = None
            self.load_error = "artifact_rejected"
            logger.exception("V2 artifact rejected; model disabled")

    @property
    def ready(self):
        return self.model is not None or not self.config.model_required

    def classify(self, ecg):
        base = {"quality_status": ecg["quality_status"], "analysis_status": "UNDETERMINED",
                "metrics": {}, "afib_detected": None, "afib_probability": None,
                "heuristic_score": None, "inference_source": "unavailable",
                "model_version": None, "extractor_version": EXTRACTOR_VERSION,
                "calibrated": False}
        features = ecg["metrics"].get("features")
        if ecg["quality_status"] != "VALID" or features is None:
            return base
        vector = np.array([[features[name] for name in FEATURES]], dtype=float)
        if not np.isfinite(vector).all():
            raise ValueError("Nonfinite inference features")
        if self.model is not None:
            probabilities = np.asarray(self.model.predict_proba(vector))
            if probabilities.shape != (1, 2) or not np.isfinite(probabilities).all() or np.any((probabilities < 0) | (probabilities > 1)) or not np.allclose(probabilities.sum(axis=1), 1):
                raise RuntimeError("Invalid inference probabilities")
            probability = float(probabilities[0, self.positive_index])
            detected = probability >= self.metadata["threshold"]
            base.update(analysis_status="AFIB_SUSPECTED" if detected else "NON_AFIB",
                        afib_detected=detected, afib_probability=probability,
                        inference_source="model", model_version=self.metadata["model_version"],
                        calibrated=self.metadata["calibrated"])
            return base
        if self.config.model_required:
            raise RuntimeError("Required model is unavailable")
        score = 0.0
        rules = [("RMSSD", 66, 100, 0.15, 0.35), ("pNN50", 25, 50, 0.15, 0.30),
                 ("CV_RR", 0.08, 0.12, 0.10, 0.25), ("Shannon_H", 1.4, 1.8, 0.05, 0.10)]
        contributions = {}
        for name, lower, upper, low_score, high_score in rules:
            value = features[name]
            contribution = high_score if value >= upper else low_score if value >= lower else 0.0
            contributions[name] = contribution
            score += contribution
        high = score >= self.config.afib_high_score
        warning = score >= self.config.afib_warning_score or any(contributions.values())
        base.update(analysis_status="AFIB_SUSPECTED" if high else "IRREGULARITY_WARNING" if warning else "NON_AFIB",
                    afib_detected=high, heuristic_score=min(score, 1.0), inference_source="heuristic",
                    metrics={"rule_contributions": contributions, "fallback_reason": self.load_error,
                             "policy_version": "heuristic-v2.0"})
        return base
