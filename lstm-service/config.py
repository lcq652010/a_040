import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_SAVE_PATH = os.path.join(BASE_DIR, "models")
HISTORY_DATA_PATH = os.path.join(BASE_DIR, "data", "history")

WINDOW_SIZE = 20
FORECAST_HORIZON = 100
SAMPLING_INTERVAL_SECONDS = 10
STEPS_PER_HOUR = 3600 // SAMPLING_INTERVAL_SECONDS
STEPS_PER_MINUTE = 60 // SAMPLING_INTERVAL_SECONDS
TOTAL_STEPS_ONE_WEEK = 7 * 24 * STEPS_PER_HOUR

LSTM_PARAMS = {
    "units": 128,
    "layers": 2,
    "epochs": 100,
    "batch_size": 32,
    "dropout_rate": 0.2,
    "validation_split": 0.2,
    "learning_rate": 0.001,
}

BASE_MODEL_PATH = os.path.join(BASE_DIR, "models", "base_model")
FINE_TUNE_EPOCHS = 30
FINE_TUNE_LEARNING_RATE = 0.0001
FINE_TUNE_LAYERS = -3

BATHTUB_CONFIG = {
    "early_failure_ratio": 0.05,
    "wear_out_ratio": 0.15,
    "early_failure_hazard": 2.0,
    "wear_out_hazard": 3.0,
    "stable_hazard": 0.3,
}

DEVICE_TYPES = [
    "air_compressor",
    "centrifugal_pump",
    "fan",
    "conveyor",
    "cooling_tower",
]

DEVICE_IDS = ["AC-001", "CP-001", "FN-001", "CV-001", "CT-001"]

DEVICE_TYPE_MAP = {
    "AC-001": "air_compressor",
    "CP-001": "centrifugal_pump",
    "FN-001": "fan",
    "CV-001": "conveyor",
    "CT-001": "cooling_tower",
}

FEATURE_COLUMNS = [
    "vibration",
    "temperature",
    "current",
    "speed",
    "acoustic",
]

TARGET_COLUMN = "rul"

NORMAL_RANGES = {
    "air_compressor": {
        "vibration": (2.0, 5.0),
        "temperature": (55.0, 75.0),
        "current": (15.0, 25.0),
        "speed": (2800.0, 3000.0),
        "acoustic": (65.0, 85.0),
    },
    "centrifugal_pump": {
        "vibration": (1.0, 3.5),
        "temperature": (40.0, 60.0),
        "current": (10.0, 18.0),
        "speed": (1450.0, 1500.0),
        "acoustic": (55.0, 75.0),
    },
    "fan": {
        "vibration": (1.5, 4.0),
        "temperature": (45.0, 65.0),
        "current": (8.0, 15.0),
        "speed": (960.0, 1000.0),
        "acoustic": (60.0, 80.0),
    },
    "conveyor": {
        "vibration": (0.5, 2.5),
        "temperature": (35.0, 55.0),
        "current": (5.0, 12.0),
        "speed": (60.0, 80.0),
        "acoustic": (50.0, 70.0),
    },
    "cooling_tower": {
        "vibration": (0.8, 2.8),
        "temperature": (28.0, 42.0),
        "current": (12.0, 20.0),
        "speed": (720.0, 750.0),
        "acoustic": (52.0, 72.0),
    },
}
