import random
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, List

from base.load_config import load_config
from consts.running_consts import HEALTH_SCORE_CONFIG_JSON


class HealthScoreGenerator:
    """
    根据峰值检测结果生成健康评分：
    - 未超阈值 => 使用 normal_range 随机取值
    - 超过阈值 => 使用 abnormal_range 随机取值
    - 无检测结果 => 使用默认的 normal_range 生成兜底健康分
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        module_name: str = "health_score",
    ):
        self.config_path = self._resolve_config_path(config_path)
        self.module_name = module_name
        self.config = self._load_config()

        precision = self.config.get("precision", 1)
        self.precision = int(precision) if isinstance(precision, int) else 1

        seed = self.config.get("random_seed", None)
        self._rng = random.Random(seed)

        self.channel_ranges: Dict[str, Dict[str, Sequence[float]]] = self.config.get("channels", {})
        self.default_ranges: Dict[str, Sequence[float]] = self.config.get("defaults", {})

        aggregate = self.config.get("aggregate")
        if aggregate is None and self.channel_ranges:
            aggregate = {
                "name": "overall",
                "channels": list(self.channel_ranges.keys()),
                "method": "average",
            }
        self.aggregate_config: Optional[Dict[str, Any]] = aggregate

    def generate_scores(
        self,
        peak_results: Optional[Mapping[str, Any]] = None,
        channel_names: Optional[Iterable[str]] = None,
    ) -> Dict[str, float]:
        """
        Args:
            peak_results: 峰值检测结果，结构示例：
                {
                    "good_motor": {"peak_value": 0.42, "threshold": 0.5},
                    "bad_motor": {"exceeded": True},
                    "channel_c": False
                }
                可为空；空时将按 channel_names 或配置里的 channels 兜底。
            channel_names: 在没有检测结果时，用于生成评分的通道列表。

        Returns:
            {"good_motor": 93.4, "bad_motor": 33.1, "channel_c": 78.2}
        """
        peak_results = peak_results or {}

        if peak_results:
            items = peak_results.items()
        else:
            names = list(channel_names or self.channel_ranges.keys())
            if not names:
                raise ValueError("没有峰值结果且配置中缺少 channel 列表，无法生成健康分")
            items = [(name, False) for name in names]

        scores: Dict[str, float] = {}
        for channel_name, result in items:
            system_status = self.judge_system_status(result)
            min_val, max_val = self._get_range(channel_name, system_status)
            score = self._rng.uniform(min_val, max_val)
            scores[channel_name] = self._round_score(score)

        aggregate_score = self._aggregate_scores(scores)
        if aggregate_score is not None:
            aggregate_name = self.aggregate_config.get("name", "overall")
            scores[aggregate_name] = aggregate_score

        return scores

    @staticmethod
    def judge_system_status(result: Any) -> int:
        """
        支持三种输入：
        - bool: True 表示超阈值
        - dict: { "exceeded": bool } 或 { "peak_value": float, "threshold": float }
        - 其他：统一视为未超阈值
        """
        if isinstance(result, bool):
            return int(result)
        if isinstance(result, Mapping):
            peak_value = result.get("peak_value")
            threshold = result.get("threshold")
            i = 0
            for i_threshold in threshold:
                if peak_value < i_threshold:
                    return i
                i += 1
            return i
        else:
            return 0

    def _get_range(self, channel_name: str, system_status: int) -> Tuple[float, float]:
        key = ["sleep_range", "normal_range", "abnormal_range"][system_status]
        channel_config = self.channel_ranges.get(channel_name, {})
        range_pair = channel_config.get(key) or self.default_ranges.get(key)
        if not range_pair or len(range_pair) != 2:
            raise ValueError(f"未找到通道 {channel_name} 对应的 {key} 配置")

        low, high = min(range_pair), max(range_pair)
        return float(low), float(high)

    def _aggregate_scores(self, scores: Mapping[str, float]) -> Optional[float]:
        if not scores or not self.aggregate_config:
            return None

        channels = self.aggregate_config.get("channels") or list(scores.keys())
        values: List[float] = []
        for name in channels:
            if name not in scores:
                return None
            values.append(scores[name])

        method = str(self.aggregate_config.get("method", "average")).lower()
        if method == "sum":
            aggregate_value = sum(values)
        elif method == "weighted":
            weights = self.aggregate_config.get("weights") or []
            if len(weights) != len(channels):
                return None
            total = float(sum(weights))
            if total == 0:
                return None
            aggregate_value = sum(value * weight for value, weight in zip(values, weights)) / total
        else:
            aggregate_value = sum(values) / len(values)

        return self._round_score(aggregate_value)

    def _round_score(self, score: float) -> float:
        return round(score, self.precision) if self.precision >= 0 else score

    def _load_config(self) -> Dict[str, Any]:
        config = load_config(str(self.config_path), module_name=self.module_name)
        if not config:
            raise ValueError(f"配置文件 {self.config_path} 中缺少模块 {self.module_name}")
        return config

    @staticmethod
    def _resolve_config_path(config_path: Optional[str]) -> Path:
        if config_path:
            return Path(config_path)
        if config_path:
            return Path(config_path)
        return Path(HEALTH_SCORE_CONFIG_JSON)
