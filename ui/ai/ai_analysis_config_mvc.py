import os
import json
from dataclasses import dataclass
from typing import List, Optional, Callable

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from ui.ai.register_ai_model import ModelManagerApp
from consts.running_consts import DEFAULT_DIR


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
    ) -> List[ModelConfig]:
        """
        严格比较维度：仅当 model.dimension 等于 current_time * current_sample_rate 时返回。
        如果模型缺少 dimension，将被忽略。
        """
        target = int(round(float(current_time) * float(current_sample_rate)))

        results: List[ModelConfig] = []
        for m in self._models:
            if m.dimension is None:
                continue
            try:
                if int(m.dimension) == target:
                    results.append(m)
            except Exception:
                continue

        return results


# ========================= View ========================= #


class AIConfigView(QDialog):
    """
    视图层：定义 PyQt 界面和基本的视图更新方法
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        forced_sample_rate: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI 分析参数配置")
        self.setWindowIcon(QIcon(DEFAULT_DIR + "ui/ui_pic/sys_ico/icon.ico"))
        self.setModal(True)

        self._forced_sample_rate: Optional[int] = forced_sample_rate

        # Widgets
        self.checkbox_use_ai = QCheckBox("启用 AI 分析")

        self.spin_time = QDoubleSpinBox()
        self.spin_time.setRange(2.0, 20.0)
        self.spin_time.setSingleStep(0.1)
        self.spin_time.setDecimals(1)
        self.spin_time.setValue(4.0)
        self.spin_time.setSuffix("s")

        # 采样率仅来源于外部传入，使用被禁用的单行输入框展示
        self.sample_rate_input = QLineEdit(
            str(self._forced_sample_rate) if self._forced_sample_rate is not None else "未提供"
        )
        self.sample_rate_input.setEnabled(False)

        self.combo_model = QComboBox()

        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(2.0, 20.0)
        self.spin_interval.setSingleStep(0.1)
        self.spin_interval.setDecimals(1)
        self.spin_interval.setValue(3.5)
        self.spin_interval.setSuffix("s")

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("确认")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")

        # Layout
        form = QFormLayout()
        form.addRow(self.checkbox_use_ai)
        form.addRow(QLabel("时间设置"), self.spin_time)
        form.addRow(QLabel("采 样 率"), self.sample_rate_input)
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
        self.combo_model.setEnabled(enabled)
        self.spin_interval.setEnabled(enabled)
        # 模型管理与启用 AI 无直接耦合，允许始终可点击；如需禁用可改为 self.btn_manage_models.setEnabled(enabled)

    def get_time_value(self) -> float:
        return round(float(self.spin_time.value()), 1)

    def get_sample_rate_value(self) -> int:
        if self._forced_sample_rate is None:
            raise ValueError("未提供采样率：该对话框需要外部采样率作为唯一来源")
        return int(self._forced_sample_rate)

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
        return round(float(self.spin_interval.value()), 1)

    def set_result_data(self, data: dict) -> None:
        self._result_data = data

    def get_result_data(self) -> Optional[dict]:
        return self._result_data


# ========================= Controller ========================= #


class AIConfigController:
    """
    控制器：绑定交互、调用 Model 进行筛选并更新 View
    """

    def __init__(
        self,
        model_store: AIModelStore,
        view: AIConfigView,
        manage_dialog_factory: Optional[Callable[[AIModelStore, QWidget], QDialog]] = None,
        models_json_path: Optional[str] = None,
        initial_config: Optional[dict] = None,
    ) -> None:
        self.model_store = model_store
        self.view = view
        # 满足开闭原则：通过工厂函数注入模型管理对话框的构造器
        self.manage_dialog_factory = manage_dialog_factory
        # 外部注入的模型 JSON 路径（若未提供则使用默认相对路径）

        self.models_json_path = models_json_path

        # 连接信号
        self.view.checkbox_use_ai.toggled.connect(self.on_toggle_use_ai)
        self.view.spin_time.valueChanged.connect(self.refresh_model_list)
        self.view.button_box.accepted.connect(self.on_confirm)
        self.view.button_box.rejected.connect(self.on_cancel)
        self.view.btn_manage_models.clicked.connect(self.on_manage_models)

        # 初始化模型列表（即使控件禁用也先计算一次，便于状态切换时立即可用）
        self.refresh_model_list()
        # 根据外部传入配置初始化界面
        self._apply_initial_config(initial_config)

    def _apply_initial_config(self, cfg: Optional[dict]) -> None:
        if not isinstance(cfg, dict) or not cfg:
            return
        try:
            # 暂时屏蔽信号，避免多次刷新
            self.view.checkbox_use_ai.blockSignals(True)
            self.view.spin_time.blockSignals(True)
            self.view.spin_interval.blockSignals(True)
            self.view.combo_model.blockSignals(True)

            # 应用时间、开关
            if "time" in cfg and cfg["time"] is not None:
                try:
                    self.view.spin_time.setValue(float(cfg["time"]))
                except Exception:
                    pass
            use_ai_checked = bool(cfg.get("use_ai", False))
            self.view.checkbox_use_ai.setChecked(use_ai_checked)

            # 刷新模型列表以匹配新的时间/采样率
            self.refresh_model_list()

            # 选择模型名称，不存在则选第一项
            desired_name = str(cfg.get("model_name", ""))
            idx_to_select = -1
            if desired_name:
                for i in range(self.view.combo_model.count()):
                    if self.view.combo_model.itemText(i) == desired_name:
                        idx_to_select = i
                        break
            if idx_to_select < 0 and self.view.combo_model.count() > 0:
                idx_to_select = 0
            if idx_to_select >= 0:
                self.view.combo_model.setCurrentIndex(idx_to_select)

            # 分析间隔
            if "analysis_interval" in cfg and cfg["analysis_interval"] is not None:
                try:
                    self.view.spin_interval.setValue(float(cfg["analysis_interval"]))
                except Exception:
                    pass

            # 控件可用状态与确认按钮
            self.view.set_controls_enabled(use_ai_checked)
            self.refresh_model_list()
        finally:
            self.view.checkbox_use_ai.blockSignals(False)
            self.view.spin_time.blockSignals(False)
            self.view.spin_interval.blockSignals(False)
            self.view.combo_model.blockSignals(False)

    # -------- Slots -------- #
    def on_toggle_use_ai(self, checked: bool) -> None:
        self.view.set_controls_enabled(checked)
        # 每次开启时刷新一次，确保模型列表与当前参数一致
        if checked:
            self.refresh_model_list()
        else:
            # 未启用时，模型下拉同步禁用
            self.view.combo_model.setEnabled(False)
            # 未启用 AI 时允许确认
            self.view.button_box.button(QDialogButtonBox.Ok).setEnabled(True)

    def refresh_model_list(self) -> None:
        time_value = self.view.get_time_value()
        sample_rate_value = self.view.get_sample_rate_value()
        filtered = self.model_store.filter_models(time_value, sample_rate_value)
        has_models = self.view.set_model_options([m.model_name for m in filtered])
        # 只有在启用 AI 且有可用模型时允许选择
        self.view.combo_model.setEnabled(self.view.checkbox_use_ai.isChecked() and has_models)
        # 根据是否启用 AI 以及是否有匹配模型控制“确认”按钮
        ok_btn = self.view.button_box.button(QDialogButtonBox.Ok)
        if self.view.checkbox_use_ai.isChecked():
            ok_btn.setEnabled(has_models)
        else:
            ok_btn.setEnabled(True)

    def on_confirm(self) -> None:
        # 启用 AI 但无匹配模型时阻止退出
        if self.view.checkbox_use_ai.isChecked():
            time_value = self.view.get_time_value()
            sample_rate_value = self.view.get_sample_rate_value()
            filtered = self.model_store.filter_models(time_value, sample_rate_value)
            if not filtered:
                self.view.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
                return
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
            # 使用注册模型管理器作为管理界面（路径由外部注入）
            manager = ModelManagerApp(self.models_json_path)
            code, _ = manager.run()
            if code == QDialog.Accepted:
                # 重新加载模型数据并刷新下拉框
                self.model_store = AIModelStore.from_json_or_default(self.models_json_path)
                self.refresh_model_list()
            return

        # 使用注入的工厂创建可扩展对话框
        dlg = self.manage_dialog_factory(self.model_store, self.view)
        if isinstance(dlg, QDialog):
            dlg.exec_()
