import os
import sys
import json
import time
import numpy as np
from datetime import datetime
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    MODEL_SAVE_PATH,
    WINDOW_SIZE,
    FEATURE_COLUMNS,
    DEVICE_TYPES,
    DEVICE_IDS,
    NORMAL_RANGES,
    STEPS_PER_HOUR,
    STEPS_PER_MINUTE,
)
from model.lstm_model import PHM_LSTM_Model
from model.train import ensure_all_models_trained, train_with_transfer_learning


app = Flask(__name__)


model_registry: dict = {}
SERVICE_START_TIME = None


def initialize_models():
    global model_registry, SERVICE_START_TIME

    print("=" * 60)
    print("LSTM RUL 预测服务初始化中...")
    print("=" * 60)

    ensure_all_models_trained()

    print("\n加载已训练模型到内存中...")
    for device_id in DEVICE_IDS:
        model = PHM_LSTM_Model(device_id=device_id)
        if model.load_model():
            model_registry[device_id] = model
        else:
            print(f"  警告: {device_id} 模型加载失败，尝试迁移学习重新训练...")
            train_with_transfer_learning()
            if model.load_model():
                model_registry[device_id] = model
            else:
                print(f"  错误: {device_id} 迁移学习后仍无法加载模型")

    SERVICE_START_TIME = datetime.now()

    print("\n" + "=" * 60)
    print("LSTM RUL 预测服务初始化完成!")
    print(f"启动时间: {SERVICE_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"已加载模型数量: {len(model_registry)}")
    print(f"支持设备类型: {', '.join(DEVICE_TYPES)}")
    print(f"模型保存路径: {MODEL_SAVE_PATH}")
    print("=" * 60)
    print()


FIELD_ALIASES = {
    "acoustic": ["acoustic", "acoustic_emission"],
    "vibration": ["vibration"],
    "temperature": ["temperature"],
    "current": ["current"],
    "speed": ["speed"],
}


def _get_field_value(record: dict, feature: str):
    aliases = FIELD_ALIASES.get(feature, [feature])
    for alias in aliases:
        if alias in record:
            return record[alias]
    return None


def _generate_fallback_records(device_type: str, count: int) -> list:
    ranges = NORMAL_RANGES.get(device_type, NORMAL_RANGES.get("air_compressor", {}))
    records = []
    for _ in range(count):
        record = {}
        for feat in FEATURE_COLUMNS:
            low, high = ranges.get(feat, (50, 80))
            record[feat] = (low + high) / 2
        records.append(record)
    return records


def validate_recent_data(recent_data: list, device_type: str = None) -> tuple:
    if not isinstance(recent_data, list):
        return False, "recent_data 必须是数组格式"

    if len(recent_data) == 0 and device_type:
        recent_data.extend(_generate_fallback_records(device_type, WINDOW_SIZE))

    if len(recent_data) < WINDOW_SIZE:
        if device_type:
            needed = WINDOW_SIZE - len(recent_data)
            recent_data[0:0] = _generate_fallback_records(device_type, needed)
        else:
            return False, f"recent_data 至少需要 {WINDOW_SIZE} 条记录，当前仅 {len(recent_data)} 条"

    valid_records = []
    for idx, record in enumerate(recent_data[-WINDOW_SIZE:]):
        if not isinstance(record, dict):
            return False, f"recent_data[{idx}] 必须是对象格式"
        fixed_record = dict(record)
        for f in FEATURE_COLUMNS:
            val = _get_field_value(fixed_record, f)
            if val is None:
                ranges = NORMAL_RANGES.get(device_type, {}) if device_type else {}
                low, high = ranges.get(f, (50, 80))
                fixed_record[f] = (low + high) / 2
            else:
                fixed_record[f] = val
        valid_records.append(fixed_record)

    recent_data.clear()
    recent_data.extend(valid_records)
    return True, ""


def prepare_input_array(recent_data: list) -> np.ndarray:
    window_data = recent_data[-WINDOW_SIZE:]
    arr = np.zeros((WINDOW_SIZE, len(FEATURE_COLUMNS)), dtype=np.float32)
    for i, record in enumerate(window_data):
        for j, feature in enumerate(FEATURE_COLUMNS):
            val = _get_field_value(record, feature)
            arr[i, j] = float(val) if val is not None else 0.0
    return arr


def get_device_type(device_id: str) -> str:
    if device_id in DEVICE_TYPE_MAP:
        return DEVICE_TYPE_MAP[device_id]
    try:
        idx = DEVICE_IDS.index(device_id)
        return DEVICE_TYPES[idx % len(DEVICE_TYPES)]
    except ValueError:
        if device_id.startswith("device_"):
            try:
                num = int(device_id.replace("device_", ""))
                return DEVICE_TYPES[(num - 1) % len(DEVICE_TYPES)]
            except ValueError:
                pass
        prefix_map = {
            "AC": "air_compressor",
            "CP": "centrifugal_pump",
            "FN": "fan",
            "CV": "conveyor",
            "CT": "cooling_tower",
        }
        prefix = device_id.split("-")[0] if "-" in device_id else device_id[:2]
        if prefix in prefix_map:
            return prefix_map[prefix]
        return DEVICE_TYPES[0]


@app.route("/api/health", methods=["POST", "GET"])
def health():
    now = datetime.now()
    uptime_seconds = 0
    if SERVICE_START_TIME:
        uptime_seconds = int((now - SERVICE_START_TIME).total_seconds())

    trained_models = []
    for device_id in DEVICE_IDS:
        model = PHM_LSTM_Model(device_id=device_id)
        if model.is_trained():
            trained_models.append(device_id)

    return jsonify({
        "status": "healthy",
        "service": "LSTM RUL Prediction Service",
        "version": "1.0.0",
        "timestamp": now.isoformat(),
        "start_time": SERVICE_START_TIME.isoformat() if SERVICE_START_TIME else None,
        "uptime_seconds": uptime_seconds,
        "models_loaded": len(model_registry),
        "trained_devices": trained_models,
        "supported_device_types": DEVICE_TYPES,
        "window_size": WINDOW_SIZE,
    })


@app.route("/api/devices", methods=["GET"])
def get_devices():
    device_info = []
    for device_id in DEVICE_IDS:
        device_type = get_device_type(device_id)
        model = PHM_LSTM_Model(device_id=device_id)
        is_trained = model.is_trained()
        is_loaded = device_id in model_registry

        device_info.append({
            "device_id": device_id,
            "device_type": device_type,
            "is_trained": is_trained,
            "is_loaded": is_loaded,
            "normal_ranges": NORMAL_RANGES.get(device_type, {}),
        })

    return jsonify({
        "total": len(device_info),
        "devices": device_info,
    })


@app.route("/api/predict/rul", methods=["POST"])
def predict_rul():
    try:
        body = request.get_json(force=True, silent=True)
        if body is None:
            return jsonify({
                "success": False,
                "error": "请求体必须是有效的 JSON 格式",
            }), 400

        device_id = body.get("device_id")
        device_type = body.get("device_type")
        recent_data = body.get("recent_data")

        if not device_id:
            return jsonify({
                "success": False,
                "error": "缺少必填字段: device_id",
            }), 400

        if recent_data is None:
            return jsonify({
                "success": False,
                "error": "缺少必填字段: recent_data",
            }), 400

        if not device_type:
            device_type = get_device_type(device_id)

        is_valid, error_msg = validate_recent_data(recent_data, device_type)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
            }), 400

        if device_id not in model_registry:
            model = PHM_LSTM_Model(device_id=device_id)
            if model.load_model():
                model_registry[device_id] = model
            else:
                return jsonify({
                    "success": False,
                    "error": f"设备 {device_id} 的模型未找到，请先训练模型",
                }), 404

        model = model_registry[device_id]
        input_array = prepare_input_array(recent_data)

        prediction_start = time.time()
        result = model.predict(input_array)
        inference_time_ms = round((time.time() - prediction_start) * 1000, 2)

        response = {
            "success": True,
            "device_id": device_id,
            "device_type": device_type,
            "window_size_used": WINDOW_SIZE,
            "inference_time_ms": inference_time_ms,
            "timestamp": datetime.now().isoformat(),
            "prediction": {
                "rul_steps": result["rul_steps"],
                "rul_minutes": result["rul_minutes"],
                "rul_hours": result["rul_hours"],
                "confidence": result["confidence"],
                "health_score": result["health_score"],
            },
        }

        if result["health_score"] < 0.1:
            response["prediction"]["alert_level"] = "critical"
            response["prediction"]["recommendation"] = "立即停机检查，设备即将失效"
        elif result["health_score"] < 0.25:
            response["prediction"]["alert_level"] = "warning"
            response["prediction"]["recommendation"] = "建议尽快安排维护"
        elif result["health_score"] < 0.5:
            response["prediction"]["alert_level"] = "advisory"
            response["prediction"]["recommendation"] = "注意监控设备状态"
        else:
            response["prediction"]["alert_level"] = "normal"
            response["prediction"]["recommendation"] = "设备状态良好，正常运行"

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"预测过程中发生错误: {str(e)}",
        }), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "error": "接口不存在",
        "available_endpoints": [
            "GET  /api/health",
            "GET  /api/devices",
            "POST /api/health",
            "POST /api/predict/rul",
        ],
    }), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "success": False,
        "error": "HTTP 方法不允许",
    }), 405


if __name__ == "__main__":
    initialize_models()
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"Flask 服务器启动中...")
    print(f"监听地址: {host}:{port}")
    print()
    print("可用接口:")
    print("  GET/POST  /api/health       - 服务健康状态")
    print("  GET       /api/devices      - 已训练设备列表")
    print("  POST      /api/predict/rul  - RUL 预测接口")
    print()

    app.run(host=host, port=port, debug=False, threaded=True)
