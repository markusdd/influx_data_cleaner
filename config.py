import json
import os
from typing import Dict


class InfluxDBConfig:
    """Handles loading and validating InfluxDB configuration."""

    DEFAULT_CONFIG = {
        "influxdb": {
            "host": "localhost",
            "port": 8086,
            "username": "admin",
            "password": "admin",
            "database": "default",
        },
        "entities": {
            "hm800_ch2_power": {"unit": "W", "min": 0, "max": 1000},
            "hm800_yieldday": {"unit": "Wh", "min": 1, "max": 15},
            "hichi_gth_sml_total_in": {"unit": "kWh", "min": 35000, "max": 50000},
            "hm800_power": {"unit": "W", "min": 0, "max": 5000},
            "hichi_gth_sml_power_curr": {"unit": "W", "min": -1000, "max": 5000},
            "hichi_gth_sml_total_out": {"unit": "kWh", "min": 0, "max": 10000},
        },
    }

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from file, filling in missing or invalid sections with defaults."""
        if not os.path.exists(self.config_path):
            print(
                f"Config file not found at {self.config_path}. Creating with defaults."
            )
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config file: {e}. Resetting to defaults.")
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()

        # Start with an empty config and fill in valid sections or defaults
        final_config = {}
        modified = False

        # Validate and handle 'influxdb' section
        required_influxdb_keys = {"host", "port", "username", "password", "database"}
        if (
            "influxdb" in config
            and isinstance(config["influxdb"], dict)
            and all(k in config["influxdb"] for k in required_influxdb_keys)
        ):
            final_config["influxdb"] = config["influxdb"]
        else:
            print("Invalid or missing 'influxdb' section. Using default.")
            final_config["influxdb"] = self.DEFAULT_CONFIG["influxdb"]
            modified = True

        # Validate and handle 'entities' section
        if "entities" in config and isinstance(config["entities"], dict):
            final_config["entities"] = config["entities"]
        else:
            print("Invalid or missing 'entities' section. Using default.")
            final_config["entities"] = self.DEFAULT_CONFIG["entities"]
            modified = True

        # If we modified anything, save the updated config
        if modified:
            print(
                f"Config at {self.config_path} was incomplete or invalid. Updated with defaults."
            )
            self.save_config(final_config)

        return final_config

    def save_config(self, config: Dict) -> None:
        """Save the current config to file."""
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    def get_influxdb_config(self) -> Dict:
        """Return InfluxDB connection details."""
        return self.config["influxdb"]

    def get_entities(self) -> Dict:
        """Return entity configuration."""
        return self.config["entities"]
