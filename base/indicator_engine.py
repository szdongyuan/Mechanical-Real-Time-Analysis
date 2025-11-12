from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PredictionItem:
    result: str  # "OK" / "NG"
    score: Optional[float] = None


class RedLightController:
    """
    仅负责红灯叠加时长控制：每次 NG 事件叠加 0.2s；通过 tick() 衰减。
    """
    def __init__(self, add_seconds: float = 0.2):
        self.add_seconds = float(add_seconds)
        self.remaining_seconds: float = 0.0

    def on_ng(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds += self.add_seconds
        else:
            self.remaining_seconds = self.add_seconds

    def tick(self, step_seconds: float):
        if self.remaining_seconds <= 0:
            return
        self.remaining_seconds = max(0.0, self.remaining_seconds - max(0.0, step_seconds))

    def is_on(self) -> bool:
        return self.remaining_seconds > 0.0


class ColorIndicator:
    """
    每通道控制器：当前需求仅红灯有时长叠加；绿灯由上层根据“是否存在 NG”决定显示。
    后续可在不修改本类的前提下，组合更多颜色控制器（符合 OCP）。
    """
    def __init__(self, red_add_seconds: float = 0.2):
        self.red = RedLightController(add_seconds=red_add_seconds)
        self._last_result: str = "OK"

    def on_event(self, result: str):
        r = str(result).upper()
        self._last_result = r
        if r == "NG":
            self.red.on_ng()

    def tick(self, step_seconds: float):
        self.red.tick(step_seconds)

    def is_red_on(self) -> bool:
        return self.red.is_on()

    def current_color(self) -> str:
        # 只要红灯未亮，绿灯恒亮
        return "RED" if self.red.is_on() else "GREEN"


class IndicatorEngine:
    """
    多通道引擎：
    - process_predictions: 处理一批结果，逐通道触发事件
    - tick: 时间推进，衰减红灯
    - render_snapshot: 返回当前每通道的红灯状态
    """
    def __init__(self, red_add_seconds: float = 0.2):
        self._colorindicator: ColorIndicator = ColorIndicator(red_add_seconds=float(red_add_seconds))
        self._red_add_seconds = float(red_add_seconds)

    def process_predictions(self, items: List[PredictionItem]):
        for item in items:
            self._colorindicator.on_event(item.result)

    def tick(self, step_seconds: float):
        self._colorindicator.tick(step_seconds)

    def has_any_red_on(self) -> bool:
        return self._colorindicator.is_red_on()

    def render_snapshot(self) -> Dict[str, float]:
        return {
            "red_remaining": self._colorindicator.red.remaining_seconds,
            "color": self._colorindicator.current_color(),
        }


def parse_raw_input(raw: List[dict]) -> List[PredictionItem]:
    items: List[PredictionItem] = []
    for entry in raw:
        res_list = entry.get("result") or []
        if not res_list:
            continue
        first = res_list[0]
        result_str = str(first[1]).upper() if len(first) > 1 else "OK"
        score: Optional[float] = None
        if len(first) > 2:
            try:
                score = float(first[2])
            except Exception:
                score = None
        items.append(PredictionItem(result=result_str, score=score))
    return items


