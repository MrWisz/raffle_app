import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "last_project_dir": "projects",
    "last_export_dir": "exports",
    "window_size": "1000x800",
    "x_color": "black"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

def update_config(key, value):
    config = load_config()
    config[key] = value
    save_config(config)