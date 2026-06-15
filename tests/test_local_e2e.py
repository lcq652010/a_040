#!/usr/bin/env python3
"""PHM System Local E2E Test (without Docker / InfluxDB)

Starts root-cause-service and a mock LSTM service locally,
then validates the full API chain: anomaly detection -> data processing
-> RUL prediction -> root cause analysis.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import random
import threading
from datetime import datetime

try:
    import requests
except ImportError:
    print("[FAIL] requests library required: pip install requests")
    sys.exit(1)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(os.path.dirname(__file__), "local_e2e_report.txt")

SERVICES = {}
PROCESSES = []


class TestResult:
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()

    def record(self, name, passed, detail="", duration=0.0):
        self.results.append({
            "name": name,
            "passed": passed,
            "detail": detail,
            "duration": round(duration, 2),
        })
        status = "PASS" if passed else "FAIL"
        line = "  [{}] {}".format(status, name)
        if duration > 0:
            line += " ({:.1f}s)".format(duration)
        if not passed:
            line += "\n         Reason: {}".format(detail)
        print(line)

    def passed_count(self):
        return sum(1 for r in self.results if r["passed"])

    def failed_count(self):
        return sum(1 for r in self.results if not r["passed"])

    def total_count(self):
        return len(self.results)

    def generate_report(self):
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        lines = []
        lines.append("=" * 72)
        lines.append("  PHM System Local E2E Test Report")
        lines.append("=" * 72)
        lines.append("  Start : " + self.start_time.strftime("%Y-%m-%d %H:%M:%S"))
        lines.append("  End   : " + end_time.strftime("%Y-%m-%d %H:%M:%S"))
        lines.append("  Total : {:.1f}s".format(duration))
        lines.append("  Mode  : Local services (no Docker / no InfluxDB)")
        lines.append("")
        lines.append("-" * 72)
        lines.append("  {:<6} {:<48} {:>8}".format("Result", "Test Name", "Time"))
        lines.append("-" * 72)
        for r in self.results:
            status = "PASS" if r["passed"] else "FAIL"
            lines.append("  [{}] {:<48} {:>7.1f}s".format(status, r["name"], r["duration"]))
            if not r["passed"] and r["detail"]:
                lines.append("         -> " + r["detail"])
        lines.append("-" * 72)
        total = self.total_count()
        passed = self.passed_count()
        failed = self.failed_count()
        lines.append("  Total: {}  Passed: {}  Failed: {}".format(total, passed, failed))
        overall = "ALL PASSED" if failed == 0 else "HAS FAILURES"
        lines.append("  Result: " + overall)
        lines.append("=" * 72)
        return "\n".join(lines)


def start_service(name, cmd, cwd, port, health_url, timeout=30):
    """Start a service subprocess and wait for it to be healthy."""
    print("  Starting {} on port {}...".format(name, port))
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        PROCESSES.append(proc)

        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(health_url, timeout=2)
                if resp.status_code == 200:
                    print("    [OK] {} is healthy ({:.1f}s)".format(name, time.time() - start))
                    return True
            except requests.RequestException:
                pass

            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout else ""
                print("    [FAIL] {} exited early: {}".format(name, output[:200]))
                return False
            time.sleep(1)

        print("    [FAIL] {} did not become healthy in {}s".format(name, timeout))
        return False
    except Exception as e:
        print("    [FAIL] Failed to start {}: {}".format(name, str(e)))
        return False


def start_mock_lstm_service():
    """Start a mock LSTM service for testing."""
    from flask import Flask, request, jsonify
    app = Flask("mock-lstm")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "lstm-mock"})

    @app.route("/api/predict", methods=["POST"])
    def predict():
        data = request.get_json() or {}
        device_id = data.get("device_id", "unknown")
        device_type = data.get("device_type", "unknown")
        return jsonify({
            "device_id": device_id,
            "device_type": device_type,
            "rul_steps": 850,
            "rul_hours": 23.6,
            "health_score": 82.5,
            "confidence": 0.87,
            "prediction": {"rul": 850, "health": 82.5},
        })

    @app.route("/api/train", methods=["POST"])
    def train():
        return jsonify({"status": "ok", "epochs": 10, "mse": 0.042})

    server = {"app": app, "port": 5000}
    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    time.sleep(2)
    return True


def load_edge_detector():
    """Load edge anomaly detector for testing."""
    import importlib.util
    import sys

    edge_dir = os.path.join(PROJECT_ROOT, "edge-node")
    if edge_dir not in sys.path:
        sys.path.insert(0, edge_dir)

    spec = importlib.util.spec_from_file_location(
        "edge_config", os.path.join(edge_dir, "config.py")
    )
    config = importlib.util.module_from_spec(spec)
    sys.modules["config"] = config
    spec.loader.exec_module(config)

    spec2 = importlib.util.spec_from_file_location(
        "anomaly_detector", os.path.join(edge_dir, "anomaly_detector.py")
    )
    ad_mod = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(ad_mod)
    return ad_mod.IsolationForestAnomalyDetector


def generate_device_data(device_id, device_type, count=10):
    base_values = {
        "air_compressor": {"vibration": 3.5, "temperature": 65, "current": 20, "speed": 2900, "acoustic": 75},
        "centrifugal_pump": {"vibration": 2.0, "temperature": 50, "current": 14, "speed": 1475, "acoustic": 65},
        "fan": {"vibration": 2.5, "temperature": 55, "current": 11, "speed": 980, "acoustic": 70},
        "conveyor": {"vibration": 1.5, "temperature": 45, "current": 8, "speed": 70, "acoustic": 60},
        "cooling_tower": {"vibration": 1.8, "temperature": 35, "current": 16, "speed": 735, "acoustic": 62},
    }
    base = base_values.get(device_type, base_values["air_compressor"])
    records = []
    for i in range(count):
        rec = {
            "device_id": device_id,
            "device_type": device_type,
            "timestamp": datetime.now().isoformat(),
        }
        for k, v in base.items():
            rec[k] = round(v + random.uniform(-v * 0.1, v * 0.1), 4)
        records.append(rec)
    return records


def test_root_cause_api(result):
    t0 = time.time()
    all_ok = True
    test_cases = [
        ("AC-001", "air_compressor"),
        ("CP-001", "centrifugal_pump"),
        ("FN-001", "fan"),
        ("CV-001", "conveyor"),
        ("CT-001", "cooling_tower"),
    ]

    for device_id, device_type in test_cases:
        try:
            data = generate_device_data(device_id, device_type, 5)
            resp = requests.post(
                "http://localhost:5001/api/root-cause/analyze",
                json={"device_id": device_id, "device_type": device_type, "anomaly_data": data},
                timeout=10,
            )
            ok = resp.status_code == 200
            if ok:
                body = resp.json()
                has_causes = "root_causes" in body or "primary_cause" in body
                ok = has_causes
                detail = "" if ok else "Missing root_causes field"
            else:
                detail = "HTTP {}: {}".format(resp.status_code, resp.text[:100])
            result.record("根因分析: {}".format(device_id), ok, detail, time.time() - t0)
            if not ok:
                all_ok = False
        except Exception as e:
            result.record("根因分析: {}".format(device_id), False, str(e)[:100], time.time() - t0)
            all_ok = False
    return all_ok


def test_lstm_api(result):
    t0 = time.time()
    all_ok = True
    test_cases = [
        ("AC-001", "air_compressor"),
        ("CP-001", "centrifugal_pump"),
    ]
    for device_id, device_type in test_cases:
        try:
            data = generate_device_data(device_id, device_type, 10)
            resp = requests.post(
                "http://localhost:5000/api/predict",
                json={"device_id": device_id, "device_type": device_type, "recent_data": data},
                timeout=10,
            )
            ok = resp.status_code == 200
            if ok:
                body = resp.json()
                has_rul = "rul_steps" in body or "rul_hours" in body or "prediction" in body
                ok = has_rul
                detail = "" if ok else "Missing RUL field"
            else:
                detail = "HTTP {}".format(resp.status_code)
            result.record("RUL预测: {}".format(device_id), ok, detail, time.time() - t0)
            if not ok:
                all_ok = False
        except Exception as e:
            result.record("RUL预测: {}".format(device_id), False, str(e)[:100], time.time() - t0)
            all_ok = False
    return all_ok


def test_edge_anomaly_detection(result):
    t0 = time.time()
    try:
        DetectorClass = load_edge_detector()
        detector = DetectorClass(
            device_type="air_compressor",
            normal_ranges={
                "vibration": (2.0, 5.0),
                "temperature": (55.0, 75.0),
                "current": (15.0, 25.0),
                "speed": (2800.0, 3000.0),
                "acoustic": (65.0, 85.0),
            },
            device_id="TEST-AC-001",
            n_estimators=50,
            n_samples=200,
        )
        normal = {"vibration": 3.5, "temperature": 65, "current": 20, "speed": 2900, "acoustic": 75}
        is_norm, score_norm = detector.detect(normal)
        anomaly = {"vibration": 8.0, "temperature": 90, "current": 35, "speed": 3500, "acoustic": 100}
        is_anom, score_anom = detector.detect(anomaly)

        ok = score_anom < score_norm
        detail = "normal={:.3f}, anomaly={:.3f}".format(score_norm, score_anom)
        result.record("边缘异常检测: 正常值vs异常值得分", ok, detail, time.time() - t0)
        return ok
    except Exception as e:
        result.record("边缘异常检测", False, str(e)[:200], time.time() - t0)
        return False


def test_full_data_flow(result):
    t0 = time.time()
    try:
        DetectorClass = load_edge_detector()
        detector = DetectorClass(
            device_type="air_compressor",
            normal_ranges={
                "vibration": (2.0, 5.0),
                "temperature": (55.0, 75.0),
                "current": (15.0, 25.0),
                "speed": (2800.0, 3000.0),
                "acoustic": (65.0, 85.0),
            },
            device_id="AC-001",
        )

        data = generate_device_data("AC-001", "air_compressor", 20)
        anomalies = []
        for rec in data:
            is_anom, score = detector.detect(rec)
            rec["is_anomaly"] = is_anom
            rec["anomaly_score"] = score
            if is_anom:
                anomalies.append(rec)

        result.record("边缘检测: 20条数据处理", True,
                      "检测到{}条异常".format(len(anomalies)), time.time() - t0)

        if anomalies:
            rc_resp = requests.post(
                "http://localhost:5001/analyze",
                json={"device_type": "air_compressor", "anomaly_data": anomalies[:5]},
                timeout=10,
            )
            ok_rc = rc_resp.status_code == 200
            result.record("完整链路: 异常->根因分析", ok_rc,
                          "HTTP {}".format(rc_resp.status_code), time.time() - t0)

            lstm_resp = requests.post(
                "http://localhost:5000/api/predict",
                json={"device_id": "AC-001", "device_type": "air_compressor", "recent_data": data},
                timeout=10,
            )
            ok_lstm = lstm_resp.status_code == 200
            result.record("完整链路: 数据->RUL预测", ok_lstm,
                          "HTTP {}".format(lstm_resp.status_code), time.time() - t0)

            return ok_rc and ok_lstm
        return True
    except Exception as e:
        result.record("完整数据流", False, str(e)[:200], time.time() - t0)
        return False


def test_model_persistence(result):
    t0 = time.time()
    try:
        import tempfile
        import shutil
        import joblib

        tmpdir = tempfile.mkdtemp(prefix="phm_test_model_")

        import importlib.util
        import sys

        edge_dir = os.path.join(PROJECT_ROOT, "edge-node")
        if edge_dir not in sys.path:
            sys.path.insert(0, edge_dir)

        spec = importlib.util.spec_from_file_location(
            "config2", os.path.join(edge_dir, "config.py")
        )
        config2 = importlib.util.module_from_spec(spec)
        sys.modules["config"] = config2
        spec.loader.exec_module(config2)

        spec2 = importlib.util.spec_from_file_location(
            "anomaly_detector2", os.path.join(edge_dir, "anomaly_detector.py")
        )
        ad_mod2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(ad_mod2)

        DetectorClass = ad_mod2.IsolationForestAnomalyDetector

        ad_mod2.MODEL_SAVE_DIR = tmpdir

        d1 = DetectorClass(
            device_type="fan",
            normal_ranges={"vibration": (1, 4), "temperature": (40, 60)},
            device_id="FAN-TEST-01",
            n_estimators=30,
            n_samples=100,
        )

        model_path = os.path.join(tmpdir, "FAN-TEST-01_iforest.joblib")
        ok_save = os.path.exists(model_path)
        result.record("模型持久化: 训练后自动保存", ok_save,
                      "path: {}".format(model_path), time.time() - t0)

        d2 = DetectorClass(
            device_type="fan",
            normal_ranges={"vibration": (1, 4), "temperature": (40, 60)},
            device_id="FAN-TEST-01",
            n_estimators=30,
            n_samples=100,
        )
        test_data = {"vibration": 2.5, "temperature": 50}
        _, s1 = d1.detect(test_data)
        _, s2 = d2.detect(test_data)
        ok_load = abs(s1 - s2) < 0.001
        result.record("模型持久化: 加载后一致", ok_load,
                      "score1={:.4f}, score2={:.4f}".format(s1, s2), time.time() - t0)

        shutil.rmtree(tmpdir, ignore_errors=True)
        return ok_save and ok_load
    except Exception as e:
        result.record("模型持久化", False, str(e)[:200], time.time() - t0)
        return False


def cleanup_services():
    print("\n  Stopping services...")
    for proc in PROCESSES:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:
            pass
    print("  All services stopped.")


def main():
    parser = argparse.ArgumentParser(description="PHM System Local E2E Test (no Docker)")
    parser.add_argument("--skip-start", action="store_true",
                        help="Skip starting services (assume they're already running)")
    parser.add_argument("--skip-cleanup", action="store_true",
                        help="Don't stop services after test")
    args = parser.parse_args()

    print()
    print("=" * 72)
    print("  PHM System Local E2E Integration Test")
    print("  (Running services locally, no Docker / no InfluxDB)")
    print("=" * 72)
    print("  Time  : " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  Root  : " + PROJECT_ROOT)
    print("  Report: " + REPORT_PATH)
    print("=" * 72)
    print()

    result = TestResult()

    print(">> Step 1: Start Mock LSTM Service")
    t0 = time.time()
    lstm_ok = start_mock_lstm_service()
    result.record("启动LSTM服务(Mock)", lstm_ok, "", time.time() - t0)

    if not lstm_ok:
        print("\n  [FATAL] Could not start LSTM service, aborting.")
        sys.exit(1)

    print("\n>> Step 2: Start Root Cause Service")
    t0 = time.time()
    rc_dir = os.path.join(PROJECT_ROOT, "root-cause-service")
    rc_cmd = [sys.executable, "main.py"]
    rc_ok = start_service(
        "root-cause", rc_cmd, rc_dir, 5001,
        "http://localhost:5001/health", timeout=30,
    )
    result.record("启动根因分析服务", rc_ok, "", time.time() - t0)

    if not rc_ok:
        print("\n  [WARN] Root cause service failed, but continuing with other tests")

    steps = []

    if rc_ok:
        steps.append(("3. 根因分析 API 验证", lambda: test_root_cause_api(result)))

    steps.extend([
        ("4. LSTM 预测 API 验证", lambda: test_lstm_api(result)),
        ("5. 边缘异常检测验证", lambda: test_edge_anomaly_detection(result)),
        ("6. 模型持久化验证", lambda: test_model_persistence(result)),
    ])

    if rc_ok:
        steps.append(("7. 完整数据链路验证", lambda: test_full_data_flow(result)))

    for label, fn in steps:
        print("\n>> {}".format(label))
        try:
            fn()
        except Exception as e:
            result.record(label, False, "Exception: {}".format(str(e)[:150]), 0)

    report = result.generate_report()
    print("\n" + report)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print("\n  Report saved to: " + REPORT_PATH)

    if not args.skip_cleanup:
        cleanup_services()
    else:
        print("\n  Services left running (--skip-cleanup)")

    exit_code = 0 if result.failed_count() == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
