import os

COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", 10))

CLOUD_UPLOAD_URL = os.getenv("CLOUD_UPLOAD_URL", "http://cloud-backend:8080/api/data")

ANOMALY_INJECTION_PROBABILITY = float(os.getenv("ANOMALY_INJECTION_PROBABILITY", 0.05))

ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", -0.5))

MODEL_SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")

INCREMENTAL_UPDATE_INTERVAL = int(os.getenv("INCREMENTAL_UPDATE_INTERVAL", 100))

DEVICES_CONFIG = {
    "air_compressor": {
        "id": "AC-001",
        "name": "空压机",
        "type": "air_compressor",
        "normal_ranges": {
            "vibration": (2.0, 5.0),
            "temperature": (55.0, 75.0),
            "current": (15.0, 25.0),
            "speed": (2800.0, 3000.0),
            "acoustic_emission": (65.0, 85.0)
        },
        "units": {
            "vibration": "mm/s",
            "temperature": "℃",
            "current": "A",
            "speed": "rpm",
            "acoustic_emission": "dB"
        }
    },
    "centrifugal_pump": {
        "id": "CP-001",
        "name": "离心泵",
        "type": "centrifugal_pump",
        "normal_ranges": {
            "vibration": (1.0, 3.5),
            "temperature": (40.0, 60.0),
            "current": (10.0, 18.0),
            "speed": (1450.0, 1500.0),
            "acoustic_emission": (55.0, 75.0)
        },
        "units": {
            "vibration": "mm/s",
            "temperature": "℃",
            "current": "A",
            "speed": "rpm",
            "acoustic_emission": "dB"
        }
    },
    "fan": {
        "id": "FN-001",
        "name": "风机",
        "type": "fan",
        "normal_ranges": {
            "vibration": (1.5, 4.0),
            "temperature": (45.0, 65.0),
            "current": (8.0, 15.0),
            "speed": (960.0, 1000.0),
            "acoustic_emission": (60.0, 80.0)
        },
        "units": {
            "vibration": "mm/s",
            "temperature": "℃",
            "current": "A",
            "speed": "rpm",
            "acoustic_emission": "dB"
        }
    },
    "conveyor": {
        "id": "CV-001",
        "name": "传送带",
        "type": "conveyor",
        "normal_ranges": {
            "vibration": (0.5, 2.5),
            "temperature": (35.0, 55.0),
            "current": (5.0, 12.0),
            "speed": (60.0, 80.0),
            "acoustic_emission": (50.0, 70.0)
        },
        "units": {
            "vibration": "mm/s",
            "temperature": "℃",
            "current": "A",
            "speed": "rpm",
            "acoustic_emission": "dB"
        }
    },
    "cooling_tower": {
        "id": "CT-001",
        "name": "冷却塔",
        "type": "cooling_tower",
        "normal_ranges": {
            "vibration": (0.8, 2.8),
            "temperature": (28.0, 42.0),
            "current": (12.0, 20.0),
            "speed": (720.0, 750.0),
            "acoustic_emission": (52.0, 72.0)
        },
        "units": {
            "vibration": "mm/s",
            "temperature": "℃",
            "current": "A",
            "speed": "rpm",
            "acoustic_emission": "dB"
        }
    }
}
