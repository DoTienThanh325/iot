"""Extract from labeled window manifests. CSV signals have one 'ecg' column."""
import argparse
from pathlib import Path

import pandas as pd

from app.algorithms.v2.ecg import EXTRACTOR_VERSION, extract_features
from app.config import Settings


def extract(manifest_path, output_path):
    source = Path(manifest_path)
    manifest = pd.read_csv(source, keep_default_na=False,
                           dtype={"subject_id": str, "record_id": str})
    required = {"subject_id", "record_id", "split", "label", "data_origin", "signal_path",
                "fs", "unit", "start_sample", "end_sample"}
    if not required.issubset(manifest.columns):
        raise ValueError("Missing manifest columns")
    rows, audit = [], []
    for row in manifest.to_dict("records"):
        path = (source.parent / row["signal_path"]).resolve()
        if not row["signal_path"] or not path.is_file():
            raise ValueError(f"Signal file missing for {row['record_id']}; generate with --save-waveforms")
        if row["unit"] not in {"mV", "adc"}:
            raise ValueError("Unsupported ECG unit")
        signal = pd.read_csv(path)["ecg"].to_numpy(dtype=float)
        start, end = int(row["start_sample"]), int(row["end_sample"])
        if not 0 <= start < end <= len(signal):
            raise ValueError("Invalid sample interval")
        result = extract_features(signal[start:end], float(row["fs"]), Settings())
        audit.append({"record_id": row["record_id"], "quality_status": result["quality_status"],
                      "analysis_status": result["analysis_status"], "label": row["label"]})
        if result["quality_status"] == "VALID":
            rows.append({key: row[key] for key in ["subject_id", "record_id", "split", "label", "data_origin"]}
                        | {"extractor_version": EXTRACTOR_VERSION} | result["metrics"]["features"])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audit).to_csv(output.with_suffix(".audit.csv"), index=False)
    if not rows:
        raise ValueError("No accepted windows; consult audit")
    pd.DataFrame(rows).to_csv(output, index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    extract(args.manifest, args.output)


if __name__ == "__main__":
    main()
