"""Validated runtime configuration. Algorithm defaults are research settings."""
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    storage_mode: Literal["mongo", "memory"] = "mongo"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "iot_stroke_db"
    mongo_timeout_ms: int = Field(default=3000, ge=100, le=30000)
    model_dir: str | None = None
    model_required: bool = False
    allow_synthetic_model: bool = False
    max_concurrency: int = Field(default=2, ge=1, le=32)
    acquire_timeout: float = Field(default=0.1, gt=0, le=10)
    max_sessions: int = Field(default=1000, ge=1)
    max_windows_memory: int = Field(default=10000, ge=1)
    max_samples: int = Field(default=30000, ge=100, le=100000)
    max_body_bytes: int = Field(default=4000000, ge=1024, le=20000000)
    max_window_seconds: float = Field(default=60, gt=0, le=120)
    max_gap_seconds: float = Field(default=2, gt=0)
    spo2_low: float = Field(default=92, ge=50, le=100)
    spo2_clear: float = Field(default=95, ge=50, le=100)
    spo2_confirm_seconds: float = Field(default=10, gt=0)
    spo2_clear_seconds: float = Field(default=5, gt=0)
    impact_g: float = Field(default=2.5, gt=1)
    tilt_degrees: float = Field(default=55, gt=0, le=180)
    post_seconds: float = Field(default=3, ge=1, le=10)
    immobility_rms: float = Field(default=0.06, gt=0)
    ecg_min_seconds: float = Field(default=10, ge=3, le=60)
    ecg_low_hz: float = Field(default=0.5, gt=0)
    ecg_high_hz: float = Field(default=40, gt=0)
    afib_warning_score: float = Field(default=0.45, ge=0, le=1)
    afib_high_score: float = Field(default=0.70, ge=0, le=1)

    @model_validator(mode="after")
    def ordered_thresholds(self):
        if self.spo2_clear <= self.spo2_low:
            raise ValueError("spo2_clear must exceed spo2_low")
        if self.ecg_low_hz >= self.ecg_high_hz:
            raise ValueError("Invalid ECG band")
        if self.afib_warning_score >= self.afib_high_score:
            raise ValueError("Invalid AFib thresholds")
        if self.model_required and not self.model_dir:
            raise ValueError("MODEL_DIR is required when MODEL_REQUIRED=true")
        return self

    @classmethod
    def from_env(cls):
        values = {}
        for name in cls.model_fields:
            key = "AI_" + name.upper()
            # Preserve existing deployment environment names.
            if name in {"mongo_uri", "mongo_db"}:
                key = name.upper()
            if key in os.environ:
                values[name] = os.environ[key]
        return cls(**values)
