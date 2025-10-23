import os
import sys

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


DEFAULT_DIR = os.path.split(os.path.realpath(__file__))[0].replace("\\", "/") + "/../"
# DEFAULT_DIR = os.path.dirname(os.path.realpath(sys.argv[0])).replace("\\", "/") + "/"

STORED_SAMPLE_PATH = DEFAULT_DIR + "audio_data/stored_sample"
STORED_RECORDED_PATH = DEFAULT_DIR + "audio_data/stored_data"
STORED_RECORDED_OK_PATH = DEFAULT_DIR + "audio_data/stored_data/OK"
STORED_RECORDED_NG_PATH = DEFAULT_DIR + "audio_data/stored_data/NG"
STORED_STIMULUS_PATH = DEFAULT_DIR + "audio_data/stimulus"
JSON_DIR_PATH = DEFAULT_DIR + "ui/ui_config"

DATABASE_PATH = DEFAULT_DIR + "database/audio_data.db"

SAMPLE_RATE = 44100
POSITIVE_SAMPLE_LABEL = "OK"
NEGATIVE_SAMPLE_LABEL = "NG"
DB_AUDIO_COLUMNS = ["record_id", "file_path", "record_time", "stop_time", "operator", "description"]
DB_WARNING_COLUMNS = [
    "warning_time",
    "warning_level",
    "warning_status",
    "charge_person",
    "file_name",
    "record_id",
    "record_time",
    "stop_time",
    "deal_status",
    "description",
]

DB_USERS_COLUMNS = ["user_id", "user_name", "password", "access_level", "user_created_time", "user_updated_time"]
AUDIO_COLUMNS = [col for col in DB_AUDIO_COLUMNS if col != "record_id"]
WARNING_COLUMNS = [col for col in DB_WARNING_COLUMNS if col != "record_id"]

INSERT_USERS_COLUMNS = [col for col in DB_USERS_COLUMNS if col != "user_id"]
USERS_COLUMNS = ["user_name", "password", "access_level"]
SELECT_COLUMNS = [
    "file_path",
    "product_model",
    "record_date",
    "stimulus_method",
    "stimulus_type",
    "total_time",
    "audio_data_table.stimulus_id",
    "labels",
]
