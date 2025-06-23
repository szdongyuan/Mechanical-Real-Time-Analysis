import json


def load_devices_data():
    try:
        config_file = "D:/gqgit/new_project/ui/ui_config/device_data.json"
        with open(config_file, "r") as f:
            default_config = json.load(f)
            device_name = default_config.get("device_name")
            channels = int(default_config.get("device_chanels", 2))
            selected_channels = list()
            load_selected_channels = default_config.get("selected_channels", [0, 1])
            for i in range(len(load_selected_channels)):
                selected_channels.append(int(load_selected_channels[i]))

            return device_name, channels, selected_channels

    except Exception as e:
        print(f"Failed to load the default config file. {e}")
        return None, None, None
