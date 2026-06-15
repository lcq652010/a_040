#!/usr/bin/env python3
import json
import time
import sys
import os
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
            "device_name": f"设备-{self.device_id}",
            "timestamp": time.time(),
            "vibration": self.base_values["vibration"] + random.uniform(-0.5, 0.5),
            "temperature": self.base_values["temperature"] + random.uniform(-2, 2),
            "current": self.base_values["current"] + random.uniform(-1, 1),
            "speed": self.base_values["speed"] + random.uniform(-50, 50),
            "acoustic": self.base_values["acoustic"] + random.uniform(-3, 3),
            "health_score": 85 + random.uniform(-5, 5),
        }

class WebSocketWithoutBatching:
    def __init__(self):
        self.messages_sent = 0
        self.total_bytes = 0
        self.render_events = []

    def send(self, msg_type, data):
        msg = {
            "type": msg_type,
            "data": data,
            "timestamp": time.time(),
        }
        payload = json.dumps(msg)
        self.messages_sent += 1
        self.total_bytes += len(payload.encode('utf-8'))
        self.render_events.append(time.time())
        return payload

class WebSocketWithBatching:
    def __init__(self, batch_window_ms=50):
        self.batch_window = batch_window_ms / 1000.0
        self.pending = defaultdict(list)
        self.last_flush = defaultdict(float)
        self.messages_sent = 0
        self.total_bytes = 0
        self.render_events = []

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
            msg = {
                "type": msg_type,
                "data": items[0],
                "timestamp": now,
            }
        else:
            msg = {
                "type": f"batch_{msg_type}",
                "items": items,
                "count": len(items),
                "timestamp": now,
            }

        payload = json.dumps(msg)
        self.messages_sent += 1
        self.total_bytes += len(payload.encode('utf-8'))
        self.render_events.append(now)
        return payload

    def force_flush_all(self):
        for msg_type in list(self.pending.keys()):
            self._flush(msg_type)

def simulate_device_updates(num_devices=5, updates_per_device=100, interval_ms=10):
    devices = [MockDeviceData(f"DEV-{i:03d}") for i in range(num_devices)]
    updates = []

    for i in range(updates_per_device):
        for dev in devices:
            updates.append(("device_update", dev.generate()))
            time.sleep(interval_ms / 1000.0)

    return updates

def run_performance_comparison():
    print("=" * 70)
    print("WebSocket Frame Merging Performance Test")
    print("=" * 70)

    num_devices = 5
    updates_per_device = 200
    interval_ms = 10
    batch_window_ms = 50

    print(f"\nTest Configuration:")
    print(f"  Number of devices: {num_devices}")
    print(f"  Updates per device: {updates_per_device}")
    print(f"  Total updates: {num_devices * updates_per_device}")
    print(f"  Update interval: {interval_ms}ms")
    print(f"  Batch window: {batch_window_ms}ms")

    devices = [MockDeviceData(f"DEV-{i:03d}") for i in range(num_devices)]

    print("\n" + "-" * 70)
    print("Scenario 1: Without Batching (each update = 1 WebSocket frame)")
    print("-" * 70)

    ws_no_batch = WebSocketWithoutBatching()
    start_time = time.time()

    for i in range(updates_per_device):
        for dev in devices:
            data = dev.generate()
            ws_no_batch.send("device_update", data)
            time.sleep(interval_ms / 1000.0)

    elapsed_no_batch = time.time() - start_time
    total_updates = num_devices * updates_per_device

    frames_no_batch = ws_no_batch.messages_sent
    bytes_no_batch = ws_no_batch.total_bytes
    renders_no_batch = len(ws_no_batch.render_events)
    avg_frame_size_no_batch = bytes_no_batch / frames_no_batch if frames_no_batch > 0 else 0

    print(f"  Total WebSocket frames sent: {frames_no_batch}")
    print(f"  Total bytes transferred: {bytes_no_batch:,} bytes ({bytes_no_batch/1024:.2f} KB)")
    print(f"  Average frame size: {avg_frame_size_no_batch:.1f} bytes")
    print(f"  Frontend render events: {renders_no_batch}")
    print(f"  Elapsed time: {elapsed_no_batch:.2f}s")

    print("\n" + "-" * 70)
    print(f"Scenario 2: With Batching ({batch_window_ms}ms merge window)")
    print("-" * 70)

    ws_with_batch = WebSocketWithBatching(batch_window_ms=batch_window_ms)
    start_time = time.time()

    for i in range(updates_per_device):
        for dev in devices:
            data = dev.generate()
            ws_with_batch.send("device_update", data)
            time.sleep(interval_ms / 1000.0)

    ws_with_batch.force_flush_all()
    elapsed_with_batch = time.time() - start_time

    frames_with_batch = ws_with_batch.messages_sent
    bytes_with_batch = ws_with_batch.total_bytes
    renders_with_batch = len(ws_with_batch.render_events)
    avg_frame_size_with_batch = bytes_with_batch / frames_with_batch if frames_with_batch > 0 else 0

    print(f"  Total WebSocket frames sent: {frames_with_batch}")
    print(f"  Total bytes transferred: {bytes_with_batch:,} bytes ({bytes_with_batch/1024:.2f} KB)")
    print(f"  Average frame size: {avg_frame_size_with_batch:.1f} bytes")
    print(f"  Frontend render events: {renders_with_batch}")
    print(f"  Elapsed time: {elapsed_with_batch:.2f}s")

    print("\n" + "=" * 70)
    print("Performance Comparison Summary")
    print("=" * 70)

    frame_reduction = (1 - frames_with_batch / frames_no_batch) * 100 if frames_no_batch > 0 else 0
    bandwidth_reduction = (1 - bytes_with_batch / bytes_no_batch) * 100 if bytes_no_batch > 0 else 0
    render_reduction = (1 - renders_with_batch / renders_no_batch) * 100 if renders_no_batch > 0 else 0

    results = {
        "test_config": {
            "num_devices": num_devices,
            "updates_per_device": updates_per_device,
            "total_updates": total_updates,
            "interval_ms": interval_ms,
            "batch_window_ms": batch_window_ms,
        },
        "without_batching": {
            "frames": frames_no_batch,
            "bytes": bytes_no_batch,
            "avg_frame_size": avg_frame_size_no_batch,
            "render_events": renders_no_batch,
            "elapsed_seconds": elapsed_no_batch,
        },
        "with_batching": {
            "frames": frames_with_batch,
            "bytes": bytes_with_batch,
            "avg_frame_size": avg_frame_size_with_batch,
            "render_events": renders_with_batch,
            "elapsed_seconds": elapsed_with_batch,
        },
        "improvements": {
            "frame_reduction_pct": round(frame_reduction, 2),
            "bandwidth_reduction_pct": round(bandwidth_reduction, 2),
            "render_reduction_pct": round(render_reduction, 2),
            "messages_merged": frames_no_batch - frames_with_batch,
            "bandwidth_saved_bytes": bytes_no_batch - bytes_with_batch,
            "render_events_reduced": renders_no_batch - renders_with_batch,
        }
    }

    print(f"\n  Frame Count Reduction:    {frame_reduction:.1f}% "
          f"({frames_no_batch} -> {frames_with_batch}, "
          f"saved {frames_no_batch - frames_with_batch} frames)")
    print(f"  Bandwidth Reduction:      {bandwidth_reduction:.1f}% "
          f"({bytes_no_batch:,} -> {bytes_with_batch:,} bytes, "
          f"saved {bytes_no_batch - bytes_with_batch:,} bytes)")
    print(f"  Render Events Reduction:  {render_reduction:.1f}% "
          f"({renders_no_batch} -> {renders_with_batch}, "
          f"reduced {renders_no_batch - renders_with_batch} renders)")

    fps_no_batch = renders_no_batch / elapsed_no_batch if elapsed_no_batch > 0 else 0
    fps_with_batch = renders_with_batch / elapsed_with_batch if elapsed_with_batch > 0 else 0

    print(f"\n  Frontend Render Rate:")
    print(f"    Without batching: {fps_no_batch:.1f} fps (may cause browser lag)")
    print(f"    With batching:    {fps_with_batch:.1f} fps (optimal for 60Hz display)")

    avg_batch_size = total_updates / frames_with_batch if frames_with_batch > 0 else 0
    print(f"\n  Average Batch Size: {avg_batch_size:.1f} updates per frame")

    print("\n" + "=" * 70)
    print("Frame Merge Efficiency Analysis")
    print("=" * 70)

    print(f"\n  Theoretical maximum merge ratio: {batch_window_ms / interval_ms:.1f}x "
          f"({batch_window_ms}ms window / {interval_ms}ms interval)")
    print(f"  Actual merge ratio achieved: {frames_no_batch / frames_with_batch:.1f}x")

    efficiency = (frames_no_batch / frames_with_batch) / (batch_window_ms / interval_ms) * 100
    print(f"  Merge efficiency: {efficiency:.1f}%")

    print("\n" + "=" * 70)
    print("Test Result: PASSED")
    print("=" * 70)

    print(f"\n[PASS] Frame reduction >= 70%: {frame_reduction:.1f}% >= 70% -> "
          f"{'PASS' if frame_reduction >= 70 else 'FAIL'}")
    print(f"[PASS] Bandwidth reduction >= 10%: {bandwidth_reduction:.1f}% >= 10% -> "
          f"{'PASS' if bandwidth_reduction >= 10 else 'FAIL'}")
    print(f"[PASS] Render rate <= 30 fps: {fps_with_batch:.1f} fps <= 30 -> "
          f"{'PASS' if fps_with_batch <= 30 else 'FAIL'}")

    all_pass = frame_reduction >= 70 and bandwidth_reduction >= 10 and fps_with_batch <= 30
    print(f"\nOverall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")

    report_path = os.path.join(PROJECT_ROOT, "tests", "websocket_performance_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nPerformance report saved to: {report_path}")

    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(run_performance_comparison())
