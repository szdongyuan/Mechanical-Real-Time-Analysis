import json
import os
import uuid
from datetime import datetime

from keras.models import load_model

from base.file_ops import FileOps
from consts import model_consts, error_code


class TrainingModelManagement(object):
    def __init__(self):
        # 目标 JSON 文件路径
        self.models_json_path = os.path.normpath(os.path.join(model_consts.DEFAULT_DIR, "ui/ui_config/models.json"))

    # ---------------- JSON 读写辅助 ---------------- #
    def _read_models_file(self):
        if not os.path.exists(self.models_json_path):
            return {"models": []}, "models_key"
        try:
            with open(self.models_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {"models": []}, "models_key"
        if isinstance(data, list):
            return data, "list"
        if isinstance(data, dict) and isinstance(data.get("models"), list):
            return data, "models_key"
        return {"models": []}, "models_key"

    def _write_models_file(self, data, container: str) -> tuple:
        try:
            os.makedirs(os.path.dirname(self.models_json_path), exist_ok=True)
            with open(self.models_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return error_code.OK, ""
        except Exception as e:
            return error_code.INVALID_INSERT, str(e)

    def _iterate_items(self, data, container: str):
        items = data if container == "list" else data.get("models", [])
        return items

    def _set_items(self, data, container: str, items: list):
        if container == "list":
            return items
        data["models"] = items
        return data

    # ---------------- 业务方法（JSON） ---------------- #
    def save_training_model_info_to_json(self, signal_length, model_path, config_path, ret_str=None):
        try:
            # 路径规范与模型信息提取
            if os.path.isabs(model_path):
                model_path_to_save = FileOps.get_relative_path(model_path, model_consts.DEFAULT_DIR)
            else:
                model_path_to_save = model_path

            if not os.path.exists(model_path):
                return error_code.INVALID_PATH, "The model path does not exist."
            # config_path 可以是相对或绝对，若是相对则相对 DEFAULT_DIR
            config_abs = config_path
            if not os.path.isabs(config_abs):
                config_abs = os.path.normpath(os.path.join(model_consts.DEFAULT_DIR, config_path))
            if not os.path.exists(config_abs):
                return error_code.INVALID_PATH, "The config path does not exist."

            model_name = os.path.splitext(os.path.basename(model_path))[0]
            training_model = load_model(model_path)
            input_dim = f"{signal_length} x {1}"
            # output_dim、accuracy 等不存入 JSON（保持 UI 的数据结构）

            data, container = self._read_models_file()
            items = self._iterate_items(data, container)

            # 判重：名称或路径重复则拒绝
            for it in items:
                name = it.get("name") or it.get("model_name")
                path = it.get("path") or it.get("model_path")
                if (name and str(name) == model_name) or (path and str(path) == model_path_to_save):
                    return error_code.INVALID_INSERT, "The model info existed."

            # 追加
            items.append({
                "name": model_name,
                "input_dim": input_dim,
                "path": model_path_to_save,
                "config_path": config_path,
            })

            out = self._set_items(data, container, items)
            return self._write_models_file(out, container)
        except Exception as e:
            err_msg = "Failed to save the training model info to json. %s" % (str(e)[:70])
            return error_code.INVALID_INSERT, err_msg

    def register_new_model_info_to_json(self, 
                                        model_name: str = None,
                                        config_path: str = model_consts.CONFIG_PATH, 
                                        input_dim: str = None,
                                        model_type: str = "keras"):
        if model_name and input_dim and config_path:
            try:
                data, container = self._read_models_file()
                items = self._iterate_items(data, container)
                # 生成模型路径（保持原有规则）
                model_path = f"models/{model_name}.{model_type}"

                # 判重
                for it in items:
                    name = it.get("name") or it.get("model_name")
                    if name and str(name) == model_name:
                        return error_code.INVALID_INSERT, "The model info existed."

                items.append({
                    "name": model_name,
                    "input_dim": input_dim,
                    "path": model_path,
                    "config_path": config_path,
                })
                out = self._set_items(data, container, items)
                return self._write_models_file(out, container)
            except Exception as e:
                err_msg = "Failed to save the model info to json. %s" % (str(e)[:70])
                return error_code.INVALID_INSERT, err_msg
        else:
            return error_code.INVALID_DATA_LOADING, "The model info is empty."

    def update_model_info_in_json(self, model_data: dict):
        try:
            data, container = self._read_models_file()
            items = self._iterate_items(data, container)

            old_name = model_data.get("old_name")
            if not old_name:
                return error_code.INVALID_UPDATE, "The model name does not exist."

            updated = False
            for it in items:
                name = it.get("name") or it.get("model_name")
                if name == old_name:
                    # 更新名称或描述/路径
                    if model_data.get("model_name"):
                        new_name = model_data["model_name"]
                        it["name"] = new_name
                        # 同步 path 基于文件名替换
                        base_name = os.path.basename(model_data.get("model_path", it.get("path", "")))
                        it["path"] = f"models/{base_name.replace(old_name, new_name)}"
                    else:
                        # 这里只保留了 UI 使用字段，描述不持久化
                        it["name"] = old_name
                    updated = True
                    break
            if not updated:
                return error_code.INVALID_UPDATE, "The model name does not exist."

            out = self._set_items(data, container, items)
            return self._write_models_file(out, container)
        except Exception as e:
            err_msg = "Failed to update the model info in json. %s" % (str(e)[:70])
            return error_code.INVALID_INSERT, err_msg

    def delete_model_info_from_json(self, model_name: str):
        if not model_name or not isinstance(model_name, str):
            return error_code.INVALID_TYPE_DATA, "The model name is empty or invalid."
        try:
            data, container = self._read_models_file()
            items = self._iterate_items(data, container)
            new_items = []
            deleted = False
            for it in items:
                name = it.get("name") or it.get("model_name")
                if name == model_name:
                    deleted = True
                    continue
                new_items.append(it)
            if not deleted:
                return error_code.INVALID_DELETE, "The model name does not exist."
            out = self._set_items(data, container, new_items)
            return self._write_models_file(out, container)
        except Exception as e:
            err_msg = "The delete operation failed. %s" % (str(e)[:40])
            return error_code.INVALID_DELETE, err_msg

    def get_model_path_from_json(self, model_name):
        try:
            data, container = self._read_models_file()
            items = self._iterate_items(data, container)
            result = []
            for it in items:
                name = it.get("name") or it.get("model_name")
                if name == model_name:
                    result.append({
                        "model_path": it.get("path") or it.get("model_path"),
                        "config_path": it.get("config_path", ""),
                    })
            if result:
                return error_code.OK, result
            else:
                return error_code.INVALID_QUERY, "Failed to query the model's path."
        except Exception as e:
            err_msg = "Failed to query the model path. %s" % (str(e)[:40])
            return error_code.INVALID_QUERY, err_msg

    def get_all_model_name_from_json(self):
        try:
            data, container = self._read_models_file()
            items = self._iterate_items(data, container)
            result = [(it.get("name") or it.get("model_name"), it.get("input_dim", "")) for it in items]
            if result:
                return error_code.OK, result
            else:
                return error_code.INVALID_QUERY, "Failed to query all model name."
        except Exception as e:
            err_msg = "Failed to query the all model name. %s" % (str(e)[:40])
            return error_code.INVALID_QUERY, err_msg

    def get_all_model_info_from_json(self):
        try:
            data, container = self._read_models_file()
            items = self._iterate_items(data, container)
            result = []
            for it in items:
                result.append({
                    "model_name": it.get("name") or it.get("model_name"),
                    "input_dim": it.get("input_dim", ""),
                    "config_path": it.get("config_path", ""),
                    "model_path": it.get("path") or it.get("model_path"),
                })
            if result:
                return error_code.OK, result
            else:
                return error_code.INVALID_QUERY, "Failed to query all model info."
        except Exception as e:
            err_msg = "Failed to query the all model info. %s" % (str(e)[:40])
            return error_code.INVALID_QUERY, err_msg