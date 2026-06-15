import random
import time
from abc import ABC, abstractmethod
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import ANOMALY_INJECTION_PROBABILITY


class BaseDevice(ABC):
    def __init__(self, device_id, name, device_type, normal_ranges, units):
        self.device_id = device_id
        self.name = name
        self.device_type = device_type
        self.normal_ranges = normal_ranges
        self.units = units

    def generate_noise(self, value, noise_ratio=0.02):
        range_size = abs(value) * noise_ratio
        if range_size < 0.01:
            range_size = 0.01
        return value + random.uniform(-range_size, range_size)

    def inject_anomaly(self, value, param_name):
        if random.random() < ANOMALY_INJECTION_PROBABILITY:
            low, high = self.normal_ranges[param_name]
            range_size = high - low
            anomaly_type = random.choice(["high_spike", "low_spike", "drift"])
            if anomaly_type == "high_spike":
                return value + range_size * random.uniform(0.5, 1.5)
            elif anomaly_type == "low_spike":
                return max(0, value - range_size * random.uniform(0.5, 1.5))
            else:
                direction = random.choice([1, -1])
                return value + direction * range_size * random.uniform(0.3, 0.8)
        return value

    @abstractmethod
    def collect_data(self):
        pass

    def _generate_base_value(self, param_name):
        low, high = self.normal_ranges[param_name]
        return random.uniform(low, high)

    def _build_data_dict(self, values):
        now = datetime.now()
        data = {
            "device_id": self.device_id,
            "device_name": self.name,
            "device_type": self.device_type,
            "timestamp": now.isoformat(),
            "timestamp_ms": int(time.time() * 1000),
        }
        for param, value in values.items():
            field_name = "acoustic" if param == "acoustic_emission" else param
            data[field_name] = round(value, 4)
        data["_units"] = dict(self.units)
        return data
