import os
import sys

# DEFAULT_DIR = os.path.split(os.path.realpath(__file__))[0].replace("\\", "/") + "/../"
DEFAULT_DIR = os.path.dirname(os.path.realpath(sys.argv[0])).replace("\\", "/") + "/"

PEAK_DETECTION_SETTINGS_JSON = DEFAULT_DIR + "configs/ai_model_config/peak_detection_models.json"
PEAK_DETECTION_CONFIG_JSON   = DEFAULT_DIR + "configs/ai_model_config/peak_detection_config.json"
HEALTH_SCORE_CONFIG_JSON     = DEFAULT_DIR + "configs/ai_model_config/health_score_config.json"

# basic consts
KB = 1 << 10
MB = 1 << 20
GB = 1 << 30

# log consts
LOG_DIR = DEFAULT_DIR + "log/"

DEFAULT_LOG_FORMATTER = '[%(asctime)s][%(name)s] - [%(levelname)s] - [%(message)s] [%(filename)s:%(lineno)d]'

DEFAULT_LOG = {
    "log_name": LOG_DIR + "main.log",
    "max_size": 2 * MB,
    "backup_count": 9,
    "log_format": DEFAULT_LOG_FORMATTER,
}
AI_LOG = {
    "log_name": LOG_DIR + "ai.log",
    "max_size": 2 * MB,
    "backup_count": 9,
    "log_format": DEFAULT_LOG_FORMATTER,
}
DEBUG_LOG = {
    "log_name": LOG_DIR + "debug.log",
    "max_size": 1 * MB,
    "backup_count": 0,
    "log_format": DEFAULT_LOG_FORMATTER,
}

TEST_LOG = {
    "log_name": LOG_DIR + "test.log",
    "max_size": 100 * KB,
    "backup_count": 0,
    "log_format": DEFAULT_LOG_FORMATTER,
}

LOG_MAPPING = {
    "core": DEFAULT_LOG,
    "train": AI_LOG,
    "evaluate": AI_LOG,
    "predict": AI_LOG,
    "debug": DEBUG_LOG,
    "test": TEST_LOG,
    "db_core": DEFAULT_LOG,
    "soundcard_core": DEFAULT_LOG,
}

MODULES_LOAD = [
    ("加载样式常量", "consts.ui_style_const"),
    ("加载路径常量", "consts.running_consts"),
    ("加载日志模块", "base.log_manager"),
    ("加载数据库模块", "base.database.db_manager"),
    ("加载校准模块", "ui.calibration_window"),
    ("加载3D模型模块", "ui.show_solid_widget"),
    ("加载错误管理模块", "ui.error_manage_widget"),
    ("加载历史数据模块", "ui.historical_data"),
    ("加载主界面模块", "ui.main_window"),
    ("加载完成", None),
]
