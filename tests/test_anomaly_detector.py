import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edge-node"))

import config as edge_config
from anomaly_detector import IsolationForestAnomalyDetector


class TestIsolationForestDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="anomaly_test_")
        cls._original_model_save_dir = edge_config.MODEL_SAVE_DIR
        edge_config.MODEL_SAVE_DIR = cls.tmp_dir

    @classmethod
    def tearDownClass(cls):
        edge_config.MODEL_SAVE_DIR = cls._original_model_save_dir
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _create_detector(self, device_type="fan", device_id="TEST-001"):
        normal_ranges = edge_config.DEVICES_CONFIG[device_type]["normal_ranges"]
        return IsolationForestAnomalyDetector(
            device_type=device_type,
            normal_ranges=normal_ranges,
            device_id=device_id,
            n_estimators=50,
            n_samples=200,
        )

    def test_train_new_model(self):
        detector = self._create_detector(device_id="TEST-TRAIN-001")
        self.assertIsNotNone(detector.model)

    def test_detect_normal_data(self):
        detector = self._create_detector(device_id="TEST-NORMAL-001")
        ranges = edge_config.DEVICES_CONFIG["fan"]["normal_ranges"]
        normal_data = {}
        for param, (low, high) in ranges.items():
            field = "acoustic" if param == "acoustic_emission" else param
            normal_data[field] = (low + high) / 2
        is_anomaly, score = detector.detect(normal_data)
        self.assertFalse(is_anomaly)

    def test_detect_anomaly_data(self):
        import anomaly_detector as ad_module
        original_threshold = ad_module.ANOMALY_THRESHOLD
        ad_module.ANOMALY_THRESHOLD = 0.0
        try:
            detector = self._create_detector(device_id="TEST-ANOMALY-001")
            ranges = edge_config.DEVICES_CONFIG["fan"]["normal_ranges"]
            anomaly_data = {}
            for param, (low, high) in ranges.items():
                field = "acoustic" if param == "acoustic_emission" else param
                anomaly_data[field] = -9999
            is_anomaly, score = detector.detect(anomaly_data)
            self.assertTrue(is_anomaly)
        finally:
            ad_module.ANOMALY_THRESHOLD = original_threshold

    def test_save_and_load_model(self):
        detector1 = self._create_detector(device_id="TEST-SAVELOAD-001")
        ranges = edge_config.DEVICES_CONFIG["fan"]["normal_ranges"]
        normal_data = {}
        for param, (low, high) in ranges.items():
            field = "acoustic" if param == "acoustic_emission" else param
            normal_data[field] = (low + high) / 2
        is_anomaly_1, score_1 = detector1.detect(normal_data)

        detector2 = IsolationForestAnomalyDetector(
            device_type="fan",
            normal_ranges=ranges,
            device_id="TEST-SAVELOAD-001",
            n_estimators=50,
            n_samples=200,
        )
        self.assertIsNotNone(detector2.model)
        is_anomaly_2, score_2 = detector2.detect(normal_data)
        self.assertEqual(is_anomaly_1, is_anomaly_2)

    def test_incremental_update(self):
        detector = self._create_detector(device_id="TEST-INCR-001")
        ranges = edge_config.DEVICES_CONFIG["fan"]["normal_ranges"]
        normal_data = {}
        for param, (low, high) in ranges.items():
            field = "acoustic" if param == "acoustic_emission" else param
            normal_data[field] = (low + high) / 2

        for _ in range(100):
            detector.detect(normal_data)

        self.assertEqual(detector.update_counter, 0)
        self.assertEqual(len(detector.data_buffer), 0)

    def test_acoustic_field_alias(self):
        detector = self._create_detector(device_id="TEST-ALIAS-001")
        ranges = edge_config.DEVICES_CONFIG["fan"]["normal_ranges"]
        data_with_emission = {}
        for param, (low, high) in ranges.items():
            if param == "acoustic_emission":
                data_with_emission["acoustic_emission"] = (low + high) / 2
            else:
                data_with_emission[param] = (low + high) / 2
        is_anomaly, score = detector.detect(data_with_emission)
        self.assertIsNotNone(score)


if __name__ == "__main__":
    unittest.main()
