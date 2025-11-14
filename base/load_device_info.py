import json
import os

from consts.running_consts import DEFAULT_DIR


def load_devices_data():
    config_file = DEFAULT_DIR + "ui/ui_config/device_data.json"
    if not os.path.exists(config_file):
        return None, None, None, None, None
    with open(config_file, "r") as f:
        default_config = json.load(f)
        device_name = default_config.get("device_name")
        channels = int(default_config.get("device_chanels", 2))
        current_api = default_config.get("current_api")
        mic_index = default_config.get("mic_index")
        selected_channels = list()
        load_selected_channels = default_config.get("selected_channels", [0, 1])
        for i in range(len(load_selected_channels)):
            selected_channels.append(int(load_selected_channels[i]))

        return (device_name, channels, selected_channels, current_api, mic_index)
