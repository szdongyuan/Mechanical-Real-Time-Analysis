import numpy as np
import tensorflow as tf
from keras import Model
from tensorflow.keras import layers, models, Input
from sklearn.model_selection import train_test_split

from machine_learning.model_manager import NeuralNetManager


class FusionAutoencoderManager(NeuralNetManager):
    DEFAULT_CONFIG = {
        "model_name": "FusionAutoencoder",
        "model_init_config": {
            "input_shape_vib": [1025, 858, 1],
            "input_shape_mic": [1025, 858, 1],

            "encoder_layers_vib": [
                {"layer_name": "Conv2D",
                 "layer_kwargs": {"filters": 64, "kernel_size": [41, 22], "strides": [41, 22], "padding": "valid"}},
                {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                {"layer_name": "Reshape", "layer_kwargs": {"target_shape": [975, 64]}}  # 25*39=975
            ],
            "encoder_layers_mic": [
                {"layer_name": "Conv2D",
                 "layer_kwargs": {"filters": 64, "kernel_size": [41, 22], "strides": [41, 22], "padding": "valid"}},
                {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                {"layer_name": "CnnSeBlock", "layer_kwargs": {"filters": 64, "reduction": 4}},
                {"layer_name": "Reshape", "layer_kwargs": {"target_shape": [975, 64]}}
            ],

            "fusion_config": {
                "name": "fusion_layer",
                "num_layers": 2,
                "embed_dim": 64,
                "num_heads": 4
            },
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

            "compile_config": {
                "learning_rate": 1e-3, "loss": "mse", "metrics": ["mae"], "loss_weights": [1.0, 2.0]
            }
        },
        "model_fit_config": {
            "cycles": 1, "epochs": 50, "batch_size": 16, "balance_sample_number": False, "early_stop": True
        },
        "model_predict_config": {}
    }

    def __init__(self, model_config):
        self.feature_extractor = None
        super().__init__(model_config)
        self.init_model()

    def build_layer(self, layer_param):
        layer_name = layer_param.get("layer_name")
        layer_kwargs = layer_param.get("layer_kwargs", {})

        if layer_name == "CnnSeBlock":
            return CnnSeBlock(**layer_kwargs)
        if layer_name == "AsymmetricFusion":
            return AsymmetricFusion(**layer_kwargs)
        if hasattr(layers, layer_name):
            return getattr(layers, layer_name)(**layer_kwargs)
        else:
            raise ValueError(f"未知的层名称: {layer_name}")

    def build_sequential_from_config(self, input_shape, layers_param_list, name):
        model = models.Sequential(name=name)
        model.add(Input(shape=input_shape, name=f"{name}_input"))
        for layer_param in layers_param_list:
            model.add(self.build_layer(layer_param))
        return model

    def init_model(self):
        vib_shape = self.init_config.get("input_shape_vib")
        mic_shape = self.init_config.get("input_shape_mic")
        vib_input = Input(shape=vib_shape, name="vib_input")
        mic_input = Input(shape=mic_shape, name="mic_input")

        enc_layers_v = self.init_config.get("encoder_layers_vib", [])
        enc_layers_m = self.init_config.get("encoder_layers_mic", [])
        vib_encoder = self.build_sequential_from_config(vib_shape, enc_layers_v, "vib_encoder")
        mic_encoder = self.build_sequential_from_config(mic_shape, enc_layers_m, "mic_encoder")
        vib_tokens = vib_encoder(vib_input)
        mic_tokens = mic_encoder(mic_input)

        fus_cfg = self.init_config.get("fusion_config", {}).copy()
        if "name" not in fus_cfg:
            fus_cfg["name"] = "fusion_layer"
        fus_cfg.pop("type", None)

        fusion_layer = AsymmetricFusion(**fus_cfg)
        fused_tokens = fusion_layer([vib_tokens, mic_tokens])

        dec_layers_v = self.init_config.get("decoder_layers_vib", [])
        dec_layers_m = self.init_config.get("decoder_layers_mic", [])
        decoder_input_shape = fused_tokens.shape[1:]
        vib_decoder = self.build_sequential_from_config(decoder_input_shape, dec_layers_v, "vib_decoder")
        mic_decoder = self.build_sequential_from_config(decoder_input_shape, dec_layers_m, "mic_decoder")
        vib_recon = vib_decoder(fused_tokens)
        mic_recon = mic_decoder(fused_tokens)

        self.model = Model(
            inputs=[vib_input, mic_input],
            outputs=[vib_recon, mic_recon],
            name="FusionAutoencoder"
        )

        if self.init_config.get("pool_features", True):
            pooled_features = layers.GlobalAveragePooling1D(name="feature_pooling")(fused_tokens)
            self.feature_extractor = Model(inputs=[vib_input, mic_input], outputs=pooled_features,
                                           name="FeatureExtractor")
        else:
            self.feature_extractor = Model(inputs=[vib_input, mic_input], outputs=fused_tokens, name="FeatureExtractor")

        comp_cfg = self.init_config.get("compile_config", {})
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(
                learning_rate=comp_cfg.get("learning_rate", 1e-3),
                clipnorm=1.0
            ),
            loss=comp_cfg.get("loss", "mse"),
            metrics=comp_cfg.get("metrics", []),
            loss_weights=comp_cfg.get("loss_weights", [1.0, 2.0]),
        )

    def fit(self, x_train, y_train, validation_data=None):
        fit_kwargs = self.parse_fit_config()
        cycles = self.fit_config.get("cycles", 1)

        if not isinstance(x_train, list) or len(x_train) != 2: raise ValueError(
            "x_train 必须是 [vib_data, mic_data] 格式的列表")
        if not isinstance(y_train, list) or len(y_train) != 2: raise ValueError(
            "y_train 必须是 [vib_target, mic_target] 格式的列表")

        vib_all, mic_all = x_train[0], x_train[1]
        vib_target_all, mic_target_all = y_train[0], y_train[1]

        history = None
        for i in range(cycles):
            indices = np.arange(vib_all.shape[0])
            train_indices, val_indices = train_test_split(indices, test_size=0.2, random_state=42 + i)

            x_fit = [vib_all[train_indices], mic_all[train_indices]]
            y_fit = [vib_target_all[train_indices], mic_target_all[train_indices]]
            x_val = [vib_all[val_indices], mic_all[val_indices]]
            y_val = [vib_target_all[val_indices], mic_target_all[val_indices]]

            history = self.model.fit(
                x_fit, y_fit,
                validation_data=(x_val, y_val),
                **fit_kwargs
            )
            print("finish cycle %s" % i)

        return history

    def predict(self, x_test, verbose=1, **kwargs):
        if not self.feature_extractor: raise RuntimeError("模型未正确初始化, 'feature_extractor' 不存在。")
        if not isinstance(x_test, list) or len(x_test) != 2: raise ValueError(
            "x_test 必须是 [vib_data, mic_data] 格式的列表")

        fused_tokens = self.feature_extractor.predict(x_test, verbose=verbose)
        return fused_tokens, None

    def load_model(self, load_model_path):
        custom_objects = {
            "CnnSeBlock": CnnSeBlock,
            "AsymmetricFusion": AsymmetricFusion,
        }
        self.model = tf.keras.models.load_model(load_model_path, custom_objects=custom_objects, compile=True)
        try:
            vib_input = self.model.get_layer("vib_input").output
            mic_input = self.model.get_layer("mic_input").output
            fusion_layer_name = self.init_config.get("fusion_config", {}).get("name", "fusion_layer")

            fused_tokens = self.model.get_layer(fusion_layer_name).output

            if self.init_config.get("pool_features", True):
                pooled_features = layers.GlobalAveragePooling1D(name="feature_pooling")(fused_tokens)
                self.feature_extractor = Model(inputs=[vib_input, mic_input], outputs=pooled_features,
                                               name="FeatureExtractor_Rebuilt")
            else:
                self.feature_extractor = Model(inputs=[vib_input, mic_input], outputs=fused_tokens,
                                               name="FeatureExtractor_Rebuilt")
        except Exception as e:
            raise RuntimeError(f"无法重建 'feature_extractor' 模型: {e}")


@tf.keras.utils.register_keras_serializable()
class CnnSeBlock(layers.Layer):
    def __init__(self, filters, reduction=4, **kwargs):
        super().__init__(**kwargs)
        self.filters, self.reduction = filters, reduction
        self.conv1 = layers.Conv2D(filters, 3, padding="same", use_bias=False)
        self.ln1 = layers.LayerNormalization(epsilon=1e-6)
        self.act1 = layers.Activation("relu")
        self.conv2 = layers.Conv2D(filters, 3, padding="same", use_bias=False)
        self.ln2 = layers.LayerNormalization(epsilon=1e-6)
        self.gap = layers.GlobalAveragePooling2D()
        self.reshape = layers.Reshape((1, 1, filters))
        hidden = max(8, filters // reduction)
        self.fc1 = layers.Dense(hidden, activation="relu")
        self.fc2 = layers.Dense(filters, activation="sigmoid")
        self.multiply = layers.Multiply()
        self.add = layers.Add()

    def call(self, x):
        shortcut = x
        y = self.conv1(x)
        y = self.ln1(y)
        y = self.act1(y)
        y = self.conv2(y)
        y = self.ln2(y)
        se = self.gap(y)
        se = self.reshape(se)
        se = self.fc1(se)
        se = self.fc2(se)
        y = self.multiply([y, se])
        return self.add([shortcut, y])

    def get_config(self):
        cfg = super().get_config()
        cfg.update({"filters": self.filters, "reduction": self.reduction})
        return cfg

    def build(self, input_shape):
        super().build(input_shape)


@tf.keras.utils.register_keras_serializable()
class AsymmetricFusion(layers.Layer):
    def __init__(self, embed_dim: int, num_heads: int, num_layers: int, dropout: float = 0.1,
                 name: str = "fusion_module", **kwargs):
        super().__init__(name=name, **kwargs)
        self.embed_dim, self.num_heads, self.num_layers, self.dropout = embed_dim, num_heads, num_layers, dropout
        self.ln_q_v, self.ln_k_v, self.mha_vm, self.add_v, self.ffn_v, self.ffn_add_v = [], [], [], [], [], []
        for i in range(self.num_layers):
            self.ln_q_v.append(layers.LayerNormalization(epsilon=1e-6, name=f"{self.name}_v_ln_q_{i + 1}"))
            self.ln_k_v.append(layers.LayerNormalization(epsilon=1e-6, name=f"{self.name}_a_ln_k_{i + 1}"))
            self.mha_vm.append(
                layers.MultiHeadAttention(num_heads=self.num_heads, key_dim=self.embed_dim // self.num_heads,
                                          value_dim=self.embed_dim // self.num_heads, dropout=self.dropout,
                                          name=f"{self.name}_v_queries_a_{i + 1}"))
            self.add_v.append(layers.Add(name=f"{self.name}_v_resattn_{i + 1}"))
            self.ffn_v.append(self._build_ffn_block(self.embed_dim, prefix=f"{self.name}_v_ffn_{i + 1}"))
            self.ffn_add_v.append(layers.Add(name=f"{self.name}_v_ffn_add_{i + 1}"))
        self.concat = layers.Concatenate(axis=-1, name=f"{self.name}_concat")
    
    def build(self, input_shape):
        super().build(input_shape)

    @staticmethod
    def _build_ffn_block(dim, prefix: str):
        return tf.keras.Sequential([layers.LayerNormalization(epsilon=1e-6, name=f"{prefix}_ln"),
                                    layers.Dense(dim * 4, activation="relu", name=f"{prefix}_fc1"),
                                    layers.Dropout(0.1, name=f"{prefix}_drop"),
                                    layers.Dense(dim, name=f"{prefix}_fc2")], name=prefix)

    def call(self, inputs, training=None):
        x_vib, x_mic = inputs
        for i in range(self.num_layers):
            vib_base = x_vib
            q_v = self.ln_q_v[i](vib_base)
            k_v = self.ln_k_v[i](x_mic)
            attn_vm = self.mha_vm[i](q_v, k_v, training=training)
            x_vib = self.add_v[i]([vib_base, attn_vm])
            ffn_v_in = x_vib
            x_vib_ffn = self.ffn_v[i](ffn_v_in, training=training)
            x_vib = self.ffn_add_v[i]([ffn_v_in, x_vib_ffn])
        return self.concat([x_vib, x_mic])

    def get_config(self):
        cfg = super().get_config()
        cfg.update({"embed_dim": self.embed_dim, "num_heads": self.num_heads, "num_layers": self.num_layers,
                    "dropout": self.dropout})
        return cfg
