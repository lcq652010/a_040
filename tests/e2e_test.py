#!/usr/bin/env python3
"""PHM System End-to-End Integration Test"""

import argparse
import json
import os
import random
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("❌ 缺少 requests 库，请执行: pip install requests")
    sys.exit(1)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(os.path.dirname(__file__), "e2e_report.txt")

SERVICES = {
    "influxdb": {
        "url": "http://localhost:8086/health",
        "container": "phm-influxdb",
        "timeout": 120,
    },
    "lstm-service": {
        "url": "http://localhost:5000/api/health",
        "container": "phm-lstm-service",
        "timeout": 300,
    },
    "root-cause-service": {
        "url": "http://localhost:5001/health",
        "container": "phm-root-cause-service",
        "timeout": 120,
    },
    "cloud-backend": {
        "url": "http://localhost:8080/health",
        "container": "phm-cloud-backend",
        "timeout": 180,
    },
    "frontend": {
        "url": "http://localhost:80/",
        "container": "phm-frontend",
        "timeout": 120,
    },
}

DEVICES = [
    {"id": "AC-001", "type": "air_compressor", "ranges": {
        "vibration": (2.0, 5.0), "temperature": (55.0, 75.0),
        "current": (15.0, 25.0), "speed": (2800.0, 3000.0), "acoustic_emission": (65.0, 85.0),
    }},
    {"id": "CP-001", "type": "centrifugal_pump", "ranges": {
        "vibration": (1.0, 3.5), "temperature": (40.0, 60.0),
        "current": (10.0, 18.0), "speed": (1450.0, 1500.0), "acoustic_emission": (55.0, 75.0),
    }},
    {"id": "FN-001", "type": "fan", "ranges": {
        "vibration": (1.5, 4.0), "temperature": (45.0, 65.0),
        "current": (8.0, 15.0), "speed": (960.0, 1000.0), "acoustic_emission": (60.0, 80.0),
    }},
    {"id": "CV-001", "type": "conveyor", "ranges": {
        "vibration": (0.5, 2.5), "temperature": (35.0, 55.0),
        "current": (5.0, 12.0), "speed": (60.0, 80.0), "acoustic_emission": (50.0, 70.0),
    }},
    {"id": "CT-001", "type": "cooling_tower", "ranges": {
        "vibration": (0.8, 2.8), "temperature": (28.0, 42.0),
        "current": (12.0, 20.0), "speed": (720.0, 750.0), "acoustic_emission": (52.0, 72.0),
    }},
]

DATA_PER_DEVICE = 20
POLL_INTERVAL = 5
MAX_WAIT_ALL = 600


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
        icon = "✅" if passed else "❌"
        line = f"  {icon} {name}"
        if duration > 0:
            line += f" ({duration:.1f}s)"
        if not passed:
            line += f"\n     原因: {detail}"
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
        lines.append("=" * 70)
        lines.append("  PHM System E2E Integration Test Report")
        lines.append("=" * 70)
        lines.append(f"  Start : {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  End   : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Total : {duration:.1f}s")
        lines.append("")
        lines.append("-" * 70)
        lines.append(f"  {'Result':<6} {'Test Name':<45} {'Time':>8}")
        lines.append("-" * 70)
        for r in self.results:
            icon = "PASS" if r["passed"] else "FAIL"
            lines.append(f"  [{icon}] {r['name']:<45} {r['duration']:>7.1f}s")
            if not r["passed"] and r["detail"]:
                lines.append(f"        -> {r['detail']}")
        lines.append("-" * 70)
        total = self.total_count()
        passed = self.passed_count()
        failed = self.failed_count()
        lines.append(f"  Total: {total}  Passed: {passed}  Failed: {failed}")
        overall = "ALL PASSED" if failed == 0 else "HAS FAILURES"
        lines.append(f"  Result: {overall}")
        lines.append("=" * 70)
        return "\n".join(lines)


def run_cmd(cmd, cwd=None, timeout=120):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd or PROJECT_ROOT,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def wait_for_url(url, timeout_sec=60, method="GET", expected_status=200, json_data=None):
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            if method == "GET":
                resp = requests.get(url, timeout=5)
            else:
                resp = requests.post(url, json=json_data, timeout=5)
            if resp.status_code == expected_status:
                return True, resp
        except requests.RequestException:
            pass
        time.sleep(POLL_INTERVAL)
    return False, None


def test_docker_available(result: TestResult):
    t0 = time.time()
    code, out, err = run_cmd("docker --version")
    ok = code == 0 and "Docker" in out
    detail = "" if ok else f"Docker不可用: {err or '未检测到Docker'}"
    if ok:
        code2, out2, _ = run_cmd("docker compose version")
        ok2 = code2 == 0
        if not ok2:
            detail = "docker compose 不可用"
            ok = False
    result.record("Docker环境可用", ok, detail, time.time() - t0)
    return ok


def test_docker_compose_up(result: TestResult, skip_start: bool):
    if skip_start:
        result.record("Docker服务启动(已跳过)", True, "通过--skip-start跳过", 0)
        return True
    t0 = time.time()
    code, out, err = run_cmd(
        "docker compose up -d --build", timeout=600,
    )
    ok = code == 0
    detail = "" if ok else f"docker compose up 失败: {err[:200]}"
    result.record("Docker服务启动", ok, detail, time.time() - t0)
    return ok


def test_services_ready(result: TestResult):
    all_ok = True
    for name, svc in SERVICES.items():
        t0 = time.time()
        ok, resp = wait_for_url(svc["url"], timeout_sec=svc["timeout"])
        detail = "" if ok else f"服务 {name} 在 {svc['timeout']}s 内未就绪 ({svc['url']})"
        result.record(f"服务就绪: {name}", ok, detail, time.time() - t0)
        if not ok:
            all_ok = False
    return all_ok


def generate_device_data(device, count):
    records = []
    for i in range(count):
        data = {
            "device_id": device["id"],
            "device_type": device["type"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        for param, (low, high) in device["ranges"].items():
            data[param] = round(random.uniform(low, high), 4)
        data["is_anomaly"] = random.random() < 0.1
        data["anomaly_score"] = round(random.uniform(0.7, 1.0), 4) if data["is_anomaly"] else round(random.uniform(0.0, 0.3), 4)
        records.append(data)
    return records


def test_data_upload(result: TestResult):
    all_ok = True
    url = "http://localhost:8080/api/data"
    for device in DEVICES:
        t0 = time.time()
        records = generate_device_data(device, DATA_PER_DEVICE)
        success = 0
        fail = 0
        last_err = ""
        for rec in records:
            try:
                resp = requests.post(url, json=rec, timeout=10)
                if resp.status_code == 200:
                    success += 1
                else:
                    fail += 1
                    last_err = f"HTTP {resp.status_code}: {resp.text[:100]}"
            except requests.RequestException as e:
                fail += 1
                last_err = str(e)[:100]
        ok = success == DATA_PER_DEVICE
        detail = "" if ok else f"{device['id']}: 成功{success}/{DATA_PER_DEVICE}, 原因: {last_err}"
        result.record(f"数据上报: {device['id']}", ok, detail, time.time() - t0)
        if not ok:
            all_ok = False
    return all_ok


def test_influxdb_query(result: TestResult):
    all_ok = True
    for device in DEVICES:
        t0 = time.time()
        url = f"http://localhost:8080/api/devices/{device['id']}/data?limit=5"
        try:
            resp = requests.get(url, timeout=15)
            ok = resp.status_code == 200
            if ok:
                body = resp.json()
                count = body.get("count", 0)
                ok = count > 0
                detail = "" if ok else f"{device['id']}: InfluxDB返回0条数据"
            else:
                detail = f"{device['id']}: HTTP {resp.status_code}"
        except requests.RequestException as e:
            ok = False
            detail = f"{device['id']}: {str(e)[:100]}"
        result.record(f"InfluxDB写入验证: {device['id']}", ok, detail, time.time() - t0)
        if not ok:
            all_ok = False
    return all_ok


def test_rul_prediction(result: TestResult):
    all_ok = True
    for device in DEVICES:
        t0 = time.time()
        url = f"http://localhost:8080/api/devices/{device['id']}/rul?device_type={device['type']}"
        try:
            resp = requests.get(url, timeout=30)
            ok = resp.status_code == 200
            if ok:
                body = resp.json()
                has_prediction = "rul_steps" in body or "prediction" in body
                ok = has_prediction
                detail = "" if ok else f"{device['id']}: 返回中缺少RUL预测字段"
            else:
                detail = f"{device['id']}: HTTP {resp.status_code}, {resp.text[:150]}"
        except requests.RequestException as e:
            ok = False
            detail = f"{device['id']}: {str(e)[:100]}"
        result.record(f"RUL预测: {device['id']}", ok, detail, time.time() - t0)
        if not ok:
            all_ok = False
    return all_ok


def test_root_cause_analysis(result: TestResult):
    all_ok = True
    for device in DEVICES:
        t0 = time.time()
        url = f"http://localhost:8080/api/devices/{device['id']}/root-cause"
        payload = {
            "device_type": device["type"],
            "anomaly_data": generate_device_data(device, 3),
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            ok = resp.status_code == 200
            if ok:
                body = resp.json()
                has_cause = "primary_cause" in body or "root_causes" in body
                ok = has_cause
                detail = "" if ok else f"{device['id']}: 返回中缺少根因分析字段"
            else:
                detail = f"{device['id']}: HTTP {resp.status_code}, {resp.text[:150]}"
        except requests.RequestException as e:
            ok = False
            detail = f"{device['id']}: {str(e)[:100]}"
        result.record(f"根因分析: {device['id']}", ok, detail, time.time() - t0)
        if not ok:
            all_ok = False
    return all_ok


def test_websocket(result: TestResult):
    t0 = time.time()
    ws_ok = False
    detail = ""
    try:
        import websocket as ws_lib
        ws_url = "ws://localhost:8080/api/ws"
        connected = False

        def on_open(ws):
            nonlocal connected
            connected = True
            ws.close()

        def on_error(ws, error):
            pass

        ws_app = ws_lib.WebSocketApp(
            ws_url, on_open=on_open, on_error=on_error,
        )
        ws_app.run_forever(ping_timeout=5, ping_interval=2)
        ws_ok = connected
        if not ws_ok:
            detail = "WebSocket连接未能成功建立"
    except ImportError:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("localhost", 8080))
            upgrade_req = (
                "GET /api/ws HTTP/1.1\r\n"
                "Host: localhost:8080\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "\r\n"
            )
            sock.sendall(upgrade_req.encode())
            resp = sock.recv(4096).decode(errors="ignore")
            sock.close()
            ws_ok = "101" in resp and "Upgrade" in resp
            if not ws_ok:
                detail = f"WebSocket握手未返回101, 响应: {resp[:100]}"
        except Exception as e:
            detail = f"WebSocket连接失败: {str(e)[:100]}"
    except Exception as e:
        detail = f"WebSocket测试异常: {str(e)[:100]}"

    result.record("WebSocket连接", ws_ok, detail, time.time() - t0)
    return ws_ok


def test_frontend_accessible(result: TestResult):
    t0 = time.time()
    ok = False
    detail = ""
    try:
        resp = requests.get("http://localhost:80/", timeout=10)
        ok = resp.status_code == 200
        if not ok:
            detail = f"HTTP {resp.status_code}"
    except requests.RequestException as e:
        detail = str(e)[:100]
    result.record("前端页面可访问", ok, detail, time.time() - t0)
    return ok


def cleanup_services(skip_cleanup: bool):
    if skip_cleanup:
        print("\n  ℹ️  跳过服务清理(--skip-cleanup)")
        return
    print("\n  🧹 停止Docker服务...")
    run_cmd("docker compose down", timeout=120)
    print("  ✅ Docker服务已停止")


def main():
    parser = argparse.ArgumentParser(description="PHM System E2E Integration Test")
    parser.add_argument("--skip-start", action="store_true", help="跳过docker compose启动")
    parser.add_argument("--skip-cleanup", action="store_true", help="测试后不停止Docker服务")
    args = parser.parse_args()

    print()
    print("=" * 70)
    print("  PHM System E2E Integration Test")
    print("=" * 70)
    print(f"  Time  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Root  : {PROJECT_ROOT}")
    print(f"  Report: {REPORT_PATH}")
    print(f"  Flags : --skip-start={args.skip_start} --skip-cleanup={args.skip_cleanup}")
    print("=" * 70)
    print()

    result = TestResult()

    steps = [
        ("1. 检查Docker环境", lambda: test_docker_available(result)),
        ("2. 启动Docker服务", lambda: test_docker_compose_up(result, args.skip_start)),
        ("3. 等待服务就绪", lambda: test_services_ready(result)),
        ("4. 模拟设备数据上报", lambda: test_data_upload(result)),
        ("5. 验证InfluxDB写入", lambda: test_influxdb_query(result)),
        ("6. RUL预测验证", lambda: test_rul_prediction(result)),
        ("7. 根因分析验证", lambda: test_root_cause_analysis(result)),
        ("8. WebSocket连接验证", lambda: test_websocket(result)),
        ("9. 前端页面访问验证", lambda: test_frontend_accessible(result)),
    ]

    failed_early = False
    for label, fn in steps:
        print(f"\n▶ {label}")
        try:
            ok = fn()
            if not ok and label in ("1. 检查Docker环境", "2. 启动Docker服务", "3. 等待服务就绪"):
                print(f"\n  ⚠️  前置步骤失败，终止后续测试")
                failed_early = True
                break
        except Exception as e:
            result.record(label, False, f"未捕获异常: {str(e)[:200]}", 0)
            if label in ("1. 检查Docker环境", "2. 启动Docker服务", "3. 等待服务就绪"):
                failed_early = True
                break

    report = result.generate_report()
    print("\n" + report)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n  📄 测试报告已写入: {REPORT_PATH}")

    cleanup_services(args.skip_cleanup)

    exit_code = 1 if (result.failed_count() > 0 or failed_early) else 0
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
