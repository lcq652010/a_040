import os
import sys
import unittest
import importlib.util

import numpy as np

LSTM_SERVICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lstm-service")

_config_spec = importlib.util.spec_from_file_location(
    "lstm_service_config", os.path.join(LSTM_SERVICE_DIR, "config.py")
)
lstm_config = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(lstm_config)

_original_config = sys.modules.get("config")
sys.modules["config"] = lstm_config

_gen_spec = importlib.util.spec_from_file_location(
    "generate_history", os.path.join(LSTM_SERVICE_DIR, "data", "generate_history.py")
)
_gen_module = importlib.util.module_from_spec(_gen_spec)
_gen_spec.loader.exec_module(_gen_module)

if _original_config is not None:
    sys.modules["config"] = _original_config
else:
    sys.modules.pop("config", None)

generate_device_data = _gen_module.generate_device_data
BATHTUB_CONFIG = lstm_config.BATHTUB_CONFIG
FEATURE_COLUMNS = lstm_config.FEATURE_COLUMNS
NORMAL_RANGES = lstm_config.NORMAL_RANGES


class TestBathtubCurve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = generate_device_data("FN-001", "fan", seed=42)

    def test_generate_device_data_shape(self):
        self.assertEqual(len(self.df), 60480)
        expected_cols = set(FEATURE_COLUMNS + ["timestamp", "rul"])
        self.assertTrue(expected_cols.issubset(set(self.df.columns)))
        self.assertEqual(len(self.df.columns), len(FEATURE_COLUMNS) + 2)

    def test_early_failure_noise(self):
        N = len(self.df)
        early_end = int(N * BATHTUB_CONFIG["early_failure_ratio"])
        stable_end = int(N * (BATHTUB_CONFIG["early_failure_ratio"] + (1.0 - BATHTUB_CONFIG["early_failure_ratio"] - BATHTUB_CONFIG["wear_out_ratio"])))
        early_std = self.df["vibration"].iloc[:early_end].std()
        stable_std = self.df["vibration"].iloc[early_end:stable_end].std()
        self.assertGreater(early_std, stable_std)

    def test_stable_period_low_noise(self):
        N = len(self.df)
        early_end = int(N * BATHTUB_CONFIG["early_failure_ratio"])
        stable_end = int(N * (BATHTUB_CONFIG["early_failure_ratio"] + (1.0 - BATHTUB_CONFIG["early_failure_ratio"] - BATHTUB_CONFIG["wear_out_ratio"])))
        stable_std = self.df["vibration"].iloc[early_end:stable_end].std()
        self.assertLess(stable_std, 5.0)

    def test_wear_out_degradation(self):
        N = len(self.df)
        stable_end = int(N * (BATHTUB_CONFIG["early_failure_ratio"] + (1.0 - BATHTUB_CONFIG["early_failure_ratio"] - BATHTUB_CONFIG["wear_out_ratio"])))
        normal_mid = NORMAL_RANGES["fan"]["vibration"][1]
        wear_out_mean = self.df["vibration"].iloc[stable_end:].mean()
        self.assertGreater(wear_out_mean, normal_mid)

    def test_rul_monotonic_decrease(self):
        last_100_mean = self.df["rul"].iloc[-100:].mean()
        first_100_mean = self.df["rul"].iloc[:100].mean()
        self.assertLess(last_100_mean, first_100_mean)

    def test_rul_ends_at_zero(self):
        self.assertLessEqual(self.df["rul"].iloc[-1], 1)


if __name__ == "__main__":
    unittest.main()
