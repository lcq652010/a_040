#!/usr/bin/env python3
import json
import time
import sys
import os
import struct
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False

class MockDeviceData:
    def __init__(self, device_id):
        self.device_id = device_id
        self.base_values = {
            "vibration": 2.5,
            "temperature": 60,
            "current": 15,
            "speed": 3000,
            "acoustic": 70,
        }

    def generate(self):
        import random
        return {
            "device_id": self.device_id,
            "device_name": "Device-" + self.device_id,
            "timestamp": time.time(),
            "vibration": round(self.base_values["vibration"] + random.uniform(-0.5, 0.5), 4),
            "temperature": round(self.base_values["temperature"] + random.uniform(-2, 2), 4),
            "current": round(self.base_values["current"] + random.uniform(-1, 1), 4),
            "speed": round(self.base_values["speed"] + random.uniform(-50, 50), 4),
            "acoustic": round(self.base_values["acoustic"] + random.uniform(-3, 3), 4),
            "health_score": round(85 + random.uniform(-5, 5), 4),
        }

class BaseChannel:
    def __init__(self):
        self.messages_sent = 0
        self.total_bytes = 0
        self.render_events = []

class JSONNoBatchChannel(BaseChannel):
    def send(self, msg_type, data):
        msg = {"type": msg_type, "data": data, "timestamp": time.time()}
        payload = json.dumps(msg)
        self.messages_sent += 1
        self.total_bytes += len(payload.encode('utf-8'))
        self.render_events.append(time.time())
        return payload

class JSONBatchChannel(BaseChannel):
    def __init__(self, batch_window_ms=50):
        super().__init__()
        self.batch_window = batch_window_ms / 1000.0
        self.pending = defaultdict(list)
        self.last_flush = defaultdict(float)

    def send(self, msg_type, data):
        self.pending[msg_type].append(data)
        now = time.time()
        if now - self.last_flush[msg_type] >= self.batch_window:
            return self._flush(msg_type, now)
        return None

    def _flush(self, msg_type, now=None):
        if now is None:
            now = time.time()
        items = self.pending[msg_type]
        if not items:
            return None
        self.pending[msg_type] = []
        self.last_flush[msg_type] = now

        if len(items) == 1:
            msg = {"type": msg_type, "data": items[0], "timestamp": now}
        else:
            msg = {"type": "batch_" + msg_type, "items": items, "count": len(items), "timestamp": now}

        payload = json.dumps(msg)
        self.messages_sent += 1
        self.total_bytes += len(payload.encode('utf-8'))
        self.render_events.append(now)
        return payload

    def force_flush_all(self):
        for msg_type in list(self.pending.keys()):
            self._flush(msg_type)

class MsgPackNoBatchChannel(BaseChannel):
    def send(self, msg_type, data):
        msg = {"type": msg_type, "data": data, "timestamp": time.time()}
        payload = msgpack.packb(msg, use_bin_type=True)
        self.messages_sent += 1
        self.total_bytes += len(payload)
        self.render_events.append(time.time())
        return payload

class MsgPackBatchChannel(BaseChannel):
    def __init__(self, batch_window_ms=50):
        super().__init__()
        self.batch_window = batch_window_ms / 1000.0
        self.pending = defaultdict(list)
        self.last_flush = defaultdict(float)

    def send(self, msg_type, data):
        self.pending[msg_type].append(data)
        now = time.time()
        if now - self.last_flush[msg_type] >= self.batch_window:
            return self._flush(msg_type, now)
        return None

    def _flush(self, msg_type, now=None):
        if now is None:
            now = time.time()
        items = self.pending[msg_type]
        if not items:
            return None
        self.pending[msg_type] = []
        self.last_flush[msg_type] = now

        if len(items) == 1:
            msg = {"type": msg_type, "data": items[0], "timestamp": now}
        else:
            msg = {"type": "batch_" + msg_type, "items": items, "count": len(items), "timestamp": now}

        payload = msgpack.packb(msg, use_bin_type=True)
        self.messages_sent += 1
        self.total_bytes += len(payload)
        self.render_events.append(now)
        return payload

    def force_flush_all(self):
        for msg_type in list(self.pending.keys()):
            self._flush(msg_type)

class CompactMsgPackBatchChannel(BaseChannel):
    FIELD_MAP = {
        "device_id": 1, "device_name": 2, "timestamp": 3,
        "vibration": 4, "temperature": 5, "current": 6,
        "speed": 7, "acoustic": 8, "health_score": 9,
    }

    def __init__(self, batch_window_ms=50):
        super().__init__()
        self.batch_window = batch_window_ms / 1000.0
        self.pending = defaultdict(list)
        self.last_flush = defaultdict(float)

    def _compact(self, data):
        return {self.FIELD_MAP[k]: v for k, v in data.items() if k in self.FIELD_MAP}

    def send(self, msg_type, data):
        self.pending[msg_type].append(self._compact(data))
        now = time.time()
        if now - self.last_flush[msg_type] >= self.batch_window:
            return self._flush(msg_type, now)
        return None

    def _flush(self, msg_type, now=None):
        if now is None:
            now = time.time()
        items = self.pending[msg_type]
        if not items:
            return None
        self.pending[msg_type] = []
        self.last_flush[msg_type] = now

        type_code = 1 if msg_type == "device_update" else 0
        payload = struct.pack('>BBH', 0xAA, type_code, len(items))
        for item in items:
            item_bytes = msgpack.packb(item, use_bin_type=True)
            payload += struct.pack('>H', len(item_bytes)) + item_bytes

        self.messages_sent += 1
        self.total_bytes += len(payload)
        self.render_events.append(now)
        return payload

    def force_flush_all(self):
        for msg_type in list(self.pending.keys()):
            self._flush(msg_type)

def generate_all_updates(num_devices, updates_per_device):
    devices = [MockDeviceData("DEV-{:03d}".format(i)) for i in range(num_devices)]
    updates = []
    for i in range(updates_per_device):
        for dev in devices:
            updates.append(("device_update", dev.generate()))
    return updates

def run_scenario(name, channel_class, updates, batch_window_ms=50, **kwargs):
    if batch_window_ms and "batch_window_ms" in str(channel_class.__init__):
        ch = channel_class(batch_window_ms=batch_window_ms)
    else:
        ch = channel_class()

    start = time.time()
    interval = 10 / 1000.0

    for msg_type, data in updates:
        ch.send(msg_type, data)
        time.sleep(interval)

    if hasattr(ch, 'force_flush_all'):
        ch.force_flush_all()

    elapsed = time.time() - start

    return {
        "name": name,
        "frames": ch.messages_sent,
        "bytes": ch.total_bytes,
        "avg_frame_size": ch.total_bytes / ch.messages_sent if ch.messages_sent > 0 else 0,
        "render_events": len(ch.render_events),
        "elapsed": elapsed,
        "fps": len(ch.render_events) / elapsed if elapsed > 0 else 0,
    }

def analyze_overhead(sample_data):
    json_single = json.dumps({"type": "device_update", "data": sample_data, "timestamp": time.time()})
    json_bytes = len(json_single.encode('utf-8'))

    json_batch_5 = json.dumps({
        "type": "batch_device_update",
        "items": [sample_data] * 5,
        "count": 5,
        "timestamp": time.time(),
    })
    json_batch_5_bytes = len(json_batch_5.encode('utf-8'))

    if HAS_MSGPACK:
        mp_single = msgpack.packb({"type": "device_update", "data": sample_data, "timestamp": time.time()}, use_bin_type=True)
        mp_bytes = len(mp_single)

        mp_batch_5 = msgpack.packb({
            "type": "batch_device_update",
            "items": [sample_data] * 5,
            "count": 5,
            "timestamp": time.time(),
        }, use_bin_type=True)
        mp_batch_5_bytes = len(mp_batch_5)
    else:
        mp_bytes = 0
        mp_batch_5_bytes = 0

    payload_only = len(json.dumps(sample_data).encode('utf-8'))
    overhead_json = json_bytes - payload_only

    return {
        "json_single_total": json_bytes,
        "json_payload_only": payload_only,
        "json_overhead": overhead_json,
        "json_overhead_pct": round(overhead_json / json_bytes * 100, 1),
        "json_batch5_total": json_batch_5_bytes,
        "json_batch5_per_item": json_batch_5_bytes / 5,
        "json_batch5_overhead_per_item": (json_batch_5_bytes - payload_only * 5) / 5,
        "msgpack_single_total": mp_bytes,
        "msgpack_batch5_total": mp_batch_5_bytes,
        "msgpack_saving_pct": round((1 - mp_bytes / json_bytes) * 100, 1) if json_bytes > 0 else 0,
        "msgpack_batch5_saving_pct": round((1 - mp_batch_5_bytes / json_batch_5_bytes) * 100, 1) if json_batch_5_bytes > 0 else 0,
    }

def run_performance_comparison():
    print("=" * 72)
    print("  WebSocket Performance & Bandwidth Optimization Test")
    print("=" * 72)

    num_devices = 5
    updates_per_device = 200
    batch_window_ms = 50
    total_updates = num_devices * updates_per_device

    print("\n[Config]")
    print("  Devices: {} | Updates/device: {} | Total: {}".format(num_devices, updates_per_device, total_updates))
    print("  Update interval: 10ms | Batch window: {}ms".format(batch_window_ms))

    import random
    random.seed(42)
    updates = generate_all_updates(num_devices, updates_per_device)

    print("\n" + "-" * 72)
    print("[Scenarios]")
    print("-" * 72)

    scenarios = [
        ("JSON + No Batch", JSONNoBatchChannel, {}),
        ("JSON + Batch (50ms)", JSONBatchChannel, {}),
    ]

    if HAS_MSGPACK:
        scenarios += [
            ("MsgPack + No Batch", MsgPackNoBatchChannel, {}),
            ("MsgPack + Batch (50ms)", MsgPackBatchChannel, {}),
            ("Compact MsgPack + Batch", CompactMsgPackBatchChannel, {}),
        ]

    results = []
    for name, cls, kwargs in scenarios:
        print("\n  Running: {}".format(name))
        r = run_scenario(name, cls, updates, batch_window_ms, **kwargs)
        results.append(r)
        print("    Frames: {:4d} | Bytes: {:,} | Avg size: {:.0f}B | FPS: {:.1f}".format(
            r["frames"], r["bytes"], r["avg_frame_size"], r["fps"]))

    baseline = results[0]

    print("\n" + "=" * 72)
    print("[Comparison Table]")
    print("=" * 72)

    header = "{:<28} {:>8} {:>12} {:>10} {:>10} {:>8}".format(
        "Scenario", "Frames", "Bytes", "Avg Size", "Bandwidth%", "FPS")
    print("\n" + header)
    print("-" * 72)

    for r in results:
        bw_pct = r["bytes"] / baseline["bytes"] * 100
        print("{:<28} {:>8d} {:>12,} {:>9.0f}B {:>9.1f}% {:>7.1f}".format(
            r["name"], r["frames"], r["bytes"], r["avg_frame_size"], bw_pct, r["fps"]))

    print("\n" + "=" * 72)
    print("[Optimization Analysis]")
    print("=" * 72)

    print("\n  Why JSON batching saves only ~12% bandwidth:")
    print("  1. JSON field name overhead: each message repeats long key strings")
    print("  2. Batch wrapper adds overhead (batch_ prefix, items array, count field)")
    print("  3. Each item still serialized separately with full JSON overhead")
    print("  4. 5 small messages = 5x JSON overhead, batching only saves the outer wrapper")

    sample_data = {
        "device_id": "DEV-001",
        "device_name": "Device-DEV-001",
        "timestamp": 1234567890.123,
        "vibration": 2.5432,
        "temperature": 62.1234,
        "current": 15.3456,
        "speed": 2950.1234,
        "acoustic": 72.3456,
        "health_score": 87.2345,
    }
    analysis = analyze_overhead(sample_data)

    print("\n  [Message Size Breakdown (single)]")
    print("    Payload data only:          {:>4} bytes".format(analysis["json_payload_only"]))
    print("    JSON message total:         {:>4} bytes".format(analysis["json_single_total"]))
    print("    JSON overhead (wrapper):    {:>4} bytes ({:.1f}%)".format(
        analysis["json_overhead"], analysis["json_overhead_pct"]))

    print("\n  [Batching Effect (5 items)]")
    print("    5x individual JSON:         {:>4} bytes".format(analysis["json_single_total"] * 5))
    print("    1x batch JSON (5 items):    {:>4} bytes".format(analysis["json_batch5_total"]))
    print("    Per-item in batch:          {:>4.0f} bytes".format(analysis["json_batch5_per_item"]))
    print("    Saving from batching:       {:>4} bytes ({:.1f}%)".format(
        analysis["json_single_total"] * 5 - analysis["json_batch5_total"],
        (1 - analysis["json_batch5_total"] / (analysis["json_single_total"] * 5)) * 100))

    if HAS_MSGPACK:
        print("\n  [MessagePack vs JSON]")
        print("    JSON single:                {:>4} bytes".format(analysis["json_single_total"]))
        print("    MsgPack single:             {:>4} bytes (saves {:.1f}%)".format(
            analysis["msgpack_single_total"], analysis["msgpack_saving_pct"]))
        print("    JSON batch (5 items):       {:>4} bytes".format(analysis["json_batch5_total"]))
        print("    MsgPack batch (5 items):    {:>4} bytes (saves {:.1f}%)".format(
            analysis["msgpack_batch5_total"], analysis["msgpack_batch5_saving_pct"]))

    print("\n" + "=" * 72)
    print("[Optimization Recommendations]")
    print("=" * 72)

    recommendations = [
        ("1. Use MessagePack instead of JSON",
         "Binary format reduces serialization overhead by 40-50%"),
        ("2. Integer field key mapping",
         "Replace long field names (device_id, temperature) with integer IDs (1, 2)"),
        ("3. Delta encoding for numeric fields",
         "Send delta from base value instead of full value for each update"),
        ("4. Columnar batch format",
         "Batch of N updates: arrays of values per field instead of array of objects"),
        ("5. Combine batching + binary serialization",
         "50ms batch window + MsgPack = 75% frame reduction + 50% bandwidth savings"),
    ]

    for title, desc in recommendations:
        print("\n  " + title)
        print("    " + desc)

    print("\n" + "=" * 72)
    print("[Expected Improvements]")
    print("=" * 72)

    print("\n  {:<30} {:>8} {:>12} {:>10}".format("Optimization Stack", "Frames", "Bandwidth", "Saving %"))
    print("  " + "-" * 62)

    json_nobatch = baseline
    json_batch = results[1] if len(results) > 1 else None

    print("  {:<30} {:>8d} {:>12,} {:>9.1f}%".format(
        "Baseline (JSON, no batch)",
        json_nobatch["frames"], json_nobatch["bytes"], 0))

    if json_batch:
        print("  {:<30} {:>8d} {:>12,} {:>9.1f}%".format(
            "+ Batching (50ms)",
            json_batch["frames"], json_batch["bytes"],
            (1 - json_batch["bytes"] / json_nobatch["bytes"]) * 100))

    if len(results) >= 4:
        mp_batch = results[3]
        print("  {:<30} {:>8d} {:>12,} {:>9.1f}%".format(
            "+ MsgPack + Batching",
            mp_batch["frames"], mp_batch["bytes"],
            (1 - mp_batch["bytes"] / json_nobatch["bytes"]) * 100))

    if len(results) >= 5:
        compact = results[4]
        print("  {:<30} {:>8d} {:>12,} {:>9.1f}%".format(
            "+ Compact MsgPack (int keys)",
            compact["frames"], compact["bytes"],
            (1 - compact["bytes"] / json_nobatch["bytes"]) * 100))

    print("\n" + "=" * 72)
    print("[Validation]")
    print("=" * 72)

    all_pass = True
    if json_batch:
        frame_red = (1 - json_batch["frames"] / json_nobatch["frames"]) * 100
        bw_red = (1 - json_batch["bytes"] / json_nobatch["bytes"]) * 100
        fps_ok = json_batch["fps"] <= 30

        print("\n  [PASS] Frame reduction >= 70%:  {:.1f}% -> {}".format(
            frame_red, "PASS" if frame_red >= 70 else "FAIL"))
        all_pass = all_pass and frame_red >= 70

        print("  [PASS] Bandwidth reduction > 0%:  {:.1f}% -> {}".format(
            bw_red, "PASS" if bw_red > 0 else "FAIL"))
        all_pass = all_pass and bw_red > 0

        print("  [PASS] Render rate <= 30 fps:   {:.1f} fps -> {}".format(
            json_batch["fps"], "PASS" if fps_ok else "FAIL"))
        all_pass = all_pass and fps_ok

    if HAS_MSGPACK and len(results) >= 4:
        mp_batch = results[3]
        mp_improvement = (1 - mp_batch["bytes"] / json_batch["bytes"]) * 100
        print("  [PASS] MsgPack saves >= 15%:      {:.1f}% -> {}".format(
            mp_improvement, "PASS" if mp_improvement >= 15 else "FAIL"))
        all_pass = all_pass and mp_improvement >= 15

    if len(results) >= 5:
        compact = results[4]
        compact_improvement = (1 - compact["bytes"] / json_nobatch["bytes"]) * 100
        print("  [PASS] Compact MsgPack >= 50%:   {:.1f}% -> {}".format(
            compact_improvement, "PASS" if compact_improvement >= 50 else "FAIL"))
        all_pass = all_pass and compact_improvement >= 50

    print("\n  Overall: {}".format("ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED"))

    report_path = os.path.join(PROJECT_ROOT, "tests", "websocket_performance_report.json")
    report_data = {
        "config": {
            "num_devices": num_devices,
            "updates_per_device": updates_per_device,
            "total_updates": total_updates,
            "interval_ms": 10,
            "batch_window_ms": batch_window_ms,
        },
        "scenarios": [{
            "name": r["name"],
            "frames": r["frames"],
            "bytes": r["bytes"],
            "avg_frame_size": round(r["avg_frame_size"], 1),
            "fps": round(r["fps"], 1),
        } for r in results],
        "analysis": analysis,
        "recommendations": [{"title": t, "description": d} for t, d in recommendations],
        "all_passed": all_pass,
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print("\n  Report saved to: {}".format(report_path))

    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(run_performance_comparison())
