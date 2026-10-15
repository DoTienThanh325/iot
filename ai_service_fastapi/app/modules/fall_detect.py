import numpy as np
from typing import Dict, Any, List

def evaluate_fall(
    ax: List[float],
    ay: List[float],
    az: List[float],
    bpm_values: List[float] = None
) -> Dict[str, Any]:
    """
    Module 2: 3-Phase Fall Detection Verification Algorithm (MPU6050 + BPM)
    Validates impact, orientation change, post-fall immobility, and heart rate shift.
    """
    if not ax or len(ax) < 5:
        return {
            "fall_status": "NO_FALL",
            "max_svm": 0.0,
            "delta_theta": 0.0,
            "sigma_post": 0.0,
            "delta_bpm": 0.0,
            "message": "Không đủ dữ liệu gia tốc."
        }

    ax_arr = np.array(ax, dtype=float)
    ay_arr = np.array(ay, dtype=float)
    az_arr = np.array(az, dtype=float)

    svm_arr = np.sqrt(ax_arr**2 + ay_arr**2 + az_arr**2)
    max_idx = int(np.argmax(svm_arr))
    max_svm = float(svm_arr[max_idx])

    # Phase 1: Peak Impact check
    phase1_impact = max_svm >= 2.5

    # Phase 2: Posture tilt angle change (theta = arccos(az / SVM) * 180 / pi)
    # Compare pre-impact posture (before max_idx) with post-impact posture (after max_idx)
    clipped_az = np.clip(az_arr / np.maximum(svm_arr, 1e-6), -1.0, 1.0)
    theta_arr = np.arccos(clipped_az) * (180.0 / np.pi)

    pre_idx = max(0, max_idx - 3)
    post_idx = min(len(theta_arr) - 1, max_idx + 3)
    delta_theta = float(abs(theta_arr[post_idx] - theta_arr[pre_idx]))
    phase2_tilt = delta_theta >= 55.0

    # Phase 3: Post-fall immobility (std deviation in 3-5 seconds after impact)
    post_impact_slice = svm_arr[max_idx + 1:]
    if len(post_impact_slice) >= 3:
        sigma_post = float(np.std(post_impact_slice))
    else:
        sigma_post = float(np.std(svm_arr))
    
    phase3_immobility = sigma_post <= 0.06

    # Phase 4: Heart rate delta verification
    delta_bpm = 0.0
    phase4_vitals = False
    if bpm_values and len(bpm_values) >= 2:
        bpm_pre = bpm_values[0]
        bpm_post = bpm_values[-1]
        delta_bpm = float(abs(bpm_post - bpm_pre))
        if delta_bpm >= 15.0 or bpm_post > 120.0 or bpm_post < 45.0:
            phase4_vitals = True

    # Decision Matrix
    if phase1_impact and phase2_tilt and phase3_immobility:
        fall_status = "FALL_CONFIRMED"
        message = "Bệnh nhân ngã / Mất ý thức (Thỏa mãn 3 pha va chạm, đổi tư thế và bất động)!"
    elif phase1_impact and sigma_post > 0.15:
        fall_status = "FALSE_IMPACT"
        message = "Chỉ là va quệt tay hoặc rung lắc thông thường, cơ thể vẫn cử động linh hoạt."
    elif phase1_impact:
        fall_status = "POTENTIAL_IMPACT"
        message = "Ghi nhận va đập mạnh nhưng chưa đủ bằng chứng bất động sau ngã."
    else:
        fall_status = "NO_FALL"
        message = "Không phát hiện sự kiện ngã."

    return {
        "fall_status": fall_status,
        "max_svm": round(max_svm, 2),
        "delta_theta": round(delta_theta, 1),
        "sigma_post": round(sigma_post, 4),
        "delta_bpm": round(delta_bpm, 1),
        "vitals_confirmed": phase4_vitals,
        "message": message
    }
