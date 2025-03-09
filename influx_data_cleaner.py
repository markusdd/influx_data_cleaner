import tkinter as tk
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from influxdb import InfluxDBClient
from config import InfluxDBConfig
from ui import InfluxDataCleaner
from data import DataManager
from platformdirs import user_config_dir, user_state_dir

# Set up initial logging to stderr (console) so it’s available immediately
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_script_dir():
    """Get the directory of the script or executable, handling packaged cases."""
    if getattr(sys, "frozen", False):  # True when running as a PyInstaller executable
        script_dir = os.path.dirname(sys.executable)
        logger.debug(f"Running as packaged executable, script_dir: {script_dir}")
        return script_dir
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logger.debug(f"Running as script, script_dir: {script_dir}")
        return script_dir


def get_app_paths(app_name="influx_data_cleaner"):
    """Determine platform-appropriate paths for config, state, and log files."""
    script_dir = get_script_dir()

    # Use platformdirs for base user directories without app_name nesting
    config_base = (
        user_config_dir()
    )  # e.g., ~/.config, %APPDATA%, ~/Library/Application Support
    state_base = (
        user_state_dir()
    )  # e.g., ~/.local/state, %LOCALAPPDATA%, ~/Library/Application Support

    # Add app_name as a single directory level
    config_dir = os.path.join(config_base, app_name)
    state_dir = os.path.join(state_base, app_name)

    # Ensure directories exist
    try:
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(state_dir, exist_ok=True)
    except OSError as e:
        logger.warning(f"Failed to create directories ({config_dir}, {state_dir}): {e}")
        # Fallback to script_dir if user dirs can’t be created
        config_file = os.path.join(script_dir, f"{app_name}.config.json")
        state_file = os.path.join(script_dir, f"{app_name}.state")
        log_file = os.path.join(script_dir, f"{app_name}.log")
        logger.info(
            f"Falling back to portable mode: config={config_file}, state={state_file}, log={log_file}"
        )
        return config_file, state_file, log_file

    # Define file paths with original filenames
    config_file = os.path.join(config_dir, f"{app_name}.config.json")
    state_file = os.path.join(state_dir, f"{app_name}.state")
    log_file = os.path.join(state_dir, f"{app_name}.log")

    # Migrate existing files from script_dir if they exist
    old_config = os.path.join(script_dir, f"{app_name}.config.json")
    old_state = os.path.join(script_dir, f"{app_name}.state")
    logger.debug(f"Checking for old config at: {old_config}")
    logger.debug(f"Target config path exists? {os.path.exists(config_file)}")
    if os.path.exists(old_config) and not os.path.exists(config_file):
        logger.debug(f"Attempting to migrate config from {old_config} to {config_file}")
        try:
            os.rename(old_config, config_file)
            logger.info(f"Migrated config from {old_config} to {config_file}")
        except OSError as e:
            logger.warning(
                f"Failed to migrate config from {old_config} to {config_file}: {e}"
            )
    else:
        logger.debug(
            f"No migration needed for config: exists={os.path.exists(old_config)}, target_exists={os.path.exists(config_file)}"
        )

    logger.debug(f"Checking for old state at: {old_state}")
    logger.debug(f"Target state path exists? {os.path.exists(state_file)}")
    if os.path.exists(old_state) and not os.path.exists(state_file):
        logger.debug(f"Attempting to migrate state from {old_state} to {state_file}")
        try:
            os.rename(old_state, state_file)
            logger.info(f"Migrated state from {old_state} to {state_file}")
        except OSError as e:
            logger.warning(
                f"Failed to migrate state from {old_state} to {state_file}: {e}"
            )
    else:
        logger.debug(
            f"No migration needed for state: exists={os.path.exists(old_state)}, target_exists={os.path.exists(state_file)}"
        )

    # Fallback to script_dir if it’s writable and user dirs aren’t
    if os.access(script_dir, os.W_OK) and not (
        os.access(config_dir, os.W_OK) and os.access(state_dir, os.W_OK)
    ):
        config_file = os.path.join(script_dir, f"{app_name}.config.json")
        state_file = os.path.join(script_dir, f"{app_name}.state")
        log_file = os.path.join(script_dir, f"{app_name}.log")
        logger.info(
            f"Using portable mode: config={config_file}, state={state_file}, log={log_file}"
        )

    return config_file, state_file, log_file


# Get paths and set up rotating file handler
app_name = "influx_data_cleaner"
config_file, state_file, log_file = get_app_paths(app_name)
handler = RotatingFileHandler(
    log_file, maxBytes=1_000_000, backupCount=3
)  # 1MB limit, 3 backups
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.handlers = []  # Clear the default stderr handler
logger.addHandler(handler)


def main():
    root = tk.Tk()
    config_file, state_file, _ = get_app_paths(app_name)

    config_manager = InfluxDBConfig(config_file)
    influx_config = config_manager.get_influxdb_config()
    client = InfluxDBClient(
        host=influx_config["host"],
        port=influx_config["port"],
        username=influx_config["username"],
        password=influx_config["password"],
        database=influx_config["database"],
    )
    data_manager = DataManager(client)
    app = InfluxDataCleaner(root, config_manager, data_manager, state_file)
    root.mainloop()


if __name__ == "__main__":
    main()
