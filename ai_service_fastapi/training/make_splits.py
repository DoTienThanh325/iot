"""Create fixed group splits before segmentation; inspect label distribution afterward."""
import argparse

import numpy as np
import pandas as pd


def split_manifest(frame, seed=42):
    if frame["subject_id"].isna().any() or frame["subject_id"].nunique() < 20:
        raise ValueError("At least 20 known subjects are required for this four-way split")
    if frame.groupby("record_id")["subject_id"].nunique().max() > 1:
        raise ValueError("A record cannot belong to multiple subjects")
    groups = np.array(sorted(frame["subject_id"].unique()))
    np.random.default_rng(seed).shuffle(groups)
    # 60/10/10/20 by subject, not by row. Never retry seeds to optimize test scores.
    n = len(groups)
    boundaries = [int(n * .6), int(n * .7), int(n * .8)]
    membership = {}
    for split, members in zip(["train", "calibration", "validation", "test"],
                              np.split(groups, boundaries)):
        membership.update({str(subject): split for subject in members})
    result = frame.copy()
    result["split"] = result["subject_id"].astype(str).map(membership)
    if "label" in result:
        for split, part in result.groupby("split"):
            if set(part["label"]) != {0, 1}:
                raise ValueError(f"{split} lacks a class; design a stratified subject split before training")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    frame = pd.read_csv(args.manifest, dtype={"subject_id": str, "record_id": str})
    split_manifest(frame, args.seed).to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
