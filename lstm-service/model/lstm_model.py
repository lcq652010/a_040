import os
import json
import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    MODEL_SAVE_PATH,
    LSTM_PARAMS,
    FEATURE_COLUMNS,
    WINDOW_SIZE,
    STEPS_PER_HOUR,
    STEPS_PER_MINUTE,
)


class PHM_LSTM_Model:
    def __init__(self, device_id: str, input_dim: int = len(FEATURE_COLUMNS)):
        self.device_id = device_id
        self.input_dim = input_dim
        self.window_size = WINDOW_SIZE
        self.units = LSTM_PARAMS["units"]
        self.layers = LSTM_PARAMS["layers"]
        self.dropout_rate = LSTM_PARAMS["dropout_rate"]
        self.epochs = LSTM_PARAMS["epochs"]
        self.batch_size = LSTM_PARAMS["batch_size"]
        self.learning_rate = LSTM_PARAMS["learning_rate"]
        self.validation_split = LSTM_PARAMS["validation_split"]

        self.model = None
        self.scaler_params = None
        self.model_path = os.path.join(MODEL_SAVE_PATH, f"{device_id}_lstm.h5")
        self.config_path = os.path.join(MODEL_SAVE_PATH, f"{device_id}_config.json")

        os.makedirs(MODEL_SAVE_PATH, exist_ok=True)

    def create_model(self) -> Sequential:
        model = Sequential([
            LSTM(
                units=128,
                return_sequences=True,
                input_shape=(self.window_size, self.input_dim),
                kernel_initializer="glorot_uniform",
            ),
            Dropout(self.dropout_rate),
            LSTM(
                units=64,
                return_sequences=False,
                kernel_initializer="glorot_uniform",
            ),
            Dropout(self.dropout_rate),
            Dense(
                units=32,
                activation="relu",
                kernel_initializer="he_normal",
            ),
            Dense(
                units=1,
                activation="linear",
                kernel_initializer="he_normal",
            ),
        ])

        optimizer = Adam(learning_rate=self.learning_rate, clipnorm=1.0)
        model.compile(
            optimizer=optimizer,
            loss="mean_squared_error",
            metrics=["mean_absolute_error", "mape"],
        )

        self.model = model
        return model

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
        scaler_params: dict = None,
    ) -> dict:
        if self.model is None:
            self.create_model()

        if scaler_params is not None:
            self.scaler_params = scaler_params

        callbacks = [
            EarlyStopping(
                monitor="val_loss" if X_val is not None else "loss",
                patience=15,
                restore_best_weights=True,
                verbose=1,
                min_delta=1e-4,
            ),
            ReduceLROnPlateau(
                monitor="val_loss" if X_val is not None else "loss",
                factor=0.5,
                patience=8,
                min_lr=1e-6,
                verbose=1,
            ),
        ]

        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)
            callbacks.append(
                ModelCheckpoint(
                    self.model_path,
                    monitor="val_loss",
                    save_best_only=True,
                    verbose=0,
                )
            )
        else:
            validation_data = None
            callbacks.append(
                ModelCheckpoint(
                    self.model_path,
                    monitor="loss",
                    save_best_only=True,
                    verbose=0,
                )
            )

        history = self.model.fit(
            X_train,
            y_train,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_data=validation_data,
            validation_split=self.validation_split if validation_data is None else 0.0,
            callbacks=callbacks,
            shuffle=True,
            verbose=1,
        )

        self.save_model()

        return {
            "loss": history.history["loss"],
            "val_loss": history.history.get("val_loss", []),
            "mae": history.history.get("mean_absolute_error", []),
            "val_mae": history.history.get("val_mean_absolute_error", []),
        }

    def predict(self, recent_data: np.ndarray) -> dict:
        if self.model is None:
            if not self.load_model():
                raise FileNotFoundError(f"Model for {self.device_id} not found.")

        if recent_data.ndim == 2:
            recent_data = recent_data.reshape(1, *recent_data.shape)

        if recent_data.shape[1] != self.window_size:
            raise ValueError(
                f"Expected window size {self.window_size}, got {recent_data.shape[1]}"
            )

        if self.scaler_params and "feature_means" in self.scaler_params:
            means = np.array(self.scaler_params["feature_means"])
            stds = np.array(self.scaler_params["feature_stds"])
            scaled_data = (recent_data - means) / (stds + 1e-8)
        else:
            scaled_data = recent_data

        predictions_scaled = self.model.predict(scaled_data, verbose=0)

        if self.scaler_params and "target_mean" in self.scaler_params:
            target_mean = self.scaler_params["target_mean"]
            target_std = self.scaler_params["target_std"]
            rul_steps_array = predictions_scaled.flatten() * target_std + target_mean
        else:
            rul_steps_array = predictions_scaled.flatten()

        rul_steps = float(np.clip(rul_steps_array[0], 0, None))
        rul_minutes = rul_steps / STEPS_PER_MINUTE
        rul_hours = rul_steps / STEPS_PER_HOUR

        confidence = self._calculate_confidence(rul_steps)
        health_score = self._calculate_health_score(rul_steps)

        return {
            "rul_steps": round(rul_steps, 2),
            "rul_minutes": round(rul_minutes, 2),
            "rul_hours": round(rul_hours, 2),
            "confidence": round(confidence, 4),
            "health_score": round(health_score, 4),
        }

    def _calculate_confidence(self, rul_steps: float) -> float:
        max_rul_expected = STEPS_PER_HOUR * 24 * 7
        ratio = rul_steps / max_rul_expected if max_rul_expected > 0 else 0.5
        if ratio > 0.5:
            return 0.95
        elif ratio > 0.2:
            return 0.85
        elif ratio > 0.1:
            return 0.70
        elif ratio > 0.05:
            return 0.55
        else:
            return 0.40

    def _calculate_health_score(self, rul_steps: float) -> float:
        max_rul_expected = STEPS_PER_HOUR * 24 * 7
        raw_score = rul_steps / max_rul_expected if max_rul_expected > 0 else 0.0
        return float(np.clip(raw_score, 0.0, 1.0))

    def save_model(self):
        if self.model is None:
            raise ValueError("No model to save.")

        os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
        self.model.save(self.model_path)

        config_data = {
            "device_id": self.device_id,
            "input_dim": self.input_dim,
            "window_size": self.window_size,
            "units": self.units,
            "layers": self.layers,
            "dropout_rate": self.dropout_rate,
            "scaler_params": self.scaler_params,
        }
        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=2, default=float)

        print(f"[{self.device_id}] 模型已保存: {os.path.basename(self.model_path)}")

    def load_model(self) -> bool:
        if not os.path.exists(self.model_path):
            return False

        if not os.path.exists(self.config_path):
            return False

        try:
            self.model = load_model(self.model_path)

            with open(self.config_path, "r") as f:
                config_data = json.load(f)

            self.scaler_params = config_data.get("scaler_params")
            self.window_size = config_data.get("window_size", self.window_size)
            self.input_dim = config_data.get("input_dim", self.input_dim)

            print(f"[{self.device_id}] 模型加载成功")
            return True
        except Exception as e:
            print(f"[{self.device_id}] 加载模型失败: {e}")
            return False

    def is_trained(self) -> bool:
        return os.path.exists(self.model_path) and os.path.exists(self.config_path)
