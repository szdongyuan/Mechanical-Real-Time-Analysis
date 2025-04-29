import numpy as np

from scipy.io import wavfile

from base.db_manager import DataManage
from consts import db_consts

def save_audio_data(record_audio_data, sameple_rate, file_name):
    print("save_audio_data")
    deta = record_audio_data.copy().T.astype(np.float32)
    wavfile.write(file_name, sameple_rate, deta)

def add_record_audio_data_to_db(record_id: str, 
                                file_path: str, 
                                record_time: str,
                                stop_time: str,
                                audio_status: str = None, 
                                error_time: str = None, 
                                operator: str = None, 
                                deal_result: str = None, 
                                description: str = None):
    columns = db_consts.DB_AUDIO_COLUMNS.copy()
    if audio_status is None:
        audio_status = "no deal"
    data = [record_id, file_path, record_time, stop_time, audio_status, error_time, operator, deal_result, description]
    
    with DataManage(db_consts.DATABASE_PATH) as db:
        code, msg = db.insert_data_into_db("record_audio_data_table" ,columns, [data])
        if code == 0:
            print("add_record_audio_data_to_db success")
        else:
            print("add_record_audio_data_to_db failed")
            print(msg)

def get_record_audio_data_from_db():
    with DataManage(db_consts.DATABASE_PATH) as db:
        print(db_consts.AUDIO_COLUMNS)
        code, result = db.query("record_audio_data_table", db_consts.AUDIO_COLUMNS)
        if code == 0:
            print("get_record_audio_data_from_db success")
            return result
        else:
            print("get_record_audio_data_from_db failed")
            return None
