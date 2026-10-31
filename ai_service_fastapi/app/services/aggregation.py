import hashlib
from datetime import datetime, timezone


def aggregate(request, context, fall, afib, state):
    events = []

    def add(kind, severity, start, end, evidence, quality):
        identity = f"{request.device_id}|{request.session_id}|{kind}|{start:.6f}"
        events.append({
            "event_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
            "type": kind, "severity": severity,
            "start_time": datetime.fromtimestamp(start, timezone.utc),
            "end_time": datetime.fromtimestamp(end, timezone.utc),
            "evidence": evidence, "quality_status": quality,
        })

    for episode in context["metrics"].get("episodes", []):
        severity = "CRITICAL" if episode["persistent"] and context["quality_status"] == "VALID" else "WARNING"
        evidence = {key: value for key, value in context["metrics"].items() if key != "episodes"}
        evidence["episode"] = episode
        add("LOW_SPO2", severity, episode["event_start"], episode["event_end"],
            evidence, context["quality_status"])
    for item in fall["metrics"]["completed_candidates"]:
        if item["status"] == "FALL_SUSPECTED":
            add("FALL_SUSPECTED", "CRITICAL", item["event_start"], item["event_end"],
                item, fall["quality_status"])
    if afib["analysis_status"] in {"AFIB_SUSPECTED", "IRREGULARITY_WARNING"}:
        start = request.start_time.timestamp()
        prior = state.get("afib_event")
        if prior and start <= prior["end"] + state["max_gap_seconds"]:
            start = prior["start"]
        state["afib_event"] = {"start": start, "end": request.end_time.timestamp()}
        add("ECG_IRREGULARITY", "WARNING", start, request.end_time.timestamp(),
            {"inference_source": afib["inference_source"],
             "afib_probability": afib["afib_probability"],
             "heuristic_score": afib["heuristic_score"]}, afib["quality_status"])
    else:
        state.pop("afib_event", None)
    if events:
        severity = "CRITICAL" if any(e["severity"] == "CRITICAL" for e in events) else "WARNING"
        kinds = ", ".join(sorted({event["type"] for event in events}))
        recommendation = f"Có sự kiện cần kiểm tra: {kinds}. Xem bằng chứng và chất lượng từng tín hiệu."
    else:
        valid = [context, fall, afib]
        severity = "INFO" if any(r["quality_status"] == "VALID" and r["analysis_status"] not in {"PENDING", "UNDETERMINED"} for r in valid) else "UNKNOWN"
        recommendation = "Chưa ghi nhận sự kiện trong dữ liệu phân tích được; kiểm tra các nhóm thiếu hoặc kém chất lượng."
    return events, severity, recommendation
