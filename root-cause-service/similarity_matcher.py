import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean

try:
    from dtaidistance import dtw as dtw_lib
    _DTAIDISTANCE_AVAILABLE = True
except ImportError:
    _DTAIDISTANCE_AVAILABLE = False


class DTWMatcher:
    FEATURES = ["vibration", "temperature", "current", "speed", "acoustic"]

    FEATURE_WEIGHTS = {
        "vibration": 0.25,
        "temperature": 0.20,
        "current": 0.20,
        "speed": 0.15,
        "acoustic": 0.20
    }

    def __init__(self, case_base):
        self.case_base = case_base

    def compute_dtw_distance(self, series1, series2):
        s1 = np.array(series1, dtype=np.float64)
        s2 = np.array(series2, dtype=np.float64)

        if len(s1) == 0 or len(s2) == 0:
            return float('inf')

        if _DTAIDISTANCE_AVAILABLE:
            try:
                return float(dtw_lib.distance(s1, s2))
            except Exception:
                pass

        return self._dtw_distance_fallback(s1, s2)

    @staticmethod
    def _dtw_distance_fallback(s1, s2):
        n = len(s1)
        m = len(s2)
        dtw_matrix = np.full((n + 1, m + 1), np.inf)
        dtw_matrix[0, 0] = 0.0

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = (s1[i - 1] - s2[j - 1]) ** 2
                dtw_matrix[i, j] = cost + min(
                    dtw_matrix[i - 1, j],
                    dtw_matrix[i, j - 1],
                    dtw_matrix[i - 1, j - 1]
                )

        return float(np.sqrt(dtw_matrix[n, m]))

    def compute_dtw_similarity(self, series1, series2):
        dtw_dist = self.compute_dtw_distance(series1, series2)
        if dtw_dist == float('inf'):
            return 0.0
        return 1.0 / (1.0 + dtw_dist)

    def match_evolution_curves(self, recent_series, device_type=None, top_n=3):
        if device_type and device_type.strip():
            candidate_cases = self.case_base.get_cases_by_device_type(device_type)
        else:
            candidate_cases = self.case_base.get_all_cases()

        if not candidate_cases:
            return []

        scored_cases = []
        for case in candidate_cases:
            case_curves = case.get("evolution_curves", {})
            if not case_curves:
                continue

            weighted_sim = 0.0
            total_weight = 0.0

            for feature in self.FEATURES:
                if feature not in recent_series or feature not in case_curves:
                    continue

                input_series = recent_series[feature]
                case_series = case_curves[feature]

                sim = self.compute_dtw_similarity(input_series, case_series)
                weight = self.FEATURE_WEIGHTS.get(feature, 0.2)
                weighted_sim += weight * sim
                total_weight += weight

            if total_weight > 0:
                final_sim = weighted_sim / total_weight
            else:
                final_sim = 0.0

            scored_cases.append({
                "case": case,
                "dtw_similarity": round(final_sim, 4),
                "root_cause": case["root_cause"],
                "solution": case["solution"],
                "severity": case["severity"]
            })

        scored_cases.sort(key=lambda x: x["dtw_similarity"], reverse=True)
        return scored_cases[:top_n]


class SimilarityMatcher:
    FEATURES = ["vibration", "temperature", "current", "speed", "acoustic"]

    FEATURE_WEIGHTS = {
        "vibration": 0.25,
        "temperature": 0.20,
        "current": 0.20,
        "speed": 0.15,
        "acoustic": 0.20
    }

    POINT_WEIGHT = 0.4
    DTW_WEIGHT = 0.6

    def __init__(self, case_base):
        self.case_base = case_base
        self._weight_array = np.array([self.FEATURE_WEIGHTS[f] for f in self.FEATURES])
        self.dtw_matcher = DTWMatcher(case_base)

    def _symptoms_to_vector(self, symptoms):
        return np.array([symptoms[f] for f in self.FEATURES], dtype=np.float64)

    def _weighted_euclidean_similarity(self, vec1, vec2):
        diff = (vec1 - vec2) * self._weight_array
        weighted_dist = np.sqrt(np.sum(diff ** 2))
        max_possible_dist = np.sqrt(np.sum(self._weight_array ** 2))
        normalized_dist = weighted_dist / max_possible_dist if max_possible_dist > 0 else 0.0
        return 1.0 - normalized_dist

    def _cosine_similarity_score(self, vec1, vec2):
        v1 = vec1.reshape(1, -1)
        v2 = vec2.reshape(1, -1)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(cosine_similarity(v1, v2)[0][0])

    def _compute_dtw_score(self, anomaly_data, case):
        evolution_data = anomaly_data.get("_evolution_data")
        if not evolution_data:
            return 0.0

        case_curves = case.get("evolution_curves", {})
        if not case_curves:
            return 0.0

        weighted_sim = 0.0
        total_weight = 0.0

        for feature in self.FEATURES:
            if feature not in evolution_data or feature not in case_curves:
                continue

            input_series = evolution_data[feature]
            case_series = case_curves[feature]

            sim = self.dtw_matcher.compute_dtw_similarity(input_series, case_series)
            weight = self.FEATURE_WEIGHTS.get(feature, 0.2)
            weighted_sim += weight * sim
            total_weight += weight

        if total_weight > 0:
            return weighted_sim / total_weight
        return 0.0

    def compute_similarity(self, case, anomaly_data):
        case_vec = self._symptoms_to_vector(case["symptoms"])
        anomaly_vec = self._symptoms_to_vector(anomaly_data)

        cosine_score = self._cosine_similarity_score(case_vec, anomaly_vec)
        euclidean_score = self._weighted_euclidean_similarity(case_vec, anomaly_vec)

        point_score = 0.5 * cosine_score + 0.5 * euclidean_score

        count_factor = min(1.0, np.log1p(case.get("occurrence_count", 1)) / np.log1p(100))
        point_score = point_score * (0.9 + 0.1 * count_factor)

        has_evolution = "_evolution_data" in anomaly_data and anomaly_data["_evolution_data"]

        if has_evolution:
            dtw_score = self._compute_dtw_score(anomaly_data, case)
            dtw_score = dtw_score * (0.9 + 0.1 * count_factor)
            combined_score = self.POINT_WEIGHT * point_score + self.DTW_WEIGHT * dtw_score
        else:
            combined_score = point_score

        return float(max(0.0, min(1.0, combined_score)))

    def find_top_matches(self, anomaly_data, device_type=None, top_n=3):
        if device_type and device_type.strip():
            candidate_cases = self.case_base.get_cases_by_device_type(device_type)
        else:
            candidate_cases = self.case_base.get_all_cases()

        if not candidate_cases:
            return []

        scored_cases = []
        for case in candidate_cases:
            similarity = self.compute_similarity(case, anomaly_data)
            scored_cases.append({
                "case": case,
                "similarity": round(similarity, 4),
                "root_cause": case["root_cause"],
                "solution": case["solution"],
                "severity": case["severity"]
            })

        scored_cases.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_cases[:top_n]

    def analyze_root_cause(self, anomaly_data, device_type=None):
        top_matches = self.find_top_matches(anomaly_data, device_type, top_n=5)

        if not top_matches:
            return {
                "primary_cause": "未知故障",
                "secondary_factors": [],
                "confidence": 0.0,
                "recommendations": ["建议进行人工全面检查，未匹配到历史相似案例"]
            }

        primary = top_matches[0]
        confidence = primary["similarity"]

        secondary_factors = []
        seen_causes = {primary["case"]["fault_type"]}
        for match in top_matches[1:]:
            fault_type = match["case"]["fault_type"]
            if fault_type not in seen_causes and match["similarity"] >= confidence * 0.6:
                secondary_factors.append({
                    "fault_type": fault_type,
                    "contribution": round(match["similarity"] / (confidence + match["similarity"]), 3),
                    "description": match["root_cause"]
                })
                seen_causes.add(fault_type)
            if len(secondary_factors) >= 2:
                break

        recommendations = self._generate_recommendations(top_matches, anomaly_data, confidence)

        return {
            "primary_cause": primary["case"]["fault_type"],
            "primary_cause_detail": primary["root_cause"],
            "secondary_factors": secondary_factors,
            "confidence": round(confidence, 4),
            "recommendations": recommendations,
            "severity": primary["severity"],
            "matched_case_id": primary["case"]["case_id"]
        }

    def _generate_recommendations(self, top_matches, anomaly_data, confidence):
        recommendations = []
        primary = top_matches[0]

        if confidence >= 0.85:
            recommendations.append(f"高度怀疑为【{primary['case']['fault_type']}】，置信度{confidence:.1%}，建议立即按以下方案处置")
        elif confidence >= 0.7:
            recommendations.append(f"较可能为【{primary['case']['fault_type']}】，置信度{confidence:.1%}，建议优先排查该故障")
        elif confidence >= 0.55:
            recommendations.append(f"可能为【{primary['case']['fault_type']}】，置信度{confidence:.1%}，建议结合其他诊断手段综合判断")
        else:
            recommendations.append(f"匹配度较低（{confidence:.1%}），建议人工检查，可参考相似案例进行排查")

        recommendations.append(f"处置方案：{primary['solution']}")

        severity = primary["severity"]
        if severity >= 4:
            recommendations.append("⚠️ 严重程度较高，建议立即停机检修，避免故障扩大造成设备报废或安全事故")
        elif severity == 3:
            recommendations.append("严重程度中等，建议尽快安排检修，加强运行监控")
        else:
            recommendations.append("严重程度较低，可在合适时机安排检修，持续观察参数变化趋势")

        feature_analysis = self._analyze_dominant_features(anomaly_data)
        if feature_analysis:
            recommendations.append(f"异常特征提示：{feature_analysis}")

        has_evolution = "_evolution_data" in anomaly_data and anomaly_data["_evolution_data"]
        if has_evolution:
            recommendations.append("已结合DTW动态时间规整匹配故障演化趋势，提升诊断准确性")

        if len(top_matches) > 1:
            next_match = top_matches[1]
            if next_match["similarity"] >= confidence * 0.7:
                recommendations.append(f"同时需排除【{next_match['case']['fault_type']}】的可能性，相似度{next_match['similarity']:.1%}")

        return recommendations

    def _analyze_dominant_features(self, anomaly_data):
        feature_names_cn = {
            "vibration": "振动",
            "temperature": "温度",
            "current": "电流",
            "speed": "转速",
            "acoustic": "声发射"
        }

        sorted_features = sorted(
            self.FEATURES,
            key=lambda f: anomaly_data.get(f, 0) * self.FEATURE_WEIGHTS[f],
            reverse=True
        )

        dominant = []
        for f in sorted_features[:2]:
            val = anomaly_data.get(f, 0)
            if val >= 0.6:
                dominant.append(f"{feature_names_cn[f]}异常偏高({val:.1%})")

        return "，".join(dominant) if dominant else ""
