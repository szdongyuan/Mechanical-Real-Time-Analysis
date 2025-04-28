import os
import sqlite3
import uuid
import wave
from datetime import datetime

# from base.load_config import load_config
from base.log_manager import LogManager
from consts import model_consts, error_code


class DataSave(object):
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = None
        self.cursor = None
        self.logger = LogManager("db_core")

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.cursor = self.connection.cursor()
            return error_code.OK, "Successfully connect to database."
        except Exception as e:
            err_msg = "Failed to connect to the database %s" % (str(e)[:40])
            self.logger.error(err_msg)
            return error_code.INVALID_CONNECT_DATABASE, err_msg

    def create_table(self):
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.cursor = self.connection.cursor()
            create_record_audio_data_table_sql = '''
            CREATE TABLE "record_audio_data_table" (
                record_id INTEGER NOT NULL ON CONFLICT ABORT DEFAULT NULL,
                record_time DATETIME NOT NULL,
                stop_time DATETIME NOT NULL,
                error TEXT NOT NULL,
                error_time DATETIME,
                operator TEXT NOT NULL,
                deal_result TEXT,
                description TEXT,
                PRIMARY KEY ("id")
);
            '''
            self.cursor.execute(create_record_audio_data_table_sql)
            self.connection.commit()
            self.logger.info("Table and trigger creation success.")
            return error_code.OK, "Table creation success."
        except Exception as e:
            err_msg = "Failed to create table. %s" % (str(e)[:40])
            self.logger.error(err_msg)
            return error_code.INVALID_CREATE_TABLE, err_msg

    def get_audio_data_list(self, source_dir_list, label):
        data_list = []
        n_file = 0
        for source_dir in source_dir_list:
            source_dir_path = os.path.join(model_consts.STORED_SAMPLE_PATH, source_dir).replace("\\", "/")
            sub_folder_path = source_dir_path + "/" + label
            source_dir_str = source_dir.split("/")
            if not os.path.exists(sub_folder_path):
                continue
            for index, audio_file in enumerate(os.listdir(sub_folder_path)):
                audio_data_id = str(uuid.uuid1())
                file_path = os.path.join(source_dir, label, audio_file).replace("\\", "/")
                product_model = source_dir_str[2].split("_")[0]
                sample_rate = model_consts.SAMPLE_RATE
                record_date = (datetime.strptime(source_dir_str[3], "%Y%m%d")).strftime("%Y-%m-%d")
                sample_stimulus_data = self.get_audio_data_stimulus_info(sub_folder_path + "/" + audio_file)
                result = self.query_matching_data([sample_stimulus_data], "stimulus_signal_table",
                                                  model_consts.STIMULUS_COLUMNS,
                                                  ['stimulus_signal_table.stimulus_id'])
                stimulus_id = result[0][0] if result else None
                sample_data = (audio_data_id, file_path, product_model, sample_rate, record_date, label, stimulus_id)
                data_list.append(sample_data)
                n_file += 1
        return data_list

    def query_matching_data(self, data_list, table_name, check_column, select_column, logical_operator='AND'):
        result = []
        if logical_operator not in ['AND', 'OR']:
            raise ValueError("logical_operator must be 'AND' or 'OR'.")
        base_sql = f' {logical_operator} '.join([f"{column} = ?" for column in check_column])
        for data_item in data_list:
            sql_select = f"SELECT {', '.join(select_column)} FROM {table_name} WHERE {base_sql}"
            self.cursor.execute(sql_select, data_item)
            fet_result = self.cursor.fetchall()
            if fet_result:
                result.extend(row for row in fet_result)
        return result

    def get_audio_data_stimulus_info(self, file_path):
        audio_stimulus_data = ()
        if file_path:
            relpath = os.path.relpath(file_path, model_consts.DEFAULT_DIR).replace("\\", "/")
            relpath_str = relpath.split("/")
            stimulus_type = relpath_str[3].split("_")[0]
            stimulus_method = relpath_str[3].split("_")[1]
            repeat_times = relpath_str[3].split("_")[2]
            start_freq = relpath_str[4].split("_")[1]
            stop_feq = relpath_str[4].split("_")[2]
            sample_rate = model_consts.SAMPLE_RATE
            total_time = self.get_wav_duration(file_path)
            is_default = self.set_default("stimulus_signal_table")
            audio_stimulus_data = (
                stimulus_method, stimulus_type, int(repeat_times), int(start_freq), int(stop_feq), sample_rate, total_time, is_default)
        return audio_stimulus_data

    def set_default(self, table_name):
        select_sql = f"SELECT COUNT(*) FROM {table_name}"
        self.cursor.execute(select_sql)
        record_count = self.cursor.fetchone()[0]
        if record_count == 0:
            is_default = 1
        else:
            is_default = 0
        return is_default

    @staticmethod
    def get_data_id(data_list, id_index: int):
        for i, item in enumerate(data_list):
            data_id = str(uuid.uuid1())
            data_list[i] = item[:id_index] + (data_id,) + item[id_index:]
        return data_list

    @staticmethod
    def get_wav_duration(filepath):
        with wave.open(filepath, 'r') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = frames / float(rate)
        return int(duration)

    def insert_data_into_db(self, table_name, columns: list, data):
        try:
            if len(data) == 0:
                self.logger.info("data empty.")
                return error_code.OK, "data empty."
            values_num = ','.join(['?'] * len(data[0]))
            columns = ', '.join(columns)
            sql = f'INSERT INTO {table_name} ({columns}) VALUES ({values_num});'
            self.cursor.executemany(sql, data)
            self.connection.commit()
            self.logger.info("Insert data successfully.")
            return error_code.OK, "Insert data successfully."
        except Exception as e:
            err_msg = "Failed to insert data into the database. %s" % (str(e)[:40])
            self.logger.error(err_msg)
            return error_code.INVALID_INSERT, err_msg

    def update_table_data(self, table_name, update_data: dict, condition_field: dict, update_time=False):
        try:
            if not isinstance(update_data, dict) or not isinstance(condition_field, dict):
                return error_code.INVALID_TYPE_DATA, "The update_data format is incorrect."
            set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
            if update_time:
                set_clause += ", user_updated_time = DATETIME('now', '+8 hours')"
            where_clause_parts = []
            params = []
            for key, value in condition_field.items():
                if isinstance(value, dict):
                    for op, op_value in value.items():
                        if op == "=":
                            where_clause_parts.append(f"{key} = ?")
                            params.append(op_value)
                        elif op == "!=":
                            where_clause_parts.append(f"{key} != ?")
                            params.append(op_value)
                        else:
                            return error_code.INVALID_TYPE_DATA, f"Unsupported operator: {op}"
                else:
                    where_clause_parts.append(f"{key} = ?")
                    params.append(value)
            where_clause = ' AND '.join(where_clause_parts)
            sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
            self.cursor.execute(sql, list(update_data.values()) + params)
            self.connection.commit()
            if self.cursor.rowcount > 0:
                self.logger.info("Update data successfully.")
                return error_code.OK, "Update data successfully."
            else:
                self.logger.warning("No data has been updated.")
                return error_code.INVALID_UPDATE, "No data has been updated"
        except Exception as e:
            err_msg = "Failed to update data into the database. %s" % (str(e)[:40])
            self.logger.error(err_msg)
            return error_code.INVALID_UPDATE, err_msg

    def query(self, table_name, query_column, query_clause_data: dict = None, FK_related=False):
        try:
            join_sql = ''
            where_clause = ''
            sql_data = []
            if query_clause_data:
                where_clause = ' AND '.join([f"{key} = ?" for key in query_clause_data.keys()])
                sql_data = list(query_clause_data.values())
            query_column = ', '.join(query_column)
            if FK_related:
                join_sql = (' INNER JOIN stimulus_signal_table ON audio_data_table.stimulus_id = '
                            'stimulus_signal_table.stimulus_id')
            sql_query = f"SELECT {query_column} FROM {table_name} {join_sql}"
            if where_clause:
                sql_query += f" WHERE {where_clause};"
            self.cursor.execute(sql_query, sql_data)
            query_data = self.cursor.fetchall()
            return error_code.OK, query_data
        except Exception as e:
            err_msg = "Failed to query data from the table according to the condition. %s" % (str(e)[:40])
            self.logger.error(err_msg)
            return error_code.INVALID_QUERY, err_msg

    def query_conditions(self):
        try:
            placeholders = ''
            query_conditions = []
            params = []
            condition_mapping = self.get_data_config("data_load")
            record_date_mapping = condition_mapping.get("record_date")
            if record_date_mapping is not None:
                for key, data_date_list in record_date_mapping.items():
                    data_date_list = [] if not data_date_list else data_date_list
                    for item in data_date_list:
                        params.append(item)
                        placeholders += '?'
                query_conditions.append(f"record_date IN ({', '.join(placeholders)})")
            for key, value in condition_mapping.items():
                if key == "record_date":
                    continue
                if isinstance(value, list) and value:
                    query_conditions.append(f"{key} IN ({', '.join(['?'] * len(value))})")
                    params.extend(value)
                elif value is not None:
                    query_conditions.append(f"{key} = ?")
                    params.append(value)
            if any(key in condition_mapping for key in model_consts.STIMULUS_COLUMNS):
                join_sql = ("INNER JOIN stimulus_signal_table ON audio_data_table.stimulus_id = "
                            "stimulus_signal_table.stimulus_id")
            select_columns = ', '.join(model_consts.SELECT_COLUMNS)
            base_sql = f'SELECT {select_columns} FROM audio_data_table '
            if query_conditions:
                query_sql = f'{base_sql}{join_sql} WHERE {" AND ".join(query_conditions)}'
            self.cursor.execute(query_sql, params)
            query_data = self.cursor.fetchall()
            return query_data
        except Exception as e:
            err_msg = "Failed to query data from the table according to the condition. %s" % (str(e)[:40])
            self.logger.error(err_msg)
            return error_code.INVALID_QUERY, err_msg

    def delete_all(self, table_name):
        try:
            sql_delete = f'DELETE FROM {table_name}'
            self.cursor.execute(sql_delete)
            self.connection.commit()
            self.logger.info("Delete all information in the table.")
            return error_code.OK, "Delete all information in the table."
        except Exception as e:
            err_msg = "Failed to delete data from the table. %s" % (str(e)[:40])
            self.logger.error(err_msg)
            return error_code.INVALID_DELETE, err_msg

    def delete_with_condition(self, table_name, delete_condition):
        try:
            where_condition = ' AND '.join([f"{key} = ?" for key in delete_condition.keys()])
            sql_delete = f'DELETE FROM {table_name} WHERE {where_condition}'
            self.cursor.execute(sql_delete, list(delete_condition.values()))
            self.connection.commit()
            if self.cursor.rowcount > 0:
                self.logger.info("Delete the data that meets the condition.")
                return error_code.OK, "Delete the data that meets the condition."
            else:
                self.logger.warning("No data found to delete with the given condition.")
                return error_code.INVALID_DELETE, "No data matched the condition. No data was deleted."
        except Exception as e:
            err_msg = "Failed to delete data from the table. %s" % (str(e)[:40])
            self.logger.error(err_msg)
            return error_code.INVALID_DELETE, err_msg

    def close(self):
        try:
            self.connection.close()
            self.logger.shut_down()
            return error_code.OK, "Database connection closed."
        except Exception as e:
            err_msg = "Error closing the connection. %s" % (str(e)[:40])
            self.logger.error(err_msg)
            self.logger.shut_down()
            return error_code.INVALID_CLOSED, err_msg

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if exc_type is not None:
            print(f"DatabaseError: {exc_val}.")
