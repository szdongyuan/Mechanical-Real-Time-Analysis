import joblib
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from machine_learning.model_manager import ModelManager


class GMMManager(ModelManager):

    DEFAULT_CONFIG = {
        'model_name': 'GMMManager',
        'model_init_config': {
            'k_search_range': [1, 9],
            'gmm_params': {
                'covariance_type': "full",
                'reg_covar': 1e-3,
                'n_init': 10,
                'random_state': 0
            }
        },
        'model_fit_config': {
            'threshold_mode': "mad",
            'k_mad': 3.0,
            'percentile': 1,
            'balance_sample_number': False
        },
        'model_predict_config': {
            'manual_threshold': None
        }
    }

    def __init__(self, model_config):
        super().__init__(model_config)
        self.model = None
        self._build_model()

    def _build_model(self):
        self.model = {
            'scaler': StandardScaler(),
            'gmm': None,
            'threshold': None,
            'best_k': None
        }

    def _tau_mad_logp(self, logp_arr: np.ndarray, k: float) -> float:
        med = np.median(logp_arr)
        mad = np.median(np.abs(logp_arr - med)) + 1e-12
        return float(med - 1.4826 * mad * k)

    def fit(self, x_train, y_train=None, **kwargs):
        self.model['scaler'].fit(x_train)
        feats_norm = self.model['scaler'].transform(x_train)

        best_bic, best_k, best_gmm = np.inf, None, None
        k_range = list(range(
            self.init_config['k_search_range'][0],
            self.init_config['k_search_range'][1]
        ))
        for k in k_range:
            gmm_params = self.init_config.get("gmm_params", {})
            gmm = GaussianMixture(n_components=k, **gmm_params).fit(feats_norm)
            bic = gmm.bic(feats_norm)
            if bic < best_bic:
                best_bic, best_k, best_gmm = bic, k, gmm

        self.model['gmm'] = best_gmm
        self.model['best_k'] = best_k

        logp = best_gmm.score_samples(feats_norm)
        threshold_mode = self.fit_config.get('threshold_mode', 'mad')

        if threshold_mode == "percentile":
            p = self.fit_config.get('percentile', 1)
            tau = float(np.percentile(logp, p))
        else:
            k_mad = self.fit_config.get('k_mad', 3.0)
            tau = self._tau_mad_logp(logp, k=k_mad)

        self.model['threshold'] = tau
        return f"finished training GMM (K={best_k})"

    def predict(self, x_test):
        if not self.model or not self.model['gmm'] or not self.model['scaler']:
            raise RuntimeError("模型未正确加载。 'gmm' 或 'scaler' 缺失。")

        feats_norm = self.model['scaler'].transform(x_test)

        scores = self.model['gmm'].score_samples(feats_norm)
        manual_tau = self.pred_config.get("manual_threshold")

        if manual_tau is not None:
            tau = float(manual_tau)
        else:
            raise ValueError(
                "请在 pipeline_predict_config.yml 中设置 'manual_threshold'"
            )
        y_pred = np.where(scores >= tau, 1, 0)

        return y_pred, scores

    def get_cluster_labels(self, x_test):
        if not self.model or not self.model['gmm']:
            raise RuntimeError("模型未训练。")
        feats_norm = self.model['scaler'].transform(x_test)
        labels = self.model['gmm'].predict(feats_norm)
        return labels

    def load_model(self, load_model_path):
        if not isinstance(load_model_path, dict):
            raise ValueError(
                f"GMMManager.load_model 期望一个字典,{type(load_model_path)}。"
            )

        gmm_path = load_model_path.get('gmm')
        scaler_path = load_model_path.get('scaler')

        if not gmm_path or not scaler_path:
            raise ValueError("GMMManager.load_model 传入的字典缺少 'gmm' 或 'scaler' 键")

        self._build_model()

        try:
            gmm_obj = joblib.load(gmm_path)
            if not isinstance(gmm_obj, GaussianMixture):
                raise TypeError(f"路径 {gmm_path} 未包含 GaussianMixture 对象。")
            self.model['gmm'] = gmm_obj

            scaler_obj = joblib.load(scaler_path)
            if not isinstance(scaler_obj, StandardScaler):
                raise TypeError(f"路径 {scaler_path} 未包含 StandardScaler 对象。")
            self.model['scaler'] = scaler_obj

        except Exception as e:
            raise RuntimeError(f"GMMManager.load_model 加载模型失败: {e}")