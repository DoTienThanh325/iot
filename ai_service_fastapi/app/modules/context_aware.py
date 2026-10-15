import numpy as np
from typing import Dict, Any, List

def evaluate_context(spo2_values: List[float], ax: List[float], ay: List[float], az: List[float]) -> Dict[str, Any]:
    """
    Module 1: Context-aware False Alarm Filter
    Cross-checks SpO2 readings against motion intensity (MPU6050)
    to differentiate real hypoxia from motion artifacts / loose sensors.
    """
    if not spo2_values:
        return {
            "context_status": "NORMAL",
            "severity": "INFO",
            "mean_spo2": 98.0,
            "motion_std_svm": 0.0,
            "message": "Không đủ dữ liệu SpO2"
        }

    mean_spo2 = float(np.mean(spo2_values))

    # Calculate Signal Vector Magnitude (SVM) for acceleration
    if ax and ay and az and len(ax) == len(ay) == len(az) and len(ax) > 0:
        ax_arr = np.array(ax, dtype=float)
        ay_arr = np.array(ay, dtype=float)
        az_arr = np.array(az, dtype=float)
        svm_arr = np.sqrt(ax_arr**2 + ay_arr**2 + az_arr**2)
        motion_std_svm = float(np.std(svm_arr))
    else:
        motion_std_svm = 0.0

    # Decision Matrix
    if mean_spo2 >= 95.0:
        context_status = "NORMAL"
        severity = "INFO"
        message = "Chỉ số SpO2 và vận động bình thường."
    elif 92.0 <= mean_spo2 < 95.0:
        if motion_std_svm <= 0.15:
            context_status = "MILD_HYPOXIA"
            severity = "WARNING"
            message = "SpO2 giảm nhẹ, cần theo dõi hô hấp."
        else:
            context_status = "NORMAL"
            severity = "INFO"
            message = "SpO2 biến động nhẹ do vận động."
    else:  # mean_spo2 < 92.0%
        if motion_std_svm > 0.15:
            context_status = "SENSOR_LOOSE"
            severity = "NOISE"
            message = "Nhiễu tín hiệu / Lỏng cảm biến SpO2 do chuyển động (Chặn báo động giả)."
        else:
            context_status = "RESPIRATORY_RISK"
            severity = "CRITICAL"
            message = "Nguy cơ suy hô hấp cấp (SpO2 < 92% khi cơ thể bất động)!"

    return {
        "context_status": context_status,
        "severity": severity,
        "mean_spo2": round(mean_spo2, 2),
        "motion_std_svm": round(motion_std_svm, 4),
        "message": message
    }
