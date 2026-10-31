from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, Field, StrictFloat, StrictInt,
    field_validator, model_validator,
)

# Strict numeric types reject booleans and numeric strings. Bounds precede NumPy allocation.
Number = Annotated[StrictFloat | StrictInt, Field(allow_inf_nan=False, ge=-1e9, le=1e9)]
Samples = Annotated[list[Number], Field(min_length=1, max_length=100000)]
Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[\w.:-]+$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class AccelWindow(Contract):
    fs: Annotated[Number, Field(ge=5, le=1000)]
    unit: Literal["g", "m/s2"]
    ax: Samples
    ay: Samples
    az: Samples

    @model_validator(mode="after")
    def equal_axes(self):
        if len(self.ax) != len(self.ay) or len(self.ax) != len(self.az):
            raise ValueError("Acceleration axes must have equal lengths")
        return self


class ECGWindow(Contract):
    fs: Annotated[Number, Field(gt=80, le=1000)]
    unit: Literal["mV", "adc"]
    samples: Samples
    lead_off: bool = False


class VitalSample(Contract):
    timestamp: AwareDatetime
    value: Number

    @field_validator("timestamp")
    @classmethod
    def utc(cls, value):
        return value.astimezone(timezone.utc)


class VitalsWindow(Contract):
    spo2: list[VitalSample] = Field(default_factory=list, max_length=10000)
    bpm: list[VitalSample] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def ordered_valid(self):
        for values, low, high in [(self.spo2, 0, 100), (self.bpm, 0, 300)]:
            if any(not low <= sample.value <= high for sample in values):
                raise ValueError("Vital value outside sensor domain")
            if any(a.timestamp >= b.timestamp for a, b in zip(values, values[1:])):
                raise ValueError("Vital timestamps must be strictly increasing")
        return self


class AnalyzeRequestV2(Contract):
    schema_version: Literal["2.0"] = "2.0"
    device_id: Identifier
    session_id: Identifier
    window_id: Identifier
    start_time: AwareDatetime
    end_time: AwareDatetime
    accel: AccelWindow | None = None
    ecg: ECGWindow | None = None
    vitals: VitalsWindow | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def utc(cls, value):
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def timing(self):
        duration = (self.end_time - self.start_time).total_seconds()
        if not 0 < duration <= 120:
            raise ValueError("Window duration must be in (0, 120] seconds")
        # end_time is exclusive: duration = sample_count / fs.
        for sensor in [self.accel, self.ecg]:
            if sensor is not None:
                count = len(sensor.ax) if isinstance(sensor, AccelWindow) else len(sensor.samples)
                if abs(count / sensor.fs - duration) > max(0.001, 0.5 / sensor.fs):
                    raise ValueError("Sample count/fs disagrees with exclusive window interval")
        if self.vitals:
            for sample in self.vitals.spo2 + self.vitals.bpm:
                if not self.start_time <= sample.timestamp < self.end_time:
                    raise ValueError("Vital sample outside window")
        return self


Quality = Literal["NO_DATA", "INSUFFICIENT_DATA", "LOW_QUALITY", "VALID"]


class ModuleResult(Contract):
    quality_status: Quality
    analysis_status: str
    metrics: dict = Field(default_factory=dict)


class AFibResult(ModuleResult):
    afib_detected: bool | None = None
    afib_probability: float | None = None
    heuristic_score: float | None = None
    inference_source: Literal["model", "heuristic", "unavailable"] = "unavailable"
    model_version: str | None = None
    extractor_version: str
    calibrated: bool = False


class Event(Contract):
    event_id: str
    type: str
    severity: Literal["WARNING", "CRITICAL"]
    start_time: datetime
    end_time: datetime
    evidence: dict
    quality_status: Quality


class AnalyzeResponseV2(Contract):
    schema_version: Literal["2.0"] = "2.0"
    algorithm_version: str = "research-v2.0"
    device_id: str
    session_id: str
    window_id: str
    start_time: datetime
    end_time: datetime
    context: ModuleResult
    fall: ModuleResult
    ecg: ModuleResult
    afib: AFibResult
    events: list[Event]
    overall_severity: Literal["UNKNOWN", "INFO", "WARNING", "CRITICAL"]
    recommendation: str
    persistence_status: Literal["stored", "memory_only"]
