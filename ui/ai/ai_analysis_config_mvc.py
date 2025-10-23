import os
import sys
import json
from dataclasses import dataclass
from typing import List, Optional, Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QWidget,
)


# ========================= Model ========================= #


@dataclass
class ModelConfig:
    model_name: str
    time: Optional[float] = None
    sample_rate: Optional[int] = None
    dimension: Optional[int] = None
    path: Optional[str] = None


class AIModelStore:
    """
    模型数据管理（Model 层）
    - 负责加载模型数据
    - 提供筛选接口，支持扩展筛选条件（开闭原则）
    """

    def __init__(self, models: Optional[List[ModelConfig]] = None):
        # 仅使用 JSON 数据源；若未提供则为空
        self._models: List[ModelConfig] = models if models is not None else []

    @staticmethod
    def _try_load_from_json(json_path: str) -> Optional[List[ModelConfig]]:
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        # 支持两种格式：
        # 1) 顶层即为列表
        # 2) { "models": [ ... ] }
        raw_list = None
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict) and isinstance(data.get("models"), list):
            raw_list = data.get("models")
        else:
            return None

        parsed: List[ModelConfig] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            # A) 原目标结构：model_name, time, sample_rate, dimension（兼容保留）
            if {"model_name", "time", "sample_rate", "dimension"}.issubset(item.keys()):
                try:
                    parsed.append(
                        ModelConfig(
                            model_name=str(item["model_name"]),
                            time=float(item["time"]),
                            sample_rate=int(item["sample_rate"]),
                            dimension=int(item["dimension"]),
                            path=str(item.get("path")) if item.get("path") is not None else None,
                        )
                    )
                except Exception:
                    continue
                continue

            # B) 当前数据源结构：name, input_dim (例如 "176400 x 1"), path
            if {"name", "input_dim"}.issubset(item.keys()):
                try:
                    # 提取样本点数：取 'x' 左侧的数字部分
                    first_token = str(item["input_dim"]).split("x")[0].strip()
                    second_token = str(item["input_dim"]).split("x")[1].strip()
                    # 去除非数字字符（如空格）
                    digits_first = "".join(ch for ch in first_token if ch.isdigit())
                    digits_second = "".join(ch for ch in second_token if ch.isdigit())
                    samples = int(digits_first) * int(digits_second)
                    parsed.append(
                        ModelConfig(
                            model_name=str(item["name"]),
                            dimension=samples,
                            path=str(item.get("path")) if item.get("path") is not None else None,
                        )
                    )
                except Exception:
                    continue
                continue

            # 其他结构忽略
        return parsed if parsed else None

    @classmethod
    def from_json_or_default(cls, json_path: str) -> "AIModelStore":
        # 仅从 JSON 加载；加载失败返回空仓库
        loaded = cls._try_load_from_json(json_path)
        return cls(loaded) if loaded else cls([])

    def get_all(self) -> List[ModelConfig]:
        return list(self._models)

    def filter_models(
        self,
        current_time: float,
        current_sample_rate: int,
        tolerance_ratio: float = 0.05,
        extra_predicates: Optional[List[Callable[[ModelConfig], bool]]] = None,
    ) -> List[ModelConfig]:
        """
        根据 abs(model.time * model.sample_rate - 当前时间 * 当前采样率) < 5%*(当前时间*当前采样率) 进行筛选。
        可通过 extra_predicates 传入更多条件函数以扩展筛选（开闭原则）。
        """
        target = float(current_time) * float(current_sample_rate)
        tolerance = abs(tolerance_ratio * target)

        results: List[ModelConfig] = []
        for m in self._models:
            # 优先使用 dimension（样本点数）
            if m.dimension is not None and m.dimension > 0:
                product = float(m.dimension)
            else:
                if m.time is None or m.sample_rate is None:
                    continue
                product = float(m.time) * float(m.sample_rate)
            if abs(product - target) < tolerance:
                results.append(m)

        if extra_predicates:
            for predicate in extra_predicates:
                results = [m for m in results if predicate(m)]

        return results


# ========================= View ========================= #


class AIConfigView(QDialog):
    """
    视图层：定义 PyQt 界面和基本的视图更新方法
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI 分析参数配置")
        self.setModal(True)

        self.sample_rates = [44100, 48000]

        # Widgets
        self.checkbox_use_ai = QCheckBox("启用 AI 分析")

        self.spin_time = QDoubleSpinBox()
        self.spin_time.setRange(2.0, 20.0)
        self.spin_time.setSingleStep(0.1)
        self.spin_time.setDecimals(1)
        self.spin_time.setValue(4.0)
        self.spin_time.setSuffix("s")

        self.combo_sample_rate = QComboBox()
        for sr in self.sample_rates:
            self.combo_sample_rate.addItem(str(sr), sr)
        self.combo_sample_rate.setCurrentIndex(0 if len(self.sample_rates) > 1 else 0)  # 默认 44100

        self.combo_model = QComboBox()

        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(2.0, 20.0)
        self.spin_interval.setSingleStep(0.1)
        self.spin_interval.setDecimals(1)
        self.spin_interval.setValue(2.0)
        self.spin_interval.setSuffix("s")

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("确认")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")

        # Layout
        form = QFormLayout()
        form.addRow(self.checkbox_use_ai)
        form.addRow(QLabel("时间设置"), self.spin_time)
        form.addRow(QLabel("采 样 率"), self.combo_sample_rate)
        form.addRow(QLabel("模型选择"), self.combo_model)
        form.addRow(QLabel("分析间隔"), self.spin_interval)

        # 左下角“模型管理”按钮
        self.btn_manage_models = QPushButton("模型管理")
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn_manage_models)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.button_box)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addLayout(bottom_layout)
        self.setLayout(root)

        # 默认禁用其余控件（勾选后启用）
        self.set_controls_enabled(False)
        # 结果缓存
        self._result_data: Optional[dict] = None

    # -------- View helper methods -------- #
    def set_controls_enabled(self, enabled: bool) -> None:
        self.spin_time.setEnabled(enabled)
        self.combo_sample_rate.setEnabled(enabled)
        self.combo_model.setEnabled(enabled)
        self.spin_interval.setEnabled(enabled)
        # 模型管理与启用 AI 无直接耦合，允许始终可点击；如需禁用可改为 self.btn_manage_models.setEnabled(enabled)

    def get_time_value(self) -> float:
        return float(self.spin_time.value())

    def get_sample_rate_value(self) -> int:
        # 通过 userData 取 int
        data = self.combo_sample_rate.currentData()
        return int(data) if data is not None else int(self.combo_sample_rate.currentText())

    def set_model_options(self, model_names: List[str]) -> bool:
        self.combo_model.blockSignals(True)
        self.combo_model.clear()
        if not model_names:
            self.combo_model.addItem("无可用模型")
            self.combo_model.blockSignals(False)
            return False
        else:
            for name in model_names:
                self.combo_model.addItem(name)
        self.combo_model.blockSignals(False)
        return True

    def get_selected_model_name(self) -> str:
        return self.combo_model.currentText()

    def get_analysis_interval(self) -> float:
        return float(self.spin_interval.value())

    def set_result_data(self, data: dict) -> None:
        self._result_data = data

    def get_result_data(self) -> Optional[dict]:
        return self._result_data


# ========================= Controller ========================= #


class AIConfigController:
    """
    控制器：绑定交互、调用 Model 进行筛选并更新 View
    """

    def __init__(self, model_store: AIModelStore, view: AIConfigView, manage_dialog_factory: Optional[Callable[[AIModelStore, QWidget], QDialog]] = None) -> None:
        self.model_store = model_store
        self.view = view
        # 满足开闭原则：通过工厂函数注入模型管理对话框的构造器
        self.manage_dialog_factory = manage_dialog_factory

        # 连接信号
        self.view.checkbox_use_ai.toggled.connect(self.on_toggle_use_ai)
        self.view.spin_time.valueChanged.connect(self.refresh_model_list)
        self.view.combo_sample_rate.currentTextChanged.connect(self.refresh_model_list)
        self.view.button_box.accepted.connect(self.on_confirm)
        self.view.button_box.rejected.connect(self.on_cancel)
        self.view.btn_manage_models.clicked.connect(self.on_manage_models)

        # 初始化模型列表（即使控件禁用也先计算一次，便于状态切换时立即可用）
        self.refresh_model_list()

    # -------- Slots -------- #
    def on_toggle_use_ai(self, checked: bool) -> None:
        self.view.set_controls_enabled(checked)
        # 每次开启时刷新一次，确保模型列表与当前参数一致
        if checked:
            self.refresh_model_list()
        else:
            # 未启用时，模型下拉同步禁用
            self.view.combo_model.setEnabled(False)

    def refresh_model_list(self) -> None:
        time_value = self.view.get_time_value()
        sample_rate_value = self.view.get_sample_rate_value()
        filtered = self.model_store.filter_models(time_value, sample_rate_value, tolerance_ratio=0.05)
        has_models = self.view.set_model_options([m.model_name for m in filtered])
        # 只有在启用 AI 且有可用模型时允许选择
        self.view.combo_model.setEnabled(self.view.checkbox_use_ai.isChecked() and has_models)

    def on_confirm(self) -> None:
        result = {
            "use_ai": bool(self.view.checkbox_use_ai.isChecked()),
            "time": float(self.view.get_time_value()),
            "sample_rate": int(self.view.get_sample_rate_value()),
            "model_name": str(self.view.get_selected_model_name()),
            "analysis_interval": float(self.view.get_analysis_interval()),
        }
        self.view.set_result_data(result)
        self.view.accept()

    def on_cancel(self) -> None:
        self.view.reject()

    def on_manage_models(self) -> None:
        if self.manage_dialog_factory is None:
            # 默认简单实现：只读查看当前可用模型
            dlg = QDialog(self.view)
            dlg.setWindowTitle("模型管理")
            layout = QVBoxLayout()
            lst = QListWidget()
            for m in self.model_store.get_all():
                dim_txt = f"dim={m.dimension}" if m.dimension is not None else "dim=?"
                lst.addItem(f"{m.model_name}  {dim_txt}")
            layout.addWidget(lst)
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dlg.accept)
            layout.addWidget(close_btn)
            dlg.setLayout(layout)
            dlg.resize(360, 300)
            dlg.exec_()
            return

        # 使用注入的工厂创建可扩展对话框
        dlg = self.manage_dialog_factory(self.model_store, self.view)
        if isinstance(dlg, QDialog):
            dlg.exec_()


# ========================= App (main) ========================= #


def main() -> None:
    app = QApplication(sys.argv)

    # 模型数据来源：优先尝试当前目录下的 models.json（要求字段匹配），否则使用内置列表
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "../ui_config/models.json")
    print(json_path)
    model_store = AIModelStore.from_json_or_default(json_path)

    view = AIConfigView()
    controller = AIConfigController(model_store, view)  # noqa: F841 (保持引用)

    view.resize(420, 240)
    if view.exec_() == view.Accepted:
        result = view.get_result_data()  # 字典结果
        print(result)

    # 应用以对话框为主，关闭对话框后退出
    sys.exit(0)


if __name__ == "__main__":
    main()
