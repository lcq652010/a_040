import numpy as np
from sklearn.ensemble import IsolationForest

from config import ANOMALY_THRESHOLD


class IsolationForestAnomalyDetector:
    def __init__(self, device_type, normal_ranges, n_estimators=100, n_samples=500):
        self.device_type = device_type
        self.normal_ranges = normal_ranges
        self.param_names = list(normal_ranges.keys())
        self.n_estimators = n_estimators
        self.n_samples = n_samples
        self.model = None
        self._train()

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

    def detect(self, data_values):
        feature_vector = []
        for param in self.param_names:
            field_name = "acoustic" if param == "acoustic_emission" else param
            value = data_values.get(field_name, data_values.get(param, 0))
            if isinstance(value, dict):
                value = value.get("value", 0)
            feature_vector.append(float(value))
        X = np.array([feature_vector])
        scores = self.model.decision_function(X)
        score = float(scores[0])
        is_anomaly = score < ANOMALY_THRESHOLD
        return is_anomaly, score
