"""One extractor shared by training and inference; offline window processing."""
from functools import lru_cache

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

EXTRACTOR_VERSION = "ecg-v2.0-offline"
FEATURES = ["HR_mean", "RMSSD", "pNN50", "CV_RR", "Shannon_H"]


@lru_cache(maxsize=32)
def filter_coefficients(fs, low, high):
    return butter(4, [low, high], fs=fs, btype="bandpass", output="sos")


def extract_features(samples, fs, config, lead_off=False):
    metrics = {"extractor_version": EXTRACTOR_VERSION, "features": None,
               "peaks_count": 0, "valid_rr_count": 0}

    def result(quality, status):
        return {"quality_status": quality, "analysis_status": status, "metrics": metrics}

    if samples is None or len(samples) == 0:
        return result("NO_DATA", "UNDETERMINED")
    x = np.asarray(samples, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all() or fs <= 2 * config.ecg_high_hz:
        return result("LOW_QUALITY", "INVALID_SIGNAL")
    metrics["duration_seconds"] = len(x) / fs
    if lead_off:
        return result("LOW_QUALITY", "ECG_LEAD_OFF")
    if len(x) < fs * config.ecg_min_seconds:
        return result("INSUFFICIENT_DATA", "SHORT_WINDOW")
    if np.ptp(x) < 1e-9:
        return result("LOW_QUALITY", "FLAT_SIGNAL")
    # A repeated extreme is a conservative saturation indicator, not a full SQI.
    saturation = max(np.mean(x == x.min()), np.mean(x == x.max()))
    metrics["saturation_ratio"] = float(saturation)
    if saturation > 0.20:
        return result("LOW_QUALITY", "SATURATED_SIGNAL")
    filtered = sosfiltfilt(filter_coefficients(float(fs), config.ecg_low_hz,
                                              config.ecg_high_hz), x)
    # Select dominant polarity before adaptive prominence peak detection.
    centered = filtered - np.median(filtered)
    if abs(np.percentile(centered, 1)) > abs(np.percentile(centered, 99)):
        centered = -centered
    scale = float(np.std(centered))
    if scale < 1e-10:
        return result("LOW_QUALITY", "FLAT_SIGNAL")
    peaks, _ = find_peaks(centered, distance=max(1, int(0.3 * fs)),
                          prominence=0.7 * scale, height=0.5 * scale)
    metrics["peaks_count"] = int(len(peaks))
    if len(peaks) < 6:
        return result("INSUFFICIENT_DATA", "INSUFFICIENT_QRS")
    raw_rr = np.diff(peaks) * 1000.0 / fs
    mask = (raw_rr >= 300) & (raw_rr <= 2000)
    valid_rr = raw_rr[mask]
    metrics.update(valid_rr_count=int(mask.sum()), valid_rr_ratio=float(mask.mean()),
                   artifact_ratio=float(1 - mask.mean()))
    if len(valid_rr) < 5 or mask.mean() < 0.8:
        return result("LOW_QUALITY", "NOISY_RR")
    # Do not join RR intervals separated by a rejected interval.
    differences = np.diff(raw_rr)[mask[:-1] & mask[1:]]
    if len(differences) < 3:
        return result("INSUFFICIENT_DATA", "INSUFFICIENT_ADJACENT_RR")
    mean_rr = float(np.mean(valid_rr))
    # Fixed bin edges in milliseconds; definition is part of extractor version.
    counts, _ = np.histogram(valid_rr, bins=np.linspace(300, 2000, 11))
    probabilities = counts[counts > 0] / counts.sum()
    metrics["features"] = {
        "HR_mean": 60000.0 / mean_rr,
        "RMSSD": float(np.sqrt(np.mean(differences ** 2))),
        "pNN50": float(np.mean(abs(differences) > 50) * 100),
        "CV_RR": float(np.std(valid_rr) / mean_rr),
        "Shannon_H": float(-np.sum(probabilities * np.log2(probabilities))),
    }
    return result("VALID", "SUCCESS")
