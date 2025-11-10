import numpy as np

from base.load_config import load_config
from base.pre_processing.preprocessing_manager import PreprocessingManager
from consts import error_code, model_consts
from machine_learning import MODEL_MAPPING



def init_model_from_config(**kwargs):
    """
        Initialize the model based on configuration.

        Returns:
            Instantiate a model class based on the configuration.
    """
    model_config = kwargs.get("model_config")

    if model_config is None:
        config_path = kwargs.get("config_path", model_consts.DEFAULT_DIR + model_consts.CONFIG_PATH)
        model_config = load_config(config_path=config_path, module_name="model")

    model_name = model_config.get("model_name")
    model_obj = MODEL_MAPPING.get(model_name)

    if model_obj is None:
        raise ValueError(f"未在 MODEL_MAPPING 中找到模型: {model_name}。请检查配置或 MODEL_MAPPING。")

    model = model_obj(model_config)
    return model


def preprocess_raw_signals(raw_signals, fs, preprocess_config):
    if not raw_signals:
        return np.array([])

    pm = PreprocessingManager()

    processed_data_list = []
    for i in range(len(raw_signals)):
        processed_item = pm.process(raw_signals[i], fs[i], **preprocess_config)
        processed_data_list.append(processed_item)

    first_item = processed_data_list[0]

    if isinstance(first_item, (list, tuple)):
        num_inputs = len(first_item)
        output_batches = [[] for _ in range(num_inputs)]

        for item_pair in processed_data_list:
            if not isinstance(item_pair, (list, tuple)) or len(item_pair) != num_inputs:
                raise ValueError(f"期望有 {num_inputs} 个元素，但得到了 {len(item_pair)}。")
            for i in range(num_inputs):
                output_batches[i].append(item_pair[i])

        return [np.array(batch) for batch in output_batches]

    else:
        return np.array(processed_data_list)
