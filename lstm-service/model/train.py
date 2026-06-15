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
    BASE_MODEL_PATH,
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


def _prepare_device_data(df: pd.DataFrame, scaler_params: dict):
    train_df, test_df = split_train_test(df, test_size=0.2)

    train_features = train_df[FEATURE_COLUMNS].values.astype(np.float32)
    train_targets = train_df[TARGET_COLUMN].values.astype(np.float32)
    test_features = test_df[FEATURE_COLUMNS].values.astype(np.float32)
    test_targets = test_df[TARGET_COLUMN].values.astype(np.float32)

    X_train, y_train = create_sequences(train_features, train_targets, WINDOW_SIZE, step=5)
    X_test, y_test = create_sequences(test_features, test_targets, WINDOW_SIZE, step=1)

    X_train_scaled, y_train_scaled = apply_scaling(X_train, y_train, scaler_params)
    X_test_scaled, y_test_scaled = apply_scaling(X_test, y_test, scaler_params)

    return X_train_scaled, y_train_scaled, X_test_scaled, y_test_scaled, scaler_params


def train_with_transfer_learning():
    print("=" * 70)
    print("迁移学习训练流程")
    print("=" * 70)
    print()

    device_data = load_history_data()

    if not device_data:
        print("错误: 无法加载任何设备数据")
        return

    print(f"\n共发现 {len(device_data)} 台设备数据")
    print()

    print("-" * 70)
    print("第一步: 合并所有设备数据训练基础模型 (base_model)")
    print("-" * 70)

    all_features_list = []
    all_targets_list = []

    for device_id, df in device_data.items():
        features = df[FEATURE_COLUMNS].values.astype(np.float32)
        targets = df[TARGET_COLUMN].values.astype(np.float32)
        all_features_list.append(features)
        all_targets_list.append(targets)

    all_features = np.concatenate(all_features_list, axis=0)
    all_targets = np.concatenate(all_targets_list, axis=0)

    base_scaler_params = compute_scaler_params(
        all_features.reshape(1, -1, len(FEATURE_COLUMNS)),
        all_targets,
    )

    base_model = PHM_LSTM_Model(device_id="base_model")
    base_model.create_model()

    split_idx = int(len(all_features) * 0.8)
    train_features = all_features[:split_idx]
    train_targets = all_targets[:split_idx]
    test_features = all_features[split_idx:]
    test_targets = all_targets[split_idx:]

    X_train, y_train = create_sequences(train_features, train_targets, WINDOW_SIZE, step=5)
    X_test, y_test = create_sequences(test_features, test_targets, WINDOW_SIZE, step=5)

    X_train_scaled, y_train_scaled = apply_scaling(X_train, y_train, base_scaler_params)
    X_test_scaled, y_test_scaled = apply_scaling(X_test, y_test, base_scaler_params)

    print(f"  合并数据总量: {len(all_features)} 条")
    print(f"  训练序列数: {len(X_train_scaled)} | 测试序列数: {len(X_test_scaled)}")
    print(f"  基础模型训练 epochs=50")

    base_model.epochs = 50
    base_history = base_model.train(
        X_train=X_train_scaled,
        y_train=y_train_scaled,
        X_val=X_test_scaled,
        y_val=y_test_scaled,
        scaler_params=base_scaler_params,
    )

    base_model.save_base_model(BASE_MODEL_PATH)

    if len(base_history.get("loss", [])) > 0:
        print(f"\n  基础模型训练完成!")
        print(f"  最终训练 Loss: {base_history['loss'][-1]:.6f}")
        if base_history.get("val_loss"):
            print(f"  最终验证 Loss: {base_history['val_loss'][-1]:.6f}")

    print()
    print("-" * 70)
    print("第二步: 对每台设备加载基础模型并微调")
    print("-" * 70)

    fine_tune_results = {}
    for idx, (device_id, df) in enumerate(device_data.items(), 1):
        print(f"\n[{idx}/{len(device_data)}] 微调设备 {device_id}...")

        device_model = PHM_LSTM_Model(device_id=device_id)

        if not device_model.load_base_model(BASE_MODEL_PATH):
            print(f"  警告: {device_id} 加载基础模型失败，跳过微调")
            continue

        features = df[FEATURE_COLUMNS].values.astype(np.float32)
        targets = df[TARGET_COLUMN].values.astype(np.float32)

        device_scaler_params = compute_scaler_params(
            features.reshape(1, -1, len(FEATURE_COLUMNS)),
            targets,
        )

        X_tr, y_tr, X_val, y_val, device_scaler_params = _prepare_device_data(df, device_scaler_params)

        print(f"  训练序列数: {len(X_tr)} | 验证序列数: {len(X_val)}")
        print(f"  微调 epochs=30, learning_rate=0.0001")

        ft_history = device_model.fine_tune(
            X_train=X_tr,
            y_train=y_tr,
            X_val=X_val,
            y_val=y_val,
            scaler_params=device_scaler_params,
        )

        if len(ft_history.get("loss", [])) > 0:
            print(f"  微调完成! 最终 Loss: {ft_history['loss'][-1]:.6f}")
            if ft_history.get("val_loss"):
                print(f"  最终验证 Loss: {ft_history['val_loss'][-1]:.6f}")

        fine_tune_results[device_id] = ft_history

    print("\n" + "=" * 70)
    print("迁移学习训练流程完成!")
    print(f"  基础模型已保存: {BASE_MODEL_PATH}")
    print(f"  已微调设备数: {len(fine_tune_results)}")
    print(f"  设备模型保存路径: {MODEL_SAVE_PATH}")
    print("=" * 70)

    return fine_tune_results


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
        print("检测到部分或全部设备模型未训练，启动迁移学习训练流程...")
        train_with_transfer_learning()

    return True


if __name__ == "__main__":
    main()
