import json
import os
from typing import Any, Dict, Optional, Tuple, List

from PyQt5.QtCore import QRegularExpression, Qt
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from base.log_manager import LogManager
from consts.db_consts import JSON_DIR_PATH
from consts.running_consts import DEFAULT_DIR
from ui.ai.ai_analysis_config_mvc import AIModelStore


# ---------------- Models ---------------- #


class AnalysisToggleModel:
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self.logger = LogManager.set_log_handler("core")
        self._config_path = os.path.normpath(os.path.join(DEFAULT_DIR, "ui/ui_config/model_analysis.json"))
        self.use_ai: bool = False
        self._all_fields: Dict[str, Any] = {}
        self._load()
        if isinstance(initial, dict):
            try:
                if "use_ai" in initial:
                    self.use_ai = bool(initial["use_ai"])
                for k in ("time", "sample_rate", "model_name", "analysis_interval"):
                    if k in initial:
                        self._all_fields[k] = initial[k]
            except Exception as e:
                self.logger.error(f"Failed to load analysis config: {e}")

    def _load(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._all_fields = json.load(f) or {}
                self.use_ai = bool(self._all_fields.get("use_ai", self.use_ai))
        except Exception as e:
            self.logger.error(f"Failed to load analysis config: {e}")

    def save(self, use_ai: bool, time_value: float, sample_rate: int, model_name: str, analysis_interval: float) -> None:
        data = dict(self._all_fields)
        data["use_ai"] = bool(use_ai)
        data["time"] = float(time_value)
        data["sample_rate"] = int(sample_rate)
        data["model_name"] = str(model_name)
        data["analysis_interval"] = float(analysis_interval)
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._all_fields = data
        self.use_ai = data["use_ai"]


class InforLimitionModel:
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._config_path = os.path.join(JSON_DIR_PATH, "infor_limition.json")
        self.logger = LogManager.set_log_handler("core")
        self.duration_min: int = 10
        self.max_count: int = 100
        self.enable_limit: bool = False
        self._load()
        if isinstance(initial, dict):
            try:
                if "duration_min" in initial:
                    self.duration_min = int(initial["duration_min"])
                if "max_count" in initial:
                    self.max_count = int(initial["max_count"])
                if "enable_limit" in initial:
                    self.enable_limit = bool(initial["enable_limit"])
            except Exception as e:
                self.logger.error(f"Failed to load infor limition config: {e}")

    def _load(self) -> None:
        try:
            os.makedirs(JSON_DIR_PATH, exist_ok=True)
            if not os.path.exists(self._config_path):
                return
            with open(self._config_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            self.duration_min = int(data.get("duration_min", self.duration_min))
            self.max_count = int(data.get("max_count", self.max_count))
            self.enable_limit = bool(data.get("enable_limit", self.enable_limit))
        except Exception as e:
            self.logger.error(f"Failed to load infor limition config: {e}")

    def save(self, duration_min: int, max_count: int, enable_limit: bool) -> None:
        data = {
            "duration_min": int(duration_min),
            "max_count": int(max_count),
            "enable_limit": bool(enable_limit),
        }
        os.makedirs(JSON_DIR_PATH, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.duration_min = data["duration_min"]
        self.max_count = data["max_count"]
        self.enable_limit = data["enable_limit"]


class TcpConfigModel:
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._config_path = os.path.normpath(os.path.join(DEFAULT_DIR, "ui/ui_config/tcp_config.json"))
        self.logger = LogManager.set_log_handler("core")
        self.enable_tcp: bool = False
        self.ip: str = "127.0.0.1"
        self.port: int = 50000
        self._load()
        if isinstance(initial, dict):
            try:
                if "enable_tcp" in initial:
                    self.enable_tcp = bool(initial["enable_tcp"])
                if "ip" in initial:
                    self.ip = str(initial["ip"]) or "127.0.0.1"
                if "port" in initial:
                    self.port = int(initial["port"])
            except Exception as e:
                self.logger.error(f"Failed to load tcp config: {e}")

    def _load(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            if not os.path.exists(self._config_path):
                return
            with open(self._config_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            self.enable_tcp = bool(data.get("enable_tcp", self.enable_tcp))
            self.ip = str(data.get("ip", self.ip)) or "127.0.0.1"
            try:
                self.port = int(data.get("port", self.port))
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Failed to load tcp config: {e}")

    def save(self, enable_tcp: bool, ip: str, port: int) -> None:
        data = {
            "enable_tcp": bool(enable_tcp),
            "ip": str(ip).strip() or "127.0.0.1",
            "port": int(port),
        }
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.enable_tcp = data["enable_tcp"]
        self.ip = data["ip"]
        self.port = data["port"]


# ---------------- View ---------------- #


class AnalysisConfigView(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, forced_sample_rate: Optional[int] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("分析与通知/TCP 配置")
        self.setModal(True)

        # AI
        self.checkbox_use_ai = QCheckBox("启用 AI 分析")
        self.spin_time = QDoubleSpinBox()
        self.spin_time.setRange(2.0, 20.0)
        self.spin_time.setSingleStep(0.1)
        self.spin_time.setDecimals(1)
        self.spin_time.setValue(4.0)
        self.spin_time.setSuffix("s")
        self.sample_rate_input = QLineEdit(str(forced_sample_rate) if forced_sample_rate is not None else "未提供")
        self.sample_rate_input.setEnabled(False)
        self.combo_model = QComboBox()
        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(2.0, 20.0)
        self.spin_interval.setSingleStep(0.1)
        self.spin_interval.setDecimals(1)
        self.spin_interval.setValue(3.5)
        self.spin_interval.setSuffix("s")

        # 通知限制
        self.checkbox_enable_limit = QCheckBox("启用通知限制")
        self.spin_duration_min = QSpinBox()
        self.spin_duration_min.setRange(1, 1_000_000)
        self.spin_duration_min.setSuffix(" min")
        self.spin_max_count = QSpinBox()
        self.spin_max_count.setRange(1, 100_000_000)

        # TCP
        self.checkbox_enable_tcp = QCheckBox("启用 TCP")
        self.line_ip = QLineEdit()
        self.line_ip.setPlaceholderText("127.0.0.1")
        ip_regex = QRegularExpression(
            r"^(25[0-5]|2[0-4]\d|1?\d?\d)\."
            r"(25[0-5]|2[0-4]\d|1?\d?\d)\."
            r"(25[0-5]|2[0-4]\d|1?\d?\d)\."
            r"(25[0-5]|2[0-4]\d|1?\d?\d)$"
        )
        self.line_ip.setValidator(QRegularExpressionValidator(ip_regex, self))
        self.spin_port = QSpinBox()
        self.spin_port.setRange(49152, 65535)
        self.spin_port.setValue(50000)

        # 按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("确认")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")

        # 布局
        form = QFormLayout()
        form.setSpacing(10)
        if hasattr(form, "setHorizontalSpacing"):
            form.setHorizontalSpacing(30)
        form.addRow(self.checkbox_use_ai)
        form.addRow(QLabel("时间设置"), self.spin_time)
        form.addRow(QLabel("采 样 率"), self.sample_rate_input)
        form.addRow(QLabel("模型选择"), self.combo_model)
        form.addRow(QLabel("分析间隔"), self.spin_interval)
        # 通知限制：先放启用开关，再放输入项
        form.addRow(self.checkbox_enable_limit)
        form.addRow(QLabel("统计时长"), self.spin_duration_min)
        form.addRow(QLabel("最大数量"), self.spin_max_count)
        # TCP：先放启用开关，再放输入项
        form.addRow(self.checkbox_enable_tcp)
        form.addRow(QLabel("IP 地 址"), self.line_ip)
        form.addRow(QLabel("端 口 号"), self.spin_port)

        self.btn_manage_models = QPushButton("模型管理")
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn_manage_models)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.button_box)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addStretch(1)
        root.addLayout(bottom_layout)
        self.setLayout(root)

    # 一组启用/禁用方法，供控制器调用
    def set_infor_inputs_enabled(self, enabled: bool) -> None:
        self.spin_duration_min.setEnabled(bool(enabled))
        self.spin_max_count.setEnabled(bool(enabled))

    def set_tcp_inputs_enabled(self, enabled: bool) -> None:
        self.line_ip.setEnabled(bool(enabled))
        self.spin_port.setEnabled(bool(enabled))

    def set_ai_controls_enabled(self, enabled: bool) -> None:
        self.spin_time.setEnabled(bool(enabled))
        self.combo_model.setEnabled(bool(enabled))
        self.spin_interval.setEnabled(bool(enabled))

    def get_time_value(self) -> float:
        return round(float(self.spin_time.value()), 1)

    def get_sample_rate_value(self) -> Optional[int]:
        try:
            return int(self.sample_rate_input.text()) if self.sample_rate_input.text().strip().isdigit() else None
        except Exception:
            return None

    def set_model_options(self, model_names: List[str]) -> bool:
        self.combo_model.blockSignals(True)
        self.combo_model.clear()
        if not model_names:
            self.combo_model.addItem("无可用模型")
            self.combo_model.blockSignals(False)
            return False
        for name in model_names:
            self.combo_model.addItem(name)
        self.combo_model.blockSignals(False)
        return True

    def get_selected_model_name(self) -> str:
        return self.combo_model.currentText()

    def get_analysis_interval(self) -> float:
        return round(float(self.spin_interval.value()), 1)


# ---------------- Controller ---------------- #


class AnalysisConfigController:
    def __init__(
        self,
        analysis_model: AnalysisToggleModel,
        limit_model: InforLimitionModel,
        tcp_model: TcpConfigModel,
        view: AnalysisConfigView,
        models_json_path: Optional[str] = None,
        forced_sample_rate: Optional[int] = None,
    ) -> None:
        self.logger = LogManager.set_log_handler("core")
        self.analysis_model = analysis_model
        self.limit_model = limit_model
        self.tcp_model = tcp_model
        self.view = view
        self._result_values: Optional[Dict[str, Any]] = None
        self._models_json_path = models_json_path or os.path.normpath(os.path.join(DEFAULT_DIR, "ui/ui_config/models.json"))
        self._forced_sample_rate = forced_sample_rate
        self._model_store = AIModelStore.from_json_or_default(self._models_json_path)

        self._init_values()
        self._bind()
        self._apply_dependencies()
        self._refresh_model_list()

    def _init_values(self) -> None:
        # AI
        self.view.checkbox_use_ai.setChecked(bool(self.analysis_model.use_ai))
        try:
            if "time" in self.analysis_model._all_fields:
                self.view.spin_time.setValue(float(self.analysis_model._all_fields["time"]))
        except Exception as e:
            self.logger.error(f"Failed to init values: {e}")
        try:
            if "analysis_interval" in self.analysis_model._all_fields:
                self.view.spin_interval.setValue(float(self.analysis_model._all_fields["analysis_interval"]))
        except Exception as e:
            self.logger.error(f"Failed to init values: {e}")
        if self._forced_sample_rate is not None:
            self.view.sample_rate_input.setText(str(int(self._forced_sample_rate)))
        else:
            sr = self.analysis_model._all_fields.get("sample_rate")
            self.view.sample_rate_input.setText(str(int(sr)) if isinstance(sr, int) else self.view.sample_rate_input.text())
        self.view.set_ai_controls_enabled(bool(self.analysis_model.use_ai))
        # 通知限制
        self.view.checkbox_enable_limit.setChecked(bool(self.limit_model.enable_limit))
        self.view.spin_duration_min.setValue(int(self.limit_model.duration_min))
        self.view.spin_max_count.setValue(int(self.limit_model.max_count))
        # TCP
        self.view.checkbox_enable_tcp.setChecked(bool(self.tcp_model.enable_tcp))
        self.view.line_ip.setText(str(self.tcp_model.ip) or "127.0.0.1")
        try:
            self.view.spin_port.setValue(int(self.tcp_model.port))
        except Exception as e:
            self.view.spin_port.setValue(50000)

    def _bind(self) -> None:
        self.view.checkbox_use_ai.toggled.connect(self.on_toggle_use_ai)
        self.view.spin_time.valueChanged.connect(self._refresh_model_list)
        self.view.checkbox_enable_limit.toggled.connect(self.on_toggle_enable_limit)
        self.view.checkbox_enable_tcp.toggled.connect(self.on_toggle_enable_tcp)
        self.view.button_box.accepted.connect(self.on_confirm)
        self.view.button_box.rejected.connect(self.on_cancel)
        self.view.btn_manage_models.clicked.connect(self.on_manage_models)

    def _apply_dependencies(self) -> None:
        # 规则：
        # 1) 未勾选“启用 AI 分析”，则不能勾选“启用通知限制”
        # 2) 未勾选“启用通知限制”，则不能勾选“启用 TCP”
        use_ai = bool(self.view.checkbox_use_ai.isChecked())
        enable_limit = bool(self.view.checkbox_enable_limit.isChecked()) if use_ai else False
        enable_tcp = bool(self.view.checkbox_enable_tcp.isChecked()) if enable_limit else False

        # 自动纠正勾选状态链
        if not use_ai and self.view.checkbox_enable_limit.isChecked():
            self.view.checkbox_enable_limit.blockSignals(True)
            self.view.checkbox_enable_limit.setChecked(False)
            self.view.checkbox_enable_limit.blockSignals(False)
        if not enable_limit and self.view.checkbox_enable_tcp.isChecked():
            self.view.checkbox_enable_tcp.blockSignals(True)
            self.view.checkbox_enable_tcp.setChecked(False)
            self.view.checkbox_enable_tcp.blockSignals(False)

        # 控件可用性
        self.view.set_ai_controls_enabled(use_ai)
        self.view.checkbox_enable_limit.setEnabled(use_ai)
        self.view.set_infor_inputs_enabled(use_ai and bool(self.view.checkbox_enable_limit.isChecked()))

        self.view.checkbox_enable_tcp.setEnabled(use_ai and bool(self.view.checkbox_enable_limit.isChecked()))
        self.view.set_tcp_inputs_enabled(use_ai and bool(self.view.checkbox_enable_limit.isChecked()) and bool(self.view.checkbox_enable_tcp.isChecked()))
        self._update_ok_enabled()

    def on_toggle_use_ai(self, checked: bool) -> None:
        self._apply_dependencies()

    def on_toggle_enable_limit(self, checked: bool) -> None:
        # 若取消通知限制，同时取消 TCP
        if not checked and self.view.checkbox_enable_tcp.isChecked():
            self.view.checkbox_enable_tcp.blockSignals(True)
            self.view.checkbox_enable_tcp.setChecked(False)
            self.view.checkbox_enable_tcp.blockSignals(False)
        self._apply_dependencies()

    def on_toggle_enable_tcp(self, checked: bool) -> None:
        self._apply_dependencies()

    def _validate(self) -> Tuple[bool, str]:
        # 仅当启用 TCP 时进行校验
        if self.view.checkbox_enable_tcp.isChecked():
            ip = self.view.line_ip.text().strip()
            parts = ip.split(".")
            if len(parts) != 4:
                return False, "IP 地址格式不正确"
            try:
                for p in parts:
                    v = int(p)
                    if v < 0 or v > 255:
                        return False, "IP 地址每段应在 0-255 之间"
            except Exception:
                return False, "IP 地址格式不正确"
            port = int(self.view.spin_port.value())
            if port < 49152 or port > 65535:
                return False, "端口号应在 49152-65535 范围内"
        if self.view.checkbox_use_ai.isChecked():
            if self.view.combo_model.count() == 0 or self.view.combo_model.itemText(0) == "无可用模型":
                return False, "启用 AI 时需要可用的模型"
        return True, ""

    def on_confirm(self) -> None:
        ok, msg = self._validate()
        if not ok:
            QMessageBox.warning(self.view, "提示", msg)
            return
        # 保存到模型
        use_ai = bool(self.view.checkbox_use_ai.isChecked())
        time_value = float(self.view.get_time_value())
        sr_value = self._resolve_sample_rate()
        model_name = str(self.view.get_selected_model_name())
        interval_value = float(self.view.get_analysis_interval())
        enable_limit = bool(self.view.checkbox_enable_limit.isChecked())
        enable_tcp = bool(self.view.checkbox_enable_tcp.isChecked())

        self.analysis_model.save(
            use_ai=use_ai,
            time_value=time_value,
            sample_rate=sr_value,
            model_name=model_name,
            analysis_interval=interval_value,
        )
        self.limit_model.save(
            duration_min=int(self.view.spin_duration_min.value()),
            max_count=int(self.view.spin_max_count.value()),
            enable_limit=enable_limit,
        )
        self.tcp_model.save(
            enable_tcp=enable_tcp,
            ip=self.view.line_ip.text().strip() or "127.0.0.1",
            port=int(self.view.spin_port.value()),
        )

        self._result_values = {
            "ai_config": {
                "use_ai": self.analysis_model.use_ai,
                "time": float(self.analysis_model._all_fields.get("time", time_value)),
                "sample_rate": int(self.analysis_model._all_fields.get("sample_rate", sr_value)),
                "model_name": str(self.analysis_model._all_fields.get("model_name", model_name)),
                "analysis_interval": float(self.analysis_model._all_fields.get("analysis_interval", interval_value)),
            },
            "infor_limition": {
                "duration_min": self.limit_model.duration_min,
                "max_count": self.limit_model.max_count,
                "enable_limit": self.limit_model.enable_limit,
            },
            "tcp_config": {
                "enable_tcp": self.tcp_model.enable_tcp,
                "ip": self.tcp_model.ip,
                "port": self.tcp_model.port,
            },
        }
        self.view.accept()

    def on_cancel(self) -> None:
        self.view.reject()

    def get_result_values(self) -> Dict[str, Any]:
        return dict(self._result_values or {})

    def _resolve_sample_rate(self) -> int:
        if isinstance(self._forced_sample_rate, int) and self._forced_sample_rate > 0:
            return int(self._forced_sample_rate)
        sr_text = self.view.sample_rate_input.text().strip()
        try:
            return int(sr_text)
        except Exception:
            return 44100

    def _refresh_model_list(self) -> None:
        sr = self._resolve_sample_rate()
        filtered = self._model_store.filter_models(self.view.get_time_value(), sr)
        names = [m.model_name for m in filtered]
        has_models = self.view.set_model_options(names)
        desired = str(self.analysis_model._all_fields.get("model_name", "") or "")
        if desired:
            for i in range(self.view.combo_model.count()):
                if self.view.combo_model.itemText(i) == desired:
                    self.view.combo_model.setCurrentIndex(i)
                    break
        self.view.combo_model.setEnabled(self.view.checkbox_use_ai.isChecked() and has_models)
        self._update_ok_enabled()

    def _update_ok_enabled(self) -> None:
        ok_btn = self.view.button_box.button(QDialogButtonBox.Ok)
        if not ok_btn:
            return
        if self.view.checkbox_use_ai.isChecked():
            ok_btn.setEnabled(self.view.combo_model.count() > 0 and self.view.combo_model.itemText(0) != "无可用模型")
        else:
            ok_btn.setEnabled(True)

    def on_manage_models(self) -> None:
        # 延迟导入以避免循环依赖
        try:
            from ui.ai.register_ai_model import ModelManagerApp
        except Exception:
            ModelManagerApp = None
        if ModelManagerApp is None:
            QMessageBox.warning(self.view, "提示", "无法打开模型管理器：未找到 ModelManagerApp")
            return
        manager = ModelManagerApp(self._models_json_path)
        code, _ = manager.run()
        if code == QDialog.Accepted:
            # 重新加载模型列表
            self._model_store = AIModelStore.from_json_or_default(self._models_json_path)
            self._refresh_model_list()


# ---------------- Open API ---------------- #


def open_analysis_config_dialog(
    parent: Optional[QWidget] = None,
    initial: Optional[Dict[str, Any]] = None,
    forced_sample_rate: Optional[int] = None,
    models_json_path: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    合并的配置对话框入口：
    - 未勾选“启用 AI 分析”→ 禁用并取消勾选“启用通知限制”
    - 未勾选“启用通知限制”→ 禁用并取消勾选“启用 TCP”
    仍然使用 MVC 设计。
    """
    initial = initial or {}
    analysis_initial = initial.get("ai_config") if isinstance(initial, dict) else None
    limit_initial = initial.get("infor_limition") if isinstance(initial, dict) else None
    tcp_initial = initial.get("tcp_config") if isinstance(initial, dict) else None

    analysis_model = AnalysisToggleModel(initial=analysis_initial)
    limit_model = InforLimitionModel(initial=limit_initial)
    tcp_model = TcpConfigModel(initial=tcp_initial)
    view = AnalysisConfigView(forced_sample_rate=forced_sample_rate)
    if parent is not None:
        view.setParent(parent, Qt.Dialog)
    controller = AnalysisConfigController(
        analysis_model,
        limit_model,
        tcp_model,
        view,
        models_json_path=models_json_path,
        forced_sample_rate=forced_sample_rate,
    )
    code = view.exec_()
    if code == QDialog.Accepted:
        return 1, controller.get_result_values()
    return 0, {}


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    code, values = open_analysis_config_dialog(None, None)
    if code == 1:
        print(json.dumps(values, ensure_ascii=False, indent=2))
    else:
        print("Cancelled")
    sys.exit(0)


