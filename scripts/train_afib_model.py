#!/usr/bin/env python3
"""
Script: train_afib_model.py
Trains a Random Forest Classifier on 5 Key HRV Features based on
clinical distributions from MIT-BIH Atrial Fibrillation & Arrhythmia benchmarks:
- HR_mean
- RMSSD
- pNN50
- CV_RR
- Shannon_H
Saves the model to ai_service_fastapi/app/models/afib_rf_model.pkl
"""

import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

def generate_synthetic_mitbih_hrv_dataset(n_samples=2500, random_state=42):
    np.random.seed(random_state)
    n_class = n_samples // 2

    # Class 0: Normal Sinus Rhythm (NSR)
    hr_nsr = np.random.normal(loc=74.0, scale=8.0, size=n_class)
    rmssd_nsr = np.random.normal(loc=35.0, scale=10.0, size=n_class)
    pnn50_nsr = np.random.normal(loc=12.0, scale=6.0, size=n_class)
    cv_rr_nsr = np.random.normal(loc=0.05, scale=0.015, size=n_class)
    shannon_h_nsr = np.random.normal(loc=1.15, scale=0.18, size=n_class)

    X_nsr = np.column_stack([hr_nsr, rmssd_nsr, pnn50_nsr, cv_rr_nsr, shannon_h_nsr])
    y_nsr = np.zeros(n_class, dtype=int)

    # Class 1: Atrial Fibrillation (AFib)
    hr_afib = np.random.normal(loc=115.0, scale=20.0, size=n_class)
    rmssd_afib = np.random.normal(loc=140.0, scale=30.0, size=n_class)
    pnn50_afib = np.random.normal(loc=68.0, scale=12.0, size=n_class)
    cv_rr_afib = np.random.normal(loc=0.19, scale=0.04, size=n_class)
    shannon_h_afib = np.random.normal(loc=2.05, scale=0.22, size=n_class)

    X_afib = np.column_stack([hr_afib, rmssd_afib, pnn50_afib, cv_rr_afib, shannon_h_afib])
    y_afib = np.ones(n_class, dtype=int)

    # Ensure physical lower bounds
    X = np.vstack([X_nsr, X_afib])
    y = np.concatenate([y_nsr, y_afib])

    X[:, 0] = np.clip(X[:, 0], 40.0, 200.0)  # HR
    X[:, 1] = np.clip(X[:, 1], 5.0, 300.0)   # RMSSD
    X[:, 2] = np.clip(X[:, 2], 0.0, 100.0)   # pNN50
    X[:, 3] = np.clip(X[:, 3], 0.01, 0.5)    # CV_RR
    X[:, 4] = np.clip(X[:, 4], 0.1, 4.0)     # Shannon_H

    return X, y

def main():
    print("Generating training dataset based on MIT-BIH clinical distributions...")
    X, y = generate_synthetic_mitbih_hrv_dataset(n_samples=4000)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("Training Random Forest Classifier (n_estimators=100)...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Validation Accuracy: {acc * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Normal Sinus", "AFib"]))

    # Output directory
    output_dir = os.path.join(os.path.dirname(__file__), "..", "ai_service_fastapi", "app", "models")
    os.makedirs(output_dir, exist_ok=True)
    model_file = os.path.join(output_dir, "afib_rf_model.pkl")

    joblib.dump(clf, model_file)
    print(f"Model saved successfully to: {model_file}")

if __name__ == "__main__":
    main()
