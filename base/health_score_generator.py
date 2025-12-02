import random
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, List

from base.load_config import load_config
from consts.running_consts import HEALTH_SCORE_CONFIG_JSON


class MotorState:
    """电机状态常量，与 knock_detection.MotorState 对应"""
    SLEEPING = 0   # 停机状态
    RUNNING = 1    # 正常运行
    KNOCKED = 2    # 被敲击


class HealthScoreGenerator:
    """
    根据电机状态生成健康评分：
    - 停机状态 (SLEEPING) => 使用 sleep_range 随机取值
    - 正常运行 (RUNNING) => 使用 normal_range 随机取值
    - 被敲击 (KNOCKED) => 使用 abnormal_range 随机取值
    - 无检测结果 => 使用默认的 normal_range 生成兜底健康分
    
    检测结果格式:
    {
        "good_motor": {
            "motor_state": 0/1/2,  # 0=停机, 1=运行, 2=敲击
            "is_running": bool,
            "is_knocked": bool,
            "energy_level": float,
            "max_zscore": float,
            ...
        }
    }
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
            peak_results: 检测结果，结构示例：
                {
                    "good_motor": {
                        "motor_state": 1,
                        "is_running": True,
                        "is_knocked": False,
                        "energy_level": 0.001,
                        "max_zscore": 2.5
                    },
                    "bad_motor": {
                        "motor_state": 2,
                        "is_running": True,
                        "is_knocked": True,
                        "energy_level": 0.002,
                        "max_zscore": 8.5
                    }
                }
                可为空；空时将按 channel_names 或配置里的 channels 兜底。
            channel_names: 在没有检测结果时，用于生成评分的通道列表。

        Returns:
            {"good_motor": 93.4, "bad_motor": 33.1, "overall": 63.2}
        """
        peak_results = peak_results or {}

        if peak_results:
            items = peak_results.items()
        else:
            names = list(channel_names or self.channel_ranges.keys())
            if not names:
                raise ValueError("没有峰值结果且配置中缺少 channel 列表，无法生成健康分")
            items = [(name, {}) for name in names]

        scores: Dict[str, float] = {}
        for channel_name, result in items:
            motor_state = self.judge_motor_state(result)
            min_val, max_val = self._get_range(channel_name, motor_state)
            score = self._rng.uniform(min_val, max_val)
            scores[channel_name] = self._round_score(score)

        aggregate_score = self._aggregate_scores(scores)
        if aggregate_score is not None:
            aggregate_name = self.aggregate_config.get("name", "overall")
            scores[aggregate_name] = aggregate_score

        return scores

    @staticmethod
    def judge_motor_state(result: Any) -> int:
        """
        判断电机状态：
        - 直接使用 motor_state 字段（如果存在）
        - 或者根据 is_knocked 和 is_running 推断
        - 兼容旧格式（bool 或 exceeded 字段）
        
        返回:
            0 = SLEEPING（停机）
            1 = RUNNING（正常运行）
            2 = KNOCKED（被敲击）
        """
        if isinstance(result, Mapping):
            # 优先使用 motor_state 字段
            if "motor_state" in result:
                state = result["motor_state"]
                # 处理 IntEnum 类型
                if hasattr(state, 'value'):
                    return int(state.value)
                return int(state)
            
            # 根据 is_knocked 和 is_running 推断
            is_knocked = result.get("is_knocked", False)
            is_running = result.get("is_running", True)
            
            if is_knocked:
                return MotorState.KNOCKED
            elif not is_running:
                return MotorState.SLEEPING
            else:
                return MotorState.RUNNING
        
        elif isinstance(result, bool):
            # 旧格式兼容：True 表示异常（敲击）
            return MotorState.KNOCKED if result else MotorState.RUNNING
        
        else:
            # 默认返回正常运行状态
            return MotorState.RUNNING

    def _get_range(self, channel_name: str, motor_state: int) -> Tuple[float, float]:
        """
        根据电机状态获取对应的分数范围
        
        Args:
            channel_name: 通道名称
            motor_state: 0=停机, 1=运行, 2=敲击
        """
        state_to_key = {
            MotorState.SLEEPING: "sleep_range",
            MotorState.RUNNING: "normal_range",
            MotorState.KNOCKED: "abnormal_range",
        }
        key = state_to_key.get(motor_state, "normal_range")
        
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
        return Path(HEALTH_SCORE_CONFIG_JSON)
