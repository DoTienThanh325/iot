import math
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
from typing import Dict, Any, List, Tuple

def butter_bandpass(lowcut: float, highcut: float, fs: int, order: int = 4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def filter_ecg_signal(samples: List[float], fs: int = 125) -> np.ndarray:
    """Bandpass Butterworth filter: Order 4, 0.5 Hz - 40 Hz"""
    if len(samples) < 30:
        return np.array(samples, dtype=float)
    b, a = butter_bandpass(0.5, 40.0, fs, order=4)
    filtered = filtfilt(b, a, np.array(samples, dtype=float))
    return filtered

def extract_hrv_features(samples: List[float], fs: int = 125) -> Dict[str, Any]:
    """
    Module 3: Preprocessing AD8232 ECG Signal & Extracting 5 Key HRV Features
    - HR_mean (BPM)
    - RMSSD (ms)
    - pNN50 (%)
    - CV_RR (ratio)
    - Shannon_H (Shannon Entropy)
    """
    if not samples or len(samples) < fs * 3:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Không đủ mẫu tín hiệu ECG (Cần tối thiểu 3 giây).",
            "features": None
        }

    # 1. Filter ECG
    filtered = filter_ecg_signal(samples, fs)

    # 2. Peak Detection (adaptive distance based on minimum physiological RR ~300ms)
    # 300ms @ 125Hz = ~37 samples. Min height based on signal percentile
    min_distance = int(0.3 * fs)  # 300 ms
    height_threshold = np.percentile(filtered, 70)
    peaks, properties = find_peaks(filtered, distance=min_distance, height=height_threshold)

    # If peak count is too low, try standard peak detection with lower threshold
    if len(peaks) < 6:
        height_threshold = np.mean(filtered) + 0.5 * np.std(filtered)
        peaks, properties = find_peaks(filtered, distance=min_distance, height=height_threshold)

    # Check lead off (Section 4.3 Step 1: valid peaks < 6 in 10s -> ECG_LEAD_OFF)
    if len(peaks) < 6:
        return {
            "status": "ECG_LEAD_OFF",
            "message": "Tuột điện cực AD8232 hoặc tín hiệu quá yếu (< 6 đỉnh R).",
            "features": None
        }

    # 3. Compute RR intervals in milliseconds
    raw_rr = (np.diff(peaks) / fs) * 1000.0  # ms

    # Filter out non-physiological artifacts (300ms <= RR <= 2000ms)
    valid_rr = raw_rr[(raw_rr >= 300.0) & (raw_rr <= 2000.0)]

    if len(valid_rr) < 5:
        return {
            "status": "NOISY_SIGNAL",
            "message": "Tín hiệu điện tim quá nhiễu sau khi lọc khoảng RR.",
            "features": None
        }

    # 4. Feature 1: Mean Heart Rate (HR_mean)
    mean_rr = float(np.mean(valid_rr))
    hr_mean = float(60000.0 / mean_rr) if mean_rr > 0 else 0.0

    # Feature 2: RMSSD (Root Mean Square of Successive Differences)
    diff_rr = np.diff(valid_rr)
    rmssd = float(np.sqrt(np.mean(diff_rr**2))) if len(diff_rr) > 0 else 0.0

    # Feature 3: pNN50 (% of successive intervals differing by > 50ms)
    if len(diff_rr) > 0:
        nn50 = np.sum(np.abs(diff_rr) > 50.0)
        pnn50 = float((nn50 / len(diff_rr)) * 100.0)
    else:
        pnn50 = 0.0

    # Feature 4: CV_RR (Coefficient of Variation of RR intervals)
    std_rr = float(np.std(valid_rr))
    cv_rr = float(std_rr / mean_rr) if mean_rr > 0 else 0.0

    # Feature 5: Shannon Entropy (Shannon_H)
    # Bin RR intervals into histogram with 16 bins
    counts, _ = np.histogram(valid_rr, bins=10)
    probs = counts / np.sum(counts)
    probs = probs[probs > 0]
    shannon_h = float(-np.sum(probs * np.log2(probs))) if len(probs) > 0 else 0.0

    return {
        "status": "SUCCESS",
        "peaks_count": len(peaks),
        "valid_rr_count": len(valid_rr),
        "features": {
            "HR_mean": round(hr_mean, 2),
            "RMSSD": round(rmssd, 2),
            "pNN50": round(pnn50, 2),
            "CV_RR": round(cv_rr, 4),
            "Shannon_H": round(shannon_h, 4)
        }
    }
