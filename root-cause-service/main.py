from flask import Flask, request, jsonify
from case_base import CaseBase
from similarity_matcher import SimilarityMatcher
import time

app = Flask(__name__)

case_base = CaseBase()
matcher = SimilarityMatcher(case_base)

REQUIRED_SYMPTOMS = ["vibration", "temperature", "current", "speed", "acoustic"]


@app.route("/api/root-cause/analyze", methods=["POST"])
def analyze_root_cause():
    start_time = time.time()
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "请求体为空，需提供JSON数据"
        }), 400

    required_fields = ["device_id", "device_type", "anomaly_data"]
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "error": f"缺少必要字段: {field}"
            }), 400

    anomaly_data_raw = data["anomaly_data"]

    if isinstance(anomaly_data_raw, list) and len(anomaly_data_raw) > 0:
        latest_record = anomaly_data_raw[-1]
        anomaly_data = {}
        for key, val in latest_record.items():
            if isinstance(val, (int, float)):
                anomaly_data[key] = float(val)
            elif isinstance(val, dict) and "value" in val:
                anomaly_data[key] = float(val["value"])
    elif isinstance(anomaly_data_raw, dict):
        anomaly_data = {}
        for key, val in anomaly_data_raw.items():
            if isinstance(val, (int, float)):
                anomaly_data[key] = float(val)
            elif isinstance(val, dict) and "value" in val:
                anomaly_data[key] = float(val["value"])
    else:
        return jsonify({
            "success": False,
            "error": "anomaly_data 格式错误，需是对象或非空数组"
        }), 400

    normalized_data = {}
    for symptom in REQUIRED_SYMPTOMS:
        if symptom not in anomaly_data:
            alias_map = {"acoustic": "acoustic_emission"}
            if symptom in alias_map and alias_map[symptom] in anomaly_data:
                anomaly_data[symptom] = anomaly_data[alias_map[symptom]]
            elif symptom == "acoustic" and "acoustic_emission" not in anomaly_data:
                ranges = {
                    "compressor": 70, "pump": 60, "fan": 65, "motor": 58,
                    "conveyor": 55, "generator": 62,
                    "air_compressor": 70, "centrifugal_pump": 60,
                    "cooling_tower": 58,
                }
                dt = data.get("device_type", "")
                anomaly_data[symptom] = ranges.get(dt, 60)
            else:
                return jsonify({
                    "success": False,
                    "error": f"anomaly_data 缺少必要症状字段: {symptom}"
                }), 400
        try:
            val = float(anomaly_data[symptom])
            normalized_data[symptom] = max(0.0, min(1.0, val / 100.0))
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": f"症状字段 {symptom} 必须是可转换为数字的值"
            }), 400

    recent_series_raw = data.get("recent_series")
    if recent_series_raw and isinstance(recent_series_raw, dict):
        normalized_evolution = {}
        for feature, values in recent_series_raw.items():
            if not isinstance(values, list) or len(values) == 0:
                continue
            try:
                numeric_values = [float(v) for v in values]
            except (ValueError, TypeError):
                continue
            min_val = min(numeric_values)
            max_val = max(numeric_values)
            if max_val - min_val < 1e-9:
                normalized_evolution[feature] = [0.5] * len(numeric_values)
            else:
                normalized_evolution[feature] = [
                    round((v - min_val) / (max_val - min_val), 4)
                    for v in numeric_values
                ]
        if normalized_evolution:
            normalized_data["_evolution_data"] = normalized_evolution

    device_type = data["device_type"]
    device_id = data["device_id"]

    device_type_aliases = {
        "air_compressor": "compressor",
        "centrifugal_pump": "pump",
        "fan": "fan",
        "conveyor": "conveyor",
        "cooling_tower": "fan",
        "compressor": "compressor",
        "pump": "pump",
        "motor": "motor",
        "generator": "generator",
    }
    normalized_device_type = device_type_aliases.get(device_type, device_type)

    analysis = matcher.analyze_root_cause(normalized_data, normalized_device_type)
    top_matches = matcher.find_top_matches(normalized_data, normalized_device_type, top_n=3)

    top_causes = []
    for idx, match in enumerate(top_matches):
        top_causes.append({
            "rank": idx + 1,
            "fault_type": match["case"]["fault_type"],
            "similarity": match["similarity"],
            "root_cause": match["root_cause"],
            "solution": match["solution"],
            "severity": match["severity"],
            "case_id": match["case"]["case_id"],
            "occurrence_count": match["case"]["occurrence_count"]
        })

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return jsonify({
        "success": True,
        "device_id": device_id,
        "device_type": device_type,
        "top_causes": top_causes,
        "primary_cause": analysis["primary_cause"],
        "primary_cause_detail": analysis.get("primary_cause_detail", ""),
        "secondary_factors": analysis["secondary_factors"],
        "confidence": analysis["confidence"],
        "severity": analysis.get("severity"),
        "recommendations": analysis["recommendations"],
        "matched_case_id": analysis.get("matched_case_id"),
        "analysis_time_ms": elapsed_ms
    }), 200


@app.route("/api/cases", methods=["GET"])
def get_all_cases():
    cases = case_base.get_all_cases()
    return jsonify({
        "success": True,
        "total": len(cases),
        "device_types": case_base.get_device_types(),
        "cases": cases
    }), 200


@app.route("/api/cases/<device_type>", methods=["GET"])
def get_cases_by_device(device_type):
    cases = case_base.get_cases_by_device_type(device_type)
    if not cases:
        available = case_base.get_device_types()
        return jsonify({
            "success": False,
            "error": f"未找到设备类型 '{device_type}' 的案例",
            "available_device_types": available
        }), 404

    return jsonify({
        "success": True,
        "device_type": device_type,
        "total": len(cases),
        "cases": cases
    }), 200


@app.route("/api/cases", methods=["POST"])
def add_case():
    data = request.get_json()
    if not data:
        return jsonify({
            "success": False,
            "error": "请求体为空，需提供案例JSON数据"
        }), 400

    try:
        case_id = case_base.add_case(data)
        return jsonify({
            "success": True,
            "message": f"案例 {case_id} 已成功添加",
            "case_id": case_id,
            "total_cases": case_base.get_case_count()
        }), 201
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "root-cause-service",
        "case_count": case_base.get_case_count(),
        "device_types": case_base.get_device_types(),
        "features": SimilarityMatcher.FEATURES,
        "feature_weights": SimilarityMatcher.FEATURE_WEIGHTS
    }), 200


def print_startup_info():
    print("=" * 60)
    print("  故障根因分析服务 (Root Cause Analysis Service)")
    print("=" * 60)
    print(f"  服务端口: 5001")
    print(f"  案例库总数: {case_base.get_case_count()} 个")
    print(f"  支持设备类型: {', '.join(case_base.get_device_types())}")
    print()
    print("  特征权重配置:")
    for feat, weight in SimilarityMatcher.FEATURE_WEIGHTS.items():
        print(f"    - {feat}: {weight:.0%}")
    print()
    print("  可用接口:")
    print("    POST   /api/root-cause/analyze   - 分析故障根因")
    print("    GET    /api/cases                - 获取所有案例")
    print("    GET    /api/cases/<device_type>  - 按设备类型获取案例")
    print("    POST   /api/cases                - 添加新案例")
    print("    GET    /health                   - 健康检查")
    print("=" * 60)
    print("  服务启动中...")
    print()


if __name__ == "__main__":
    print_startup_info()
    app.run(host="0.0.0.0", port=5001, debug=False)
