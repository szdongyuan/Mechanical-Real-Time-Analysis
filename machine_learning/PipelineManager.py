from machine_learning.model_manager import ModelManager


class PipelineManager(ModelManager):

    DEFAULT_CONFIG = {
        'model_name': 'PipelineManager',
        'model_init_config': {
            'stage1_config': {
                'model_name': 'FusionAutoencoderManager',
                'model_init_config': {
                    "input_shape_vib": [1025, 858, 1],
                    "input_shape_mic": [1025, 858, 1],
                    "encoder_layers_vib": [
                        {"layer_name": "Conv2D",
                         "layer_kwargs": {"filters": 64, "kernel_size": [41, 22], "strides": [41, 22]}},
                        {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                        {"layer_name": "Reshape", "layer_kwargs": {"target_shape": [975, 64]}}
                    ],
                    "encoder_layers_mic": [
                        {"layer_name": "Conv2D",
                         "layer_kwargs": {"filters": 64, "kernel_size": [41, 22], "strides": [41, 22]}},
                        {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                        {"layer_name": "Reshape", "layer_kwargs": {"target_shape": [975, 64]}}
                    ],
                    "fusion_config": {"name": "fusion_layer", "num_layers": 2, "embed_dim": 64, "num_heads": 4},
                    "decoder_layers_vib": [
                        {"layer_name": "Reshape", "layer_kwargs": {"target_shape": [25, 39, 128]}},
                        {"layer_name": "Conv2DTranspose",
                         "layer_kwargs": {"filters": 64, "kernel_size": 3, "strides": [41, 22], "padding": "same",
                                          "activation": "relu"}},
                        {"layer_name": "Conv2D",
                         "layer_kwargs": {"filters": 1, "kernel_size": 3, "padding": "same", "activation": "sigmoid"}}
                    ],
                    "decoder_layers_mic": [
                        {"layer_name": "Reshape", "layer_kwargs": {"target_shape": [25, 39, 128]}},
                        {"layer_name": "Conv2DTranspose",
                         "layer_kwargs": {"filters": 64, "kernel_size": 3, "strides": [41, 22], "padding": "same",
                                          "activation": "relu"}},
                        {"layer_name": "Conv2D",
                         "layer_kwargs": {"filters": 1, "kernel_size": 3, "padding": "same", "activation": "sigmoid"}}
                    ],
                    "pool_features": True,
                    "compile_config": {"loss": "mse"}
                }

            },
            'stage2_config': {
                'model_name': 'GMMManager',
                'model_init_config': {
                    'k_search_range': [1, 9],
                    'gmm_params': {'covariance_type': "full", 'reg_covar': 1e-3}
                },
                'model_fit_config': {
                    'threshold_mode': "mad",
                    'k_mad': 3.0
                }
            }
        },

        'model_fit_config': {},

        'model_predict_config': {
            'manual_threshold': None
        }
    }

    def __init__(self, model_config):
        super().__init__(model_config)
        self.model = None
        self.model_stage1 = None
        self.model_stage2 = None

    def load_model(self, load_model_path=None):
        if not isinstance(load_model_path, dict):
            raise ValueError("请在调用 predict() 时传入一个包含模型路径的字典。")

        s1_model_path = load_model_path.get('ae')
        s2_model_path = load_model_path.get('gmm')
        scaler_model_path = load_model_path.get('scaler')

        missing_keys = []
        if not s1_model_path: missing_keys.append('ae')
        if not s2_model_path: missing_keys.append('gmm')
        if not scaler_model_path: missing_keys.append('scaler')

        if missing_keys:
            raise ValueError(f"传入的 'load_model_path' 字典缺少以下必需键: {missing_keys}")

        # -----------------------------------------------------------------
        # 4. 加载 Stage 1 (AE)
        # -----------------------------------------------------------------
        s1_cfg = self.init_config.get("stage1_config")
        from base.model_config import init_model_from_config
        self.model_stage1 = init_model_from_config(model_config=s1_cfg)

        self.model_stage1.load_model(s1_model_path)
        s2_cfg = self.init_config.get("stage2_config")
        self.model_stage2 = init_model_from_config(model_config=s2_cfg)

        s2_paths_dict = {
            'gmm': s2_model_path,
            'scaler': scaler_model_path
        }

        self.model_stage2.load_model(s2_paths_dict)
        self.model_stage2.pred_config = self.pred_config

    def predict(self, x_test, verbose=1, **kwargs):
        if not self.model_stage1 or not self.model_stage2:
            raise RuntimeError("模型未加载。请在预测前调用 .load_model()")

        features, _ = self.model_stage1.predict(x_test, verbose=verbose)
        y_pred, scores = self.model_stage2.predict(features)
        return y_pred, scores
