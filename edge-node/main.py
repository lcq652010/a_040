import signal
import sys
import time
import logging

import requests

from config import (
    COLLECTION_INTERVAL,
    CLOUD_UPLOAD_URL,
    DEVICES_CONFIG
)
from devices import (
    AirCompressor,
    CentrifugalPump,
    Fan,
    Conveyor,
    CoolingTower
)
from anomaly_detector import IsolationForestAnomalyDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

DEVICE_CLASSES = {
    "air_compressor": AirCompressor,
    "centrifugal_pump": CentrifugalPump,
    "fan": Fan,
    "conveyor": Conveyor,
    "cooling_tower": CoolingTower
}

running = True


def signal_handler(signum, frame):
    global running
    logger.info("收到退出信号，正在关闭边缘节点...")
    running = False


def init_devices():
    devices = []
    for device_key, config in DEVICES_CONFIG.items():
        device_class = DEVICE_CLASSES.get(device_key)
        if device_class:
            device = device_class(config)
            devices.append(device)
            logger.info(f"初始化设备: {device.name} ({device.device_id})")
    return devices


def init_detectors(devices):
    detectors = {}
    for device in devices:
        detector = IsolationForestAnomalyDetector(
            device_type=device.device_type,
            normal_ranges=device.normal_ranges,
            device_id=device.device_id
        )
        detectors[device.device_id] = detector
        logger.info(f"初始化异常检测器: {device.name}")
    return detectors


def upload_to_cloud(payload):
    try:
        response = requests.post(
            CLOUD_UPLOAD_URL,
            json=payload,
            timeout=5
        )
        if response.status_code in (200, 201):
            return True, f"上传成功 (HTTP {response.status_code})"
        else:
            return False, f"上传失败 (HTTP {response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"上传异常: {str(e)}"


def format_data_log(data):
    units = data.get("_units", {})
    parts = []
    for param in ["vibration", "temperature", "current", "speed", "acoustic"]:
        if param in data:
            unit = units.get(param, "")
            if not unit and param == "acoustic":
                unit = units.get("acoustic_emission", "dB")
            parts.append(f"{param}={data[param]}{unit}")
    return ", ".join(parts)


def main():
    global running

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 60)
    logger.info("边缘节点启动")
    logger.info(f"采集间隔: {COLLECTION_INTERVAL}秒")
    logger.info(f"云端地址: {CLOUD_UPLOAD_URL}")
    logger.info("=" * 60)

    devices = init_devices()
    detectors = init_detectors(devices)

    if not devices:
        logger.error("未初始化任何设备，程序退出")
        sys.exit(1)

    cycle = 0
    while running:
        cycle += 1
        logger.info(f"--- 第 {cycle} 轮采集开始 ---")

        for device in devices:
            try:
                data = device.collect_data()
                detector = detectors.get(device.device_id)
                is_anomaly, score = detector.detect(data)

                data_str = format_data_log(data)
                anomaly_str = "是" if is_anomaly else "否"

                log_msg = (
                    f"[{device.name}] "
                    f"数据: {data_str} | "
                    f"异常: {anomaly_str} (分数={score:.4f})"
                )

                if is_anomaly:
                    logger.warning(log_msg)
                    payload = {
                        **data,
                        "anomaly_score": round(score, 4),
                        "is_anomaly": True
                    }
                    success, msg = upload_to_cloud(payload)
                    if success:
                        logger.info(f"[{device.name}] 云端{msg}")
                    else:
                        logger.error(f"[{device.name}] 云端{msg}")
                else:
                    logger.info(log_msg)

            except Exception as e:
                logger.error(f"[{device.name}] 采集异常: {str(e)}", exc_info=True)

        logger.info(f"--- 第 {cycle} 轮采集完成，休眠 {COLLECTION_INTERVAL} 秒 ---")

        for _ in range(COLLECTION_INTERVAL):
            if not running:
                break
            time.sleep(1)

    logger.info("边缘节点已安全退出")


if __name__ == "__main__":
    main()
