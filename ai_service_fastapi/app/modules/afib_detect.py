import os
import logging
import joblib
import numpy as np
from typing import Dict, Any

logger = logging.getLogger("ai_service.afib_detect")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "afib_rf_model.pkl")

class AFibDetector:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                logger.info(f"Loaded Random Forest AFib model from {MODEL_PATH}")
            except Exception as e:
                logger.warning(f"Failed to load RF model: {e}. Falling back to rule-based engine.")
        else:
            logger.info("RF model file not found. Hybrid medical rule-based scoring will be used.")

    def _heuristic_afib_prob(self, hrv: Dict[str, float]) -> float:
        """
        Clinical rule-based probability scoring when model weights are not loaded.
        HRV metrics: HR_mean, RMSSD, pNN50, CV_RR, Shannon_H
        """
        score = 0.0
        rmssd = hrv.get("RMSSD", 0.0)
        pnn50 = hrv.get("pNN50", 0.0)
        cv_rr = hrv.get("CV_RR", 0.0)
        shannon_h = hrv.get("Shannon_H", 0.0)

        # RMSSD contribution (>=100ms indicates heavy irregularity)
        if rmssd >= 100.0:
            score += 0.35
        elif rmssd >= 66.0:
            score += 0.15

        # pNN50 contribution (>=50% indicates rapid successive variations)
        if pnn50 >= 50.0:
            score += 0.30
        elif pnn50 >= 25.0:
            score += 0.15

        # CV_RR contribution (>=0.12 shows high dispersion)
        if cv_rr >= 0.12:
            score += 0.25
        elif cv_rr >= 0.08:
            score += 0.10

        # Shannon Entropy (>=1.80 shows chaotic dynamics)
        if shannon_h >= 1.80:
            score += 0.10
        elif shannon_h >= 1.40:
            score += 0.05

        return min(max(score, 0.02), 0.99)

    def classify(self, hrv_features: Dict[str, float]) -> Dict[str, Any]:
        """
        Step 3: Hybrid Decision Logic (Random Forest + Clinical Medical Guidelines)
        """
        if not hrv_features:
            return {
                "afib_detected": False,
                "afib_probability": 0.0,
                "decision_class": "UNKNOWN",
                "recommendation": "Không có đặc trưng HRV để phân tích."
            }

        rmssd = hrv_features.get("RMSSD", 0.0)
        pnn50 = hrv_features.get("pNN50", 0.0)
        cv_rr = hrv_features.get("CV_RR", 0.0)
        shannon_h = hrv_features.get("Shannon_H", 0.0)
        hr_mean = hrv_features.get("HR_mean", 75.0)

        feature_vector = np.array([[hr_mean, rmssd, pnn50, cv_rr, shannon_h]])

        if self.model is not None:
            try:
                probs = self.model.predict_proba(feature_vector)[0]
                # Assuming index 1 corresponds to AFib class
                p_afib = float(probs[1]) if len(probs) > 1 else float(probs[0])
            except Exception as e:
                logger.error(f"Error predicting with model: {e}")
                p_afib = self._heuristic_afib_prob(hrv_features)
        else:
            p_afib = self._heuristic_afib_prob(hrv_features)

        # Hybrid Decision Rules (Section 4.3 Step 3):
        # 1. AFIB_HIGH_RISK: P(AFib) >= 0.70 OR (RMSSD >= 100 AND pNN50 >= 50% AND CV_RR >= 0.12)
        if p_afib >= 0.70 or (rmssd >= 100.0 and pnn50 >= 50.0 and cv_rr >= 0.12):
            decision_class = "AFIB_HIGH_RISK"
            afib_detected = True
            recommendation = "Phát hiện bất thường điện tim (Rung nhĩ - AFib) - Khuyến nghị tầm soát nguy cơ đột quỵ khẩn cấp!"
        # 2. ARRHYTHMIA_WARNING: 0.45 <= P < 0.70 OR at least 1 feature in suspect zone
        elif (0.45 <= p_afib < 0.70) or (66.0 <= rmssd < 100.0) or (25.0 <= pnn50 < 50.0) or (0.08 <= cv_rr < 0.12) or (1.40 <= shannon_h < 1.80):
            decision_class = "ARRHYTHMIA_WARNING"
            afib_detected = False
            recommendation = "Điện tim có dấu hiệu loạn nhịp nhẹ, tiếp tục theo dõi biến thiên nhịp tim."
        # 3. NORMAL_SINUS
        else:
            decision_class = "NORMAL_SINUS"
            afib_detected = False
            recommendation = "Điện tim nhịp xoang đều bình thường."

        return {
            "afib_detected": afib_detected,
            "afib_probability": round(p_afib, 4),
            "decision_class": decision_class,
            "recommendation": recommendation
        }

afib_detector = AFibDetector()
