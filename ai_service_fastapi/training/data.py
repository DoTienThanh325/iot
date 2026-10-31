"""Validated feature datasets, shared by training and evaluation."""
import numpy as np
import pandas as pd

from app.algorithms.v2.ecg import EXTRACTOR_VERSION, FEATURES


def load_features(path):
    frame = pd.read_csv(path, dtype={"subject_id": str, "record_id": str})
    required = FEATURES + ["subject_id", "record_id", "split", "label", "data_origin", "extractor_version"]
    if not set(required).issubset(frame.columns) or frame.empty:
        raise ValueError("Empty dataset or missing required columns")
    if frame[required].isna().any().any():
        raise ValueError("Required values cannot be missing")
    if not frame["label"].isin([0, 1]).all():
        raise ValueError("Labels must be 0 (non-AFib) or 1 (AFib)")
    if not frame["data_origin"].isin(["synthetic", "reference_labeled"]).all():
        raise ValueError("Declare synthetic/reference_labeled provenance")
    if not (frame["extractor_version"] == EXTRACTOR_VERSION).all():
        raise ValueError("Extractor version mismatch")
    if not np.isfinite(frame[FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Features must be finite numeric values")
    allowed = {"train", "calibration", "validation", "test"}
    if not set(frame["split"]).issubset(allowed):
        raise ValueError("Unknown split")
    if frame.groupby("subject_id")["split"].nunique().max() > 1:
        raise ValueError("Subject leakage between splits")
    if frame.groupby("record_id")["split"].nunique().max() > 1:
        raise ValueError("Record leakage between splits")
    if frame.duplicated(["record_id"]).any():
        raise ValueError("record_id must identify a unique window")
    for split in allowed:
        part = frame[frame["split"] == split]
        if set(part["label"]) != {0, 1}:
            raise ValueError(f"Split {split} must contain both labels")
    return frame


def arrays(part):
    return part[FEATURES].to_numpy(dtype=float), part["label"].to_numpy(dtype=int)
