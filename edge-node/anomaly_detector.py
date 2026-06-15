import os

import numpy as np
import joblib
from sklearn.ensemble import IsolationForest

from config import ANOMALY_THRESHOLD, MODEL_SAVE_DIR, INCREMENTAL_UPDATE_INTERVAL


class IsolationForestAnomalyDetector:
    def __init__(self, device_type, normal_ranges, device_id, n_estimators=100, n_samples=500):
        self.device_type = device_type
        self.normal_ranges = normal_ranges
        self.param_names = list(normal_ranges.keys())
        self.device_id = device_id
        self.n_estimators = n_estimators
        self.n_samples = n_samples
        self.model = None
        self.data_buffer = []
        self.update_counter = 0

        if not self._load_model():
            self._train()
            self._save_model()

    def _generate_training_data(self):
        n_features = len(self.param_names)
        data = np.zeros((self.n_samples, n_features))
        for i, param in enumerate(self.param_names):
            low, high = self.normal_ranges[param]
            mean = (low + high) / 2
            std = (high - low) / 4
            data[:, i] = np.random.normal(loc=mean, scale=std, size=self.n_samples)
            data[:, i] = np.clip(data[:, i], low, high)
        return data

    def _train(self):
        X_train = self._generate_training_data()
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=0.02,
            random_state=42
        )
        self.model.fit(X_train)

    def _save_model(self):
        os.makedirs(MODEL_SAVE_DIR, exist_ok=True)
        path = os.path.join(MODEL_SAVE_DIR, f"{self.device_id}_iforest.joblib")
        joblib.dump(self.model, path)

    def _load_model(self) -> bool:
        path = os.path.join(MODEL_SAVE_DIR, f"{self.device_id}_iforest.joblib")
        if os.path.exists(path):
            try:
                self.model = joblib.load(path)
                return True
            except Exception:
                return False
        return False

    def detect(self, data_values):
        feature_vector = []
        for param in self.param_names:
            field_name = "acoustic" if param == "acoustic_emission" else param
            value = data_values.get(field_name, data_values.get(param, 0))
            if isinstance(value, dict):
                value = value.get("value", 0)
            feature_vector.append(float(value))

        self.data_buffer.append(feature_vector)
        self.update_counter += 1

        if self.update_counter >= INCREMENTAL_UPDATE_INTERVAL:
            self.incremental_update()

        X = np.array([feature_vector])
        scores = self.model.decision_function(X)
        score = float(scores[0])
        is_anomaly = score < ANOMALY_THRESHOLD
        return is_anomaly, score

    def incremental_update(self):
        X_buffer = np.array(self.data_buffer)
        predictions = self.model.predict(X_buffer)
        n_anomaly = int(np.sum(predictions == -1))
        anomaly_ratio = n_anomaly / len(self.data_buffer)
        contamination = max(0.01, anomaly_ratio)

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=contamination,
            random_state=42
        )
        self.model.fit(X_buffer)
        self._save_model()

        self.data_buffer = []
        self.update_counter = 0
        print(f"[{self.device_id}] 模型已增量更新，contamination={contamination:.4f}")
