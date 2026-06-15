import os
import sys
import glob
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    HISTORY_DATA_PATH,
    MODEL_SAVE_PATH,
    WINDOW_SIZE,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    DEVICE_IDS,
)
from .lstm_model import PHM_LSTM_Model


def load_history_data(history_dir: str = HISTORY_DATA_PATH) -> Dict[str, pd.DataFrame]:
    os.makedirs(history_dir, exist_ok=True)
    csv_files = glob.glob(os.path.join(history_dir, "*_history.csv"))

    if not csv_files:
        from data.generate_history import generate_one_week_data
        print("历史数据不存在，开始生成模拟历史数据...")
        generate_one_week_data()
        csv_files = glob.glob(os.path.join(history_dir, "*_history.csv"))

    device_data = {}
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        device_id = filename.replace("_history.csv", "")
        df = pd.read_csv(csv_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        device_data[device_id] = df
        print(f"加载数据: {device_id} ({len(df)} 条记录)")

    return device_data


def create_sequences(
    data: np.ndarray,
    targets: np.ndarray,
    window_size: int,
    step: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    n_samples = len(data)

    for i in range(0, n_samples - window_size, step):
        X.append(data[i : i + window_size])
        y.append(targets[i + window_size])

    return np.array(X), np.array(y)


def split_train_test(
    df: pd.DataFrame,
    test_size: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    split_idx = int(len(df) * (1 - test_size))
    train_df = df.iloc[:split_idx].reset_index(drop=True)
    test_df = df.iloc[split_idx:].reset_index(drop=True)
    return train_df, test_df


def compute_scaler_params(
    train_features: np.ndarray,
    train_targets: np.ndarray,
) -> Dict[str, np.ndarray]:
    return {
        "feature_means": train_features.mean(axis=(0, 1)).tolist(),
        "feature_stds": (train_features.std(axis=(0, 1)) + 1e-8).tolist(),
        "target_mean": float(train_targets.mean()),
        "target_std": float(train_targets.std() + 1e-8),
    }


def apply_scaling(
    features: np.ndarray,
    targets: np.ndarray,
    scaler_params: Dict,
) -> Tuple[np.ndarray, np.ndarray]:
    means = np.array(scaler_params["feature_means"])
    stds = np.array(scaler_params["feature_stds"])
    target_mean = scaler_params["target_mean"]
    target_std = scaler_params["target_std"]

    scaled_features = (features - means) / stds
    scaled_targets = (targets - target_mean) / target_std

    return scaled_features, scaled_targets


def train_single_device(
    device_id: str,
    df: pd.DataFrame,
    skip_if_exists: bool = True,
) -> Tuple[PHM_LSTM_Model, Dict]:
    model = PHM_LSTM_Model(device_id=device_id)

    if skip_if_exists and model.is_trained():
        print(f"[{device_id}] 模型已存在，跳过训练")
        return model, {"skipped": True}

    print(f"\n{'='*60}")
    print(f"[{device_id}] 开始训练模型")
    print(f"{'='*60}")

    features = df[FEATURE_COLUMNS].values.astype(np.float32)
    targets = df[TARGET_COLUMN].values.astype(np.float32)

    train_df, test_df = split_train_test(df, test_size=0.2)
    print(f"  训练集: {len(train_df)} 条 | 测试集: {len(test_df)} 条")

    train_features = train_df[FEATURE_COLUMNS].values.astype(np.float32)
    train_targets = train_df[TARGET_COLUMN].values.astype(np.float32)
    test_features = test_df[FEATURE_COLUMNS].values.astype(np.float32)
    test_targets = test_df[TARGET_COLUMN].values.astype(np.float32)

    scaler_params = compute_scaler_params(
        features.reshape(1, -1, len(FEATURE_COLUMNS)),
        targets,
    )

    X_train, y_train = create_sequences(train_features, train_targets, WINDOW_SIZE, step=5)
    X_test, y_test = create_sequences(test_features, test_targets, WINDOW_SIZE, step=1)

    X_train_scaled, y_train_scaled = apply_scaling(X_train, y_train, scaler_params)
    X_test_scaled, y_test_scaled = apply_scaling(X_test, y_test, scaler_params)

    print(f"  训练序列数: {len(X_train_scaled)} | 测试序列数: {len(X_test_scaled)}")
    print(f"  输入形状: {X_train_scaled.shape}")

    history = model.train(
        X_train=X_train_scaled,
        y_train=y_train_scaled,
        X_val=X_test_scaled,
        y_val=y_test_scaled,
        scaler_params=scaler_params,
    )

    if len(history.get("loss", [])) > 0:
        final_loss = history["loss"][-1]
        print(f"\n[{device_id}] 训练完成!")
        print(f"  最终训练 Loss: {final_loss:.6f}")
        if history.get("val_loss"):
            print(f"  最终验证 Loss: {history['val_loss'][-1]:.6f}")

    return model, history


def main():
    print("=" * 70)
    print("LSTM RUL 预测模型训练流程")
    print("=" * 70)
    print()

    device_data = load_history_data()

    if not device_data:
        print("错误: 无法加载任何设备数据")
        return

    print(f"\n共发现 {len(device_data)} 台设备数据，开始训练模型...")
    print(f"模型保存路径: {MODEL_SAVE_PATH}")

    results = {}
    for idx, (device_id, df) in enumerate(device_data.items(), 1):
        print(f"\n[{idx}/{len(device_data)}]", end=" ")
        model, history = train_single_device(device_id, df, skip_if_exists=False)
        results[device_id] = {"history": history, "model": model}

    print("\n" + "=" * 70)
    print("所有设备模型训练完成!")
    print(f"已保存模型: {len(results)} 个")
    print("=" * 70)


def ensure_all_models_trained() -> bool:
    os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
    all_trained = True

    for device_id in DEVICE_IDS:
        model = PHM_LSTM_Model(device_id=device_id)
        if not model.is_trained():
            all_trained = False
            break

    if not all_trained:
        print("检测到部分或全部设备模型未训练，启动完整训练流程...")
        main()

    return True


if __name__ == "__main__":
    main()
