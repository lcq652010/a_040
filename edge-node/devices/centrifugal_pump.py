import random
from .base_device import BaseDevice


class CentrifugalPump(BaseDevice):
    def __init__(self, config):
        super().__init__(
            device_id=config["id"],
            name=config["name"],
            device_type=config["type"],
            normal_ranges=config["normal_ranges"],
            units=config["units"]
        )

    def collect_data(self):
        values = {}
        for param in self.normal_ranges.keys():
            val = self._generate_base_value(param)
            val = self.generate_noise(val)
            val = self.inject_anomaly(val, param)
            values[param] = val
        return self._build_data_dict(values)
