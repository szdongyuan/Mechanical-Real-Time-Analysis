import json

from consts.running_consts import DEFAULT_DIR


def load_devices_data():
    try:
        config_file = DEFAULT_DIR + "ui/ui_config/device_data.json"
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

    except Exception as e:
        print(f"Failed to load the default config file. {e}")
        # 保持返回签名一致，始终返回 5 项
        return None, None, None, None, None
