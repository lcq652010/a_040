import os
import sys
import types
import unittest
import importlib.util

import numpy as np
import pandas as pd

LSTM_SERVICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lstm-service")

_config_spec = importlib.util.spec_from_file_location(
    "lstm_service_config_train", os.path.join(LSTM_SERVICE_DIR, "config.py")
)
lstm_config = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(lstm_config)

_original_config = sys.modules.get("config")
_original_model = sys.modules.get("model")
_original_model_lstm = sys.modules.get("model.lstm_model")

sys.modules["config"] = lstm_config

mock_model_pkg = types.ModuleType("model")
mock_model_pkg.__path__ = [os.path.join(LSTM_SERVICE_DIR, "model")]
sys.modules["model"] = mock_model_pkg

mock_lstm_model = types.ModuleType("model.lstm_model")
mock_lstm_model.PHM_LSTM_Model = type("PHM_LSTM_Model", (), {})
sys.modules["model.lstm_model"] = mock_lstm_model

_train_spec = importlib.util.spec_from_file_location(
    "model.train", os.path.join(LSTM_SERVICE_DIR, "model", "train.py"),
)
_train_module = importlib.util.module_from_spec(_train_spec)
sys.modules["model.train"] = _train_module
_train_spec.loader.exec_module(_train_module)

if _original_config is not None:
    sys.modules["config"] = _original_config
else:
    sys.modules.pop("config", None)

if _original_model is not None:
    sys.modules["model"] = _original_model
else:
    sys.modules.pop("model", None)

if _original_model_lstm is not None:
    sys.modules["model.lstm_model"] = _original_model_lstm
else:
    sys.modules.pop("model.lstm_model", None)

sys.modules.pop("model.train", None)

compute_scaler_params = _train_module.compute_scaler_params
create_sequences = _train_module.create_sequences
split_train_test = _train_module.split_train_test
apply_scaling = _train_module.apply_scaling

WINDOW_SIZE = lstm_config.WINDOW_SIZE
FEATURE_COLUMNS = lstm_config.FEATURE_COLUMNS


class TestTrainUtils(unittest.TestCase):
    def test_compute_scaler_params_2d(self):
        features = np.random.randn(100, 5).astype(np.float32)
        targets = np.random.randn(100).astype(np.float32)
        params = compute_scaler_params(features, targets)
        self.assertEqual(len(params["feature_means"]), 5)
        self.assertEqual(len(params["feature_stds"]), 5)
        self.assertIsInstance(params["target_mean"], float)
        self.assertIsInstance(params["target_std"], float)

    def test_compute_scaler_params_3d(self):
        features = np.random.randn(50, 20, 5).astype(np.float32)
        targets = np.random.randn(50).astype(np.float32)
        params = compute_scaler_params(features, targets)
        self.assertEqual(len(params["feature_means"]), 5)
        self.assertEqual(len(params["feature_stds"]), 5)

    def test_create_sequences_shape(self):
        data = np.random.randn(200, 5).astype(np.float32)
        targets = np.random.randn(200).astype(np.float32)
        X, y = create_sequences(data, targets, window_size=20, step=1)
        self.assertEqual(X.shape[0], 200 - 20)
        self.assertEqual(X.shape[1], 20)
        self.assertEqual(X.shape[2], 5)
        self.assertEqual(y.shape[0], 200 - 20)

    def test_apply_scaling_zero_mean(self):
        features = np.random.randn(200, 5).astype(np.float32) * 10 + 50
        targets = np.random.randn(200).astype(np.float32) * 5 + 100
        params = compute_scaler_params(features, targets)
        scaled_features, scaled_targets = apply_scaling(features, targets, params)
        feature_means = scaled_features.mean(axis=0)
        for m in feature_means:
            self.assertAlmostEqual(float(m), 0.0, places=1)

    def test_split_train_test_ratio(self):
        df = pd.DataFrame({"a": range(1000), "b": range(1000)})
        train_df, test_df = split_train_test(df, test_size=0.2)
        self.assertEqual(len(train_df), 800)
        self.assertEqual(len(test_df), 200)


if __name__ == "__main__":
    unittest.main()
