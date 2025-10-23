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
    config_path = kwargs.get("config_path", model_consts.DEFAULT_DIR + model_consts.CONFIG_PATH)
    model_config = load_config(config_path=config_path, module_name="model")
    model_obj = MODEL_MAPPING.get(model_config.get("model_name"))
    model = model_obj(model_config)
    return model


def preprocess_raw_signals(raw_signals, fs, preprocess_config):
    """
        Preprocess the original audio signal data.

        Args:
        - raw_signals: list
            List of the original audio data.
        - fs: list
            List of sampling rates for the original audio data.
        - preprocess_config:
            Loaded data preprocessing configuration.

        Returns:
            An array containing preprocessed audio signal data.
    """
    processed_data = []
    pm = PreprocessingManager()
    for i in range(len(raw_signals)):
        processed_data.append(pm.process(raw_signals[i], fs[i], **preprocess_config))
    return np.array(processed_data)