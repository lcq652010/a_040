import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "root-cause-service"))

from case_base import CaseBase
from similarity_matcher import DTWMatcher, SimilarityMatcher


class TestDTWMatcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_base = CaseBase()
        cls.dtw_matcher = DTWMatcher(cls.case_base)

    def test_dtw_distance_identical(self):
        series = [1.0, 2.0, 3.0, 4.0, 5.0]
        distance = self.dtw_matcher.compute_dtw_distance(series, series)
        self.assertAlmostEqual(distance, 0.0, places=5)

    def test_dtw_distance_different(self):
        s1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        s2 = [10.0, 20.0, 30.0, 40.0, 50.0]
        distance = self.dtw_matcher.compute_dtw_distance(s1, s2)
        self.assertGreater(distance, 0.0)

    def test_dtw_similarity_range(self):
        s1 = [0.2, 0.4, 0.6, 0.8, 1.0]
        s2 = [0.1, 0.3, 0.5, 0.7, 0.9]
        sim = self.dtw_matcher.compute_dtw_similarity(s1, s2)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)

    def test_match_evolution_curves(self):
        t = [i / 19.0 for i in range(20)]
        recent_series = {
            "vibration": [0.2 + 0.3 * x + 0.5 * (x ** 3) for x in t],
            "temperature": [0.3 + 0.4 * (x ** 1.5) for x in t],
            "current": [0.2 + 0.15 * x for x in t],
            "speed": [0.1 + 0.05 * x for x in t],
            "acoustic": [0.25 + 0.35 * (x ** 2) for x in t],
        }
        results = self.dtw_matcher.match_evolution_curves(recent_series, device_type="pump", top_n=3)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIn("dtw_similarity", r)
            self.assertIn("root_cause", r)
            self.assertIn("solution", r)
            self.assertIn("severity", r)


class TestSimilarityMatcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_base = CaseBase()
        cls.matcher = SimilarityMatcher(cls.case_base)

    def test_compute_similarity_range(self):
        case = self.case_base.get_all_cases()[0]
        anomaly_data = {
            "vibration": 0.8,
            "temperature": 0.7,
            "current": 0.4,
            "speed": 0.1,
            "acoustic": 0.7,
        }
        sim = self.matcher.compute_similarity(case, anomaly_data)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)

    def test_find_top_matches(self):
        anomaly_data = {
            "vibration": 0.85,
            "temperature": 0.72,
            "current": 0.45,
            "speed": 0.15,
            "acoustic": 0.78,
        }
        results = self.matcher.find_top_matches(anomaly_data, top_n=3)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIn("similarity", r)
            self.assertIn("root_cause", r)

    def test_analyze_root_cause(self):
        anomaly_data = {
            "vibration": 0.85,
            "temperature": 0.72,
            "current": 0.45,
            "speed": 0.15,
            "acoustic": 0.78,
        }
        result = self.matcher.analyze_root_cause(anomaly_data)
        self.assertIn("primary_cause", result)
        self.assertIn("recommendations", result)
        self.assertIsInstance(result["recommendations"], list)
        self.assertGreater(len(result["recommendations"]), 0)

    def test_dtw_enhanced_similarity(self):
        case = self.case_base.get_all_cases()[0]
        t = [i / 19.0 for i in range(20)]
        anomaly_data_point = {
            "vibration": 0.85,
            "temperature": 0.72,
            "current": 0.45,
            "speed": 0.15,
            "acoustic": 0.78,
        }
        anomaly_data_evo = {
            "vibration": 0.85,
            "temperature": 0.72,
            "current": 0.45,
            "speed": 0.15,
            "acoustic": 0.78,
            "_evolution_data": {
                "vibration": [0.2 + 0.3 * x + 0.5 * (x ** 3) for x in t],
                "temperature": [0.3 + 0.4 * (x ** 1.5) for x in t],
                "current": [0.2 + 0.15 * x for x in t],
                "speed": [0.1 + 0.05 * x for x in t],
                "acoustic": [0.25 + 0.35 * (x ** 2) for x in t],
            },
        }
        sim_point = self.matcher.compute_similarity(case, anomaly_data_point)
        sim_evo = self.matcher.compute_similarity(case, anomaly_data_evo)
        self.assertNotEqual(sim_point, sim_evo)


if __name__ == "__main__":
    unittest.main()
