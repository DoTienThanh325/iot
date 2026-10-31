import hashlib
import json

import numpy as np
import pandas as pd
import pytest
import joblib

from app.algorithms.v2.afib import AFibPredictor
from app.algorithms.v2.ecg import FEATURES
from app.algorithms.v2.ecg import extract_features
from app.config import Settings
from app.main import app
from tests.conftest import window
from training.data import load_features
from training.extract_features import extract
from training.generate_sample_data import generate
from training.train_baseline import train


class ReversedLabels:
    n_features_in_ = 5
    classes_ = np.array([1, 0])

    def predict_proba(self, x):
        return np.tile([.8, .2], (len(x), 1))


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    folder = tmp_path_factory.mktemp("training")
    generate(folder / "data", save_waveforms=True)
    metadata, report = train(folder / "data/features.csv", folder / "model",
                             allow_synthetic=True, trees=10, bootstrap=10)
    return folder, metadata, report


def test_training_requires_explicit_demo_opt_in(tmp_path):
    generate(tmp_path / "data")
    with pytest.raises(ValueError, match="allow-synthetic"):
        train(tmp_path / "data/features.csv", tmp_path / "model")


def test_subject_leakage_is_rejected(tmp_path):
    generate(tmp_path)
    frame = pd.read_csv(tmp_path / "features.csv")
    frame.loc[0, "split"] = "test"
    frame.to_csv(tmp_path / "leak.csv", index=False)
    with pytest.raises(ValueError, match="Subject leakage"):
        load_features(tmp_path / "leak.csv")


def test_artifact_load_predict_and_synthetic_guard(artifact):
    folder, metadata, report = artifact
    assert metadata["synthetic_data"] is True
    assert report["clinical_validation"] is False
    blocked = AFibPredictor(Settings(model_dir=str(folder / "model"), model_required=True))
    blocked.load()
    assert not blocked.ready
    predictor = AFibPredictor(Settings(model_dir=str(folder / "model"), allow_synthetic_model=True))
    predictor.load()
    assert predictor.model is not None
    frame = load_features(folder / "data/features.csv")
    features = frame.iloc[0][FEATURES].to_dict()
    result = predictor.classify({"quality_status": "VALID", "metrics": {"features": features}})
    assert result["inference_source"] == "model"
    expected = predictor.model.predict_proba(np.array([[features[f] for f in FEATURES]]))[0, 1]
    assert result["afib_probability"] == expected


def test_artifact_checksum_and_schema_are_enforced(artifact, tmp_path):
    folder, metadata, _ = artifact
    (tmp_path / "afib_rf_model.pkl").write_bytes((folder / "model/afib_rf_model.pkl").read_bytes())
    bad = dict(metadata, model_sha256="0" * 64)
    (tmp_path / "metadata.json").write_text(json.dumps(bad))
    predictor = AFibPredictor(Settings(model_dir=str(tmp_path), allow_synthetic_model=True, model_required=True))
    predictor.load()
    assert predictor.model is None
    bad = dict(metadata, feature_order=list(reversed(FEATURES)))
    (tmp_path / "metadata.json").write_text(json.dumps(bad))
    predictor.load()
    assert predictor.model is None


def test_training_and_inference_extraction_match(artifact):
    folder, _, _ = artifact
    extract(folder / "data/manifest.csv", folder / "reextracted.csv")
    expected = pd.read_csv(folder / "data/features.csv")
    actual = pd.read_csv(folder / "reextracted.csv")
    assert np.allclose(expected[FEATURES], actual[FEATURES], atol=1e-9)


def test_predictor_uses_label_mapping_instead_of_second_column(artifact, tmp_path):
    _, metadata, _ = artifact
    model_path = tmp_path / "afib_rf_model.pkl"
    joblib.dump(ReversedLabels(), model_path)
    metadata = dict(metadata, classes=[1, 0], model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest())
    (tmp_path / "metadata.json").write_text(json.dumps(metadata))
    predictor = AFibPredictor(Settings(model_dir=str(tmp_path), allow_synthetic_model=True))
    predictor.load()
    assert predictor.model is not None
    features = dict(zip(FEATURES, [75, 100, 50, .12, 1.5]))
    result = predictor.classify({"quality_status": "VALID", "metrics": {"features": features}})
    assert result["afib_probability"] == .8


def test_model_probability_matches_actual_api_pipeline(artifact, client):
    folder, _, _ = artifact
    predictor = AFibPredictor(Settings(model_dir=str(folder / "model"), allow_synthetic_model=True))
    predictor.load()
    app.state.runtime["predictor"] = predictor
    samples = pd.read_csv(folder / "data/sample_ecg.csv")["ecg"].tolist()
    result = client.post("/api/v2/analyze", json=window(
        seconds=20, ecg={"fs": 125, "unit": "mV", "samples": samples}))
    assert result.status_code == 200, result.text
    expected = predictor.classify(extract_features(samples, 125, Settings()))
    assert result.json()["afib"]["afib_probability"] == expected["afib_probability"]
    assert result.json()["afib"]["inference_source"] == "model"
