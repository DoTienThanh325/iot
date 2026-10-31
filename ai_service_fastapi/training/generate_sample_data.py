"""Generate reproducible synthetic ECG and features, with explicit demo provenance."""
import argparse
import csv
from pathlib import Path

import numpy as np

from app.algorithms.v2.ecg import EXTRACTOR_VERSION, FEATURES, extract_features
from app.config import Settings


def waveform(rng, label, fs=125, seconds=20):
    t = np.arange(fs * seconds) / fs
    signal = 0.025 * np.sin(2 * np.pi * 0.25 * t) + rng.normal(0, 0.008, len(t))
    beat = 0.4
    average = rng.uniform(0.65, 1.0)
    while beat < seconds:
        signal += 1.2 * np.exp(-0.5 * ((t - beat) / 0.018) ** 2)
        signal -= 0.15 * np.exp(-0.5 * ((t - beat - 0.035) / 0.012) ** 2)
        signal += 0.12 * np.exp(-0.5 * ((t - beat - 0.22) / 0.06) ** 2)
        rr = rng.uniform(0.36, 1.40) if label else rng.normal(average, 0.014)
        beat += max(0.32, rr)
    if rng.random() < 0.5:
        signal = -signal
    return signal


def generate(output, seed=42, save_waveforms=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config = Settings()
    rng = np.random.default_rng(seed)
    rows, manifest = [], []
    split_names = ["train"] * 12 + ["calibration"] * 4 + ["validation"] * 4 + ["test"] * 4
    for subject, split in enumerate(split_names):
        for window in range(4):
            label = window % 2
            samples = waveform(rng, label)
            result = extract_features(samples, 125, config)
            if result["quality_status"] != "VALID":
                raise RuntimeError(f"Synthetic generator produced rejected signal: {result}")
            record_id = f"synthetic-s{subject:03d}-w{window:02d}"
            rows.append({
                "subject_id": f"synthetic-s{subject:03d}", "record_id": record_id,
                "split": split, "label": label, "data_origin": "synthetic",
                "extractor_version": EXTRACTOR_VERSION,
                **result["metrics"]["features"],
            })
            signal_path = ""
            if save_waveforms:
                folder = output / "waveforms"
                folder.mkdir(exist_ok=True)
                signal_path = f"waveforms/{record_id}.csv"
                np.savetxt(output / signal_path, samples, delimiter=",", header="ecg", comments="")
            manifest.append({
                "subject_id": f"synthetic-s{subject:03d}", "record_id": record_id,
                "split": split, "label": label, "data_origin": "synthetic",
                "signal_path": signal_path, "fs": 125, "unit": "mV",
                "start_sample": 0, "end_sample": len(samples),
            })
    for name, records in [("features.csv", rows), ("manifest.csv", manifest)]:
        with (output / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    # A small real waveform file for inspecting/exercising the extractor.
    sample = waveform(np.random.default_rng(seed + 1), label=0)
    np.savetxt(output / "sample_ecg.csv", sample, delimiter=",", header="ecg", comments="", fmt="%.8f")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="datasets/sample")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-waveforms", action="store_true")
    args = parser.parse_args()
    generate(args.output, args.seed, args.save_waveforms)


if __name__ == "__main__":
    main()
