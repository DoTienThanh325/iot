#!/usr/bin/env python3
"""
Script: esp32_simulator.py
Simulates ESP32 hardware client sending MQTT messages for 3 Project Scenarios:
1. Normal Stable State (Nhịp xoang đều, sinh hiệu ổn định)
2. Emergency Fall / SOS (Cấp cứu tự động, ngã bất động hoặc bấm SOS)
3. Atrial Fibrillation Stroke Risk (Sóng ECG rung nhĩ, biến thiên nhịp tim hỗn loạn)
"""

import sys
import time
import json
import math
import random
import argparse
import paho.mqtt.client as mqtt

def generate_normal_ecg_sample(t: float) -> int:
    """Generate 1 normal heartbeat ECG value at relative time t within cardiac cycle"""
    # Standard ECG model: P wave, QRS complex, T wave
    cycle_t = t % 0.8  # ~75 BPM (0.8s per beat)
    val = 0.0
    if 0.1 <= cycle_t < 0.18:
        val += 0.15 * math.sin((cycle_t - 0.1) / 0.08 * math.pi)  # P wave
    elif 0.22 <= cycle_t < 0.28:
        # QRS spike
        rel = (cycle_t - 0.22) / 0.06
        if rel < 0.3:
            val -= 0.2
        elif rel < 0.7:
            val += 1.3
        else:
            val -= 0.3
    elif 0.38 <= cycle_t < 0.52:
        val += 0.25 * math.sin((cycle_t - 0.38) / 0.14 * math.pi)  # T wave

    # Baseline + ADC scale (0 - 1023)
    adc_val = int(val * 200 + 512 + random.uniform(-5, 5))
    return adc_val

def generate_afib_ecg_sample(t: float, rr_history: list) -> int:
    """Generate AFib waveform with fibrillatory noise and irregular beat intervals"""
    val = 0.08 * math.sin(2 * math.pi * 5.8 * t) + 0.05 * math.sin(2 * math.pi * 7.5 * t)
    
    # Check if a beat is due based on irregular RR schedule
    last_beat_t = rr_history[-1] if rr_history else 0.0
    time_since_beat = t - last_beat_t
    next_interval = rr_history[-2] if len(rr_history) >= 2 else 0.55

    if time_since_beat >= next_interval:
        # Trigger QRS
        val += 1.2
        rr_history[-1] = t
        # Pick next irregular interval (490ms, 880ms, 530ms, 920ms, etc.)
        next_rrs = [0.49, 0.88, 0.53, 0.92, 0.48, 0.89, 0.52]
        rr_history[-2] = random.choice(next_rrs)

    adc_val = int(val * 200 + 512 + random.uniform(-8, 8))
    return adc_val

def run_simulation(host: str, port: int, device_id: str, scenario: int):
    client = mqtt.Client(client_id=f"simulator_{device_id}")
    print(f"Connecting to MQTT Broker {host}:{port}...")
    try:
        client.connect(host, port, 60)
        client.loop_start()
    except Exception as e:
        print(f"Failed to connect to MQTT: {e}")
        return

    print(f"\n==========================================")
    print(f" SIMULATOR ESP32 RUNNING FOR DEVICE: {device_id}")
    print(f" SCENARIO: {scenario}")
    print(f"==========================================\n")

    start_time = time.time()
    last_vitals_time = 0.0
    last_ecg_packet_time = 0.0
    alert_sent = False
    
    # State for Scenario 3
    afib_rr_history = [0.5, 0.0]

    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            # ---------------------------------------------------------
            # 1. VITALS TOPIC: 1 Hz (Every 1 second)
            # ---------------------------------------------------------
            if current_time - last_vitals_time >= 1.0:
                last_vitals_time = current_time
                now_ts = int(current_time)

                if scenario == 1:
                    # Scenario 1: Stable Normal State
                    vitals_payload = {
                        "device_id": device_id,
                        "ts": now_ts,
                        "bpm": round(75.0 + random.uniform(-2, 2), 1),
                        "spo2": round(98.0 + random.uniform(-0.5, 0.5), 1),
                        "temp": 36.6,
                        "ax": round(0.01 + random.uniform(-0.02, 0.02), 3),
                        "ay": round(-0.02 + random.uniform(-0.02, 0.02), 3),
                        "az": round(0.99 + random.uniform(-0.02, 0.02), 3)
                    }
                elif scenario == 2:
                    # Scenario 2: Emergency Fall
                    if elapsed < 5:
                        # Walking normally
                        vitals_payload = {
                            "device_id": device_id,
                            "ts": now_ts,
                            "bpm": 80.0,
                            "spo2": 97.5,
                            "temp": 36.7,
                            "ax": 0.1, "ay": -0.15, "az": 0.98
                        }
                    elif elapsed < 7:
                        # Heavy Impact (SVM = 3.2g)
                        vitals_payload = {
                            "device_id": device_id,
                            "ts": now_ts,
                            "bpm": 118.0,
                            "spo2": 96.0,
                            "temp": 36.7,
                            "ax": 2.2, "ay": 1.8, "az": 1.4  # SVM ~ 3.17g
                        }
                    else:
                        # Post-fall motionless (patient on floor)
                        vitals_payload = {
                            "device_id": device_id,
                            "ts": now_ts,
                            "bpm": 115.0,
                            "spo2": 95.0,
                            "temp": 36.7,
                            "ax": 0.01, "ay": 0.85, "az": 0.02 # horizontal tilt, static
                        }
                elif scenario == 3:
                    # Scenario 3: Atrial Fibrillation Tachycardia
                    vitals_payload = {
                        "device_id": device_id,
                        "ts": now_ts,
                        "bpm": round(116.0 + random.uniform(-5, 8), 1),
                        "spo2": 96.5,
                        "temp": 36.8,
                        "ax": 0.02, "ay": -0.01, "az": 0.99
                    }

                client.publish(f"device/{device_id}/vitals", json.dumps(vitals_payload), qos=1)
                print(f"[VITALS] Sent @ {now_ts} -> BPM: {vitals_payload['bpm']}, SpO2: {vitals_payload['spo2']}%")

            # ---------------------------------------------------------
            # 2. EMERGENCY ALERT TOPIC (Instantaneous for Scenario 2)
            # ---------------------------------------------------------
            if scenario == 2 and elapsed >= 6 and not alert_sent:
                alert_sent = True
                alert_payload = {
                    "device_id": device_id,
                    "ts": int(current_time),
                    "alert_type": "EDGE_FALL_DETECTED",
                    "bpm": 118.0,
                    "max_svm": 3.2,
                    "severity": "CRITICAL"
                }
                client.publish(f"device/{device_id}/alert", json.dumps(alert_payload), qos=2)
                print(f"\n🚨 [ALERT] Sent EDGE_FALL_DETECTED -> max_svm: 3.2g, BPM: 118.0!\n")

            # ---------------------------------------------------------
            # 3. ECG TOPIC: 5 packets/sec (Each 25 samples @ 125 Hz = 200ms per packet)
            # ---------------------------------------------------------
            if current_time - last_ecg_packet_time >= 0.2:
                last_ecg_packet_time = current_time
                samples = []
                for s in range(25):
                    t = elapsed + (s / 125.0)
                    if scenario == 3:
                        samples.append(generate_afib_ecg_sample(t, afib_rr_history))
                    else:
                        samples.append(generate_normal_ecg_sample(t))

                ecg_payload = {
                    "device_id": device_id,
                    "ts": int(current_time),
                    "fs": 125,
                    "samples": samples
                }
                client.publish(f"device/{device_id}/ecg", json.dumps(ecg_payload), qos=0)

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nSimulator stopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32 MQTT Hardware Simulator")
    parser.add_argument("--host", default="localhost", help="MQTT Broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT Broker port")
    parser.add_argument("--device", default="esp32_01", help="Device ID")
    parser.add_argument("--scenario", type=int, choices=[1, 2, 3], default=1,
                        help="1: Stable Normal, 2: Fall Emergency, 3: AFib Stroke Risk")
    args = parser.parse_args()

    run_simulation(args.host, args.port, args.device, args.scenario)
