import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    HISTORY_DATA_PATH,
    TOTAL_STEPS_ONE_WEEK,
    SAMPLING_INTERVAL_SECONDS,
    DEVICE_TYPES,
    DEVICE_IDS,
    FEATURE_COLUMNS,
    NORMAL_RANGES,
    BATHTUB_CONFIG,
)

EARLY_FAILURE_RATIO = BATHTUB_CONFIG["early_failure_ratio"]
WEAR_OUT_RATIO = BATHTUB_CONFIG["wear_out_ratio"]
STABLE_RATIO = 1.0 - EARLY_FAILURE_RATIO - WEAR_OUT_RATIO


def _compute_phase_params(i, N):
    phase_ratio = i / N

    if phase_ratio < EARLY_FAILURE_RATIO:
        noise_factor = 2.0 + np.random.random() * 0.5
        anomaly_prob = 0.08
        degradation_factor = 1.0 + 0.01 * (i / (N * EARLY_FAILURE_RATIO))
    elif phase_ratio < EARLY_FAILURE_RATIO + STABLE_RATIO:
        noise_factor = 1.0
        anomaly_prob = 0.02
        normalized_progress = (phase_ratio - EARLY_FAILURE_RATIO) / STABLE_RATIO
        degradation_factor = 1.0 + normalized_progress * 0.3
    else:
        wear_progress = (phase_ratio - EARLY_FAILURE_RATIO - STABLE_RATIO) / WEAR_OUT_RATIO
        noise_factor = 1.0 + wear_progress * 2.0
        anomaly_prob = 0.05 + wear_progress * 0.15
        degradation_factor = 1.3 + wear_progress ** 2 * 3.0

    return noise_factor, anomaly_prob, degradation_factor, phase_ratio


def _apply_degradation(feature, base_value, degradation_factor):
    if feature == "vibration":
        return base_value * degradation_factor
    elif feature == "temperature":
        return base_value * degradation_factor * 0.8
    elif feature == "current":
        return base_value * (1 + (degradation_factor - 1) * 0.5)
    elif feature == "speed":
        return base_value / degradation_factor
    elif feature == "acoustic":
        return base_value * degradation_factor
    return base_value


def _compute_rul(i, N, phase_ratio):
    if phase_ratio >= EARLY_FAILURE_RATIO + STABLE_RATIO:
        wear_progress = (phase_ratio - EARLY_FAILURE_RATIO - STABLE_RATIO) / WEAR_OUT_RATIO
        remaining = N - i
        accelerated = remaining * (1.0 - wear_progress * 0.5)
        return max(0, accelerated)
    return max(0, N - i)


def generate_device_data(device_id: str, device_type: str, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)

    if device_type not in NORMAL_RANGES:
        raise ValueError(f"Unknown device type: {device_type}")

    ranges = NORMAL_RANGES[device_type]
    total_steps = TOTAL_STEPS_ONE_WEEK

    start_time = datetime.now() - timedelta(days=7)
    timestamps = [start_time + timedelta(seconds=i * SAMPLING_INTERVAL_SECONDS) for i in range(total_steps)]

    data = {
        "timestamp": timestamps,
        "vibration": np.zeros(total_steps),
        "temperature": np.zeros(total_steps),
        "current": np.zeros(total_steps),
        "speed": np.zeros(total_steps),
        "acoustic": np.zeros(total_steps),
        "rul": np.zeros(total_steps),
    }

    base_values = {}
    base_stds = {}
    for feature in FEATURE_COLUMNS:
        low, high = ranges[feature]
        base_values[feature] = (low + high) / 2
        base_stds[feature] = (high - low) / 6

    for i in range(total_steps):
        noise_factor, anomaly_prob, degradation_factor, phase_ratio = _compute_phase_params(i, total_steps)

        for feature in FEATURE_COLUMNS:
            noise = np.random.normal(0, base_stds[feature] * 0.3 * noise_factor)
            degraded_value = _apply_degradation(feature, base_values[feature], degradation_factor)
            data[feature][i] = degraded_value + noise

            if feature == "temperature":
                hour = timestamps[i].hour
                daily_cycle = np.sin(2 * np.pi * (hour - 6) / 24) * (ranges["temperature"][1] - ranges["temperature"][0]) * 0.05
                data["temperature"][i] += daily_cycle

        if np.random.random() < anomaly_prob:
            feature_to_amp = np.random.choice(FEATURE_COLUMNS)
            low, high = ranges[feature_to_amp]
            anomaly_mag = (high - low) * np.random.uniform(0.3, 1.0)
            direction = np.random.choice([-1, 1])
            data[feature_to_amp][i] += direction * anomaly_mag

        data["rul"][i] = _compute_rul(i, total_steps, phase_ratio)

    for i in range(total_steps):
        second_of_day = timestamps[i].hour * 3600 + timestamps[i].minute * 60 + timestamps[i].second
        if 0 <= second_of_day <= 7 * 3600:
            speed_factor = 0.7
        elif 7 * 3600 < second_of_day <= 18 * 3600:
            speed_factor = 1.0
        else:
            speed_factor = 0.85
        data["speed"][i] *= speed_factor
        if second_of_day <= 7 * 3600 or second_of_day > 20 * 3600:
            data["current"][i] *= 0.85

    for feature in FEATURE_COLUMNS:
        low, high = ranges[feature]
        max_val = high * 3.0
        min_val = low * 0.5
        data[feature] = np.clip(data[feature], min_val, max_val)

    df = pd.DataFrame(data)
    return df


def generate_one_week_data():
    os.makedirs(HISTORY_DATA_PATH, exist_ok=True)

    print(f"开始生成设备历史数据，共 {len(DEVICE_IDS)} 台设备...")
    print(f"每台设备数据点数: {TOTAL_STEPS_ONE_WEEK}")
    print(f"采样间隔: {SAMPLING_INTERVAL_SECONDS}秒")
    print(f"浴盆曲线配置: 早期失效期={EARLY_FAILURE_RATIO*100}%, 稳定运行期={STABLE_RATIO*100}%, 耗损退化期={WEAR_OUT_RATIO*100}%")
    print()

    for idx, device_id in enumerate(DEVICE_IDS):
        device_type = DEVICE_TYPES[idx % len(DEVICE_TYPES)]
        seed = 1000 + idx
        print(f"[{idx + 1}/{len(DEVICE_IDS)}] 生成 {device_id} ({device_type})...", end=" ")

        df = generate_device_data(device_id, device_type, seed=seed)

        output_path = os.path.join(HISTORY_DATA_PATH, f"{device_id}_history.csv")
        df.to_csv(output_path, index=False)

        print(f"完成 -> {os.path.basename(output_path)} ({len(df)} 条记录)")

    print()
    print(f"所有设备数据生成完毕！数据保存在: {HISTORY_DATA_PATH}")


if __name__ == "__main__":
    generate_one_week_data()
