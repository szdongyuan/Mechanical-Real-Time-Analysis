import numpy as np
import uuid
import time

from scipy.io import wavfile

from base.db_manager import DataManage
from base.get_mac_address import get_mac_address
from consts import db_consts


def save_audio_data(record_audio_data, sameple_rate, file_name):
    print("save_audio_data")
    deta = record_audio_data.copy().T.astype(np.float32)
    wavfile.write(file_name, sameple_rate, deta)


def add_record_audio_data_to_db(
    record_id: str, file_path: str, record_time: str, stop_time: str, operator: str = None, description: str = None
):
    columns = db_consts.DB_AUDIO_COLUMNS.copy()
    data = [record_id, file_path, record_time, stop_time, operator, description]

    with DataManage(db_consts.DATABASE_PATH) as db:
        code, msg = db.insert_data_into_db("record_audio_data_table", columns, [data])
        if code == 0:
            print("add_record_audio_data_to_db success")
        else:
            print("add_record_audio_data_to_db failed")
            # print(msg)


def get_record_audio_data_from_db():
    with DataManage(db_consts.DATABASE_PATH) as db:
        # print(db_consts.AUDIO_COLUMNS)
        code, result = db.query("record_audio_data_table", db_consts.AUDIO_COLUMNS)
        if code == 0:
            print("get_record_audio_data_from_db success")
            return result
        else:
            print("get_record_audio_data_from_db failed")
            return None


def get_warning_audio_data_from_db():
    with DataManage(db_consts.DATABASE_PATH) as db:
        # print(db_consts.AUDIO_COLUMNS)
        code, result = db.query("warning_audio_data_table", db_consts.WARNING_COLUMNS)
        if code == 0:
            print("get_warning_audio_data_from_db success")
            return result
        else:
            print("get_warning_audio_data_from_db failed")
            return None


def auto_save_data(audio_data, sampling_rate, save_path, selected_channels, start_record_time) -> str:
    mac_address = get_mac_address()
    mac_address = mac_address.replace(":", "") if mac_address else None
    channels = len(selected_channels)
    stop_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
    file_name = (
        save_path
        + "/"
        + mac_address
        + "_"
        + start_record_time
        + "_"
        + stop_time
        + "_"
        + str(sampling_rate)
        + "_"
        + str(channels)
        + ".wav"
    )
    save_audio_data(audio_data, sampling_rate, file_name)

    record_id = str(uuid.uuid1())

    add_record_audio_data_to_db(
        record_id, file_name, start_record_time, time.strftime("%Y%m%d%H%M%S", time.localtime())
    )

    return stop_time


def get_record_audio_data_path(record_time):
    with DataManage(db_consts.DATABASE_PATH) as db:
        result = db.query_matching_data([(record_time,)], "record_audio_data_table", ["record_time"], ["file_path"])
        if result:
            return result[0][0]
        else:
            return None
