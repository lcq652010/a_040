import os
import sys
import tempfile
import shutil
import unittest
import importlib.util

import numpy as np

LSTM_SERVICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lstm-service")

_config_spec = importlib.util.spec_from_file_location(
    "lstm_service_config_tl", os.path.join(LSTM_SERVICE_DIR, "config.py")
)
lstm_config = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(lstm_config)

DEVICE_TYPE_MAP = lstm_config.DEVICE_TYPE_MAP
WINDOW_SIZE = lstm_config.WINDOW_SIZE
FEATURE_COLUMNS = lstm_config.FEATURE_COLUMNS

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

if TF_AVAILABLE:
    _original_config = sys.modules.get("config")
    sys.modules["config"] = lstm_config
    from model.lstm_model import PHM_LSTM_Model
    if _original_config is not None:
        sys.modules["config"] = _original_config
    else:
        sys.modules.pop("config", None)


def _generate_mock_data(n_samples=200, window_size=20, n_features=5):
    X = np.random.randn(n_samples, window_size, n_features).astype(np.float32)
    y = np.random.randn(n_samples).astype(np.float32)
    return X, y


@unittest.skipIf(not TF_AVAILABLE, "TensorFlow 未安装，跳过迁移学习测试")
class TestTransferLearning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="transfer_test_")
        cls.base_model_path = os.path.join(cls.tmp_dir, "base_model")
        cls.model_save_path = os.path.join(cls.tmp_dir, "models")
        os.makedirs(cls.model_save_path, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _create_model(self, device_id="TEST-TL-001"):
        model = PHM_LSTM_Model.__new__(PHM_LSTM_Model)
        model.device_id = device_id
        model.input_dim = len(FEATURE_COLUMNS)
        model.window_size = WINDOW_SIZE
        model.units = 128
        model.layers = 2
        model.dropout_rate = 0.2
        model.epochs = 2
        model.batch_size = 32
        model.learning_rate = 0.001
        model.validation_split = 0.2
        model.model = None
        model.scaler_params = None
        model.model_path = os.path.join(self.model_save_path, f"{device_id}_lstm.h5")
        model.config_path = os.path.join(self.model_save_path, f"{device_id}_config.json")
        return model

    def test_base_model_save_load(self):
        model = self._create_model("TEST-SAVELOAD-BASE")
        model.create_model()
        model.save_base_model(self.base_model_path)

        loaded_model = self._create_model("TEST-SAVELOAD-LOAD")
        result = loaded_model.load_base_model(self.base_model_path)
        self.assertTrue(result)
        self.assertIsNotNone(loaded_model.model)

    def test_freeze_layers(self):
        model = self._create_model("TEST-FREEZE")
        model.create_model()
        model._freeze_layers(-3)

        has_frozen = any(not layer.trainable for layer in model.model.layers)
        self.assertTrue(has_frozen)

    def test_fine_tune_reduces_loss(self):
        model = self._create_model("TEST-FINETUNE")
        model.create_model()
        model.save_base_model(self.base_model_path)

        ft_model = self._create_model("TEST-FINETUNE")
        ft_model.load_base_model(self.base_model_path)

        X_train, y_train = _generate_mock_data(n_samples=64)
        X_val, y_val = _generate_mock_data(n_samples=32)

        scaler_params = {
            "feature_means": [0.0] * len(FEATURE_COLUMNS),
            "feature_stds": [1.0] * len(FEATURE_COLUMNS),
            "target_mean": 0.0,
            "target_std": 1.0,
        }

        history = ft_model.fine_tune(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            scaler_params=scaler_params,
            epochs=2,
            learning_rate=0.001,
        )
        self.assertIsNotNone(history)
        self.assertIn("loss", history)
        self.assertGreater(len(history["loss"]), 0)

    def test_device_type_map(self):
        for device_id, device_type in DEVICE_TYPE_MAP.items():
            self.assertIsInstance(device_type, str)
            self.assertGreater(len(device_type), 0)


class TestDeviceTypeMapNoTF(unittest.TestCase):
    def test_device_type_map_without_tf(self):
        for device_id, device_type in DEVICE_TYPE_MAP.items():
            self.assertIsInstance(device_type, str)
            self.assertGreater(len(device_type), 0)


if __name__ == "__main__":
    unittest.main()
