import json
import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from consts.db_consts import JSON_DIR_PATH


class InforLimitionModel:
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._config_path = os.path.join(JSON_DIR_PATH, "infor_limition.json")
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
            except Exception:
                pass

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
        except Exception:
            pass

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


class InforLimitionView(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("通知限制设置")
        self.setModal(True)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 1000000)
        self.duration_spin.setSuffix(" min")

        self.max_count_spin = QSpinBox()
        self.max_count_spin.setRange(1, 100000000)

        self.enable_checkbox = QCheckBox("启用通知限制")

        confirm_btn = QPushButton("确认")
        cancel_btn = QPushButton("取消")
        self.confirm_btn = confirm_btn
        self.cancel_btn = cancel_btn

        form = QFormLayout()
        form.addRow(self.enable_checkbox)
        form.addRow(QLabel("统计时长"), self.duration_spin)
        form.addRow(QLabel("最大数量"), self.max_count_spin)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(confirm_btn)
        btn_row.addWidget(cancel_btn)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addStretch(1)
        root.addLayout(btn_row)
        self.setLayout(root)

    def set_inputs_enabled(self, enabled: bool) -> None:
        self.duration_spin.setEnabled(bool(enabled))
        self.max_count_spin.setEnabled(bool(enabled))

    def set_values(self, duration_min: int, max_count: int, enable_limit: bool) -> None:
        self.duration_spin.setValue(int(duration_min))
        self.max_count_spin.setValue(int(max_count))
        self.enable_checkbox.setChecked(bool(enable_limit))
        self.set_inputs_enabled(bool(enable_limit))

    def get_values(self) -> Dict[str, Any]:
        return {
            "duration_min": int(self.duration_spin.value()),
            "max_count": int(self.max_count_spin.value()),
            "enable_limit": bool(self.enable_checkbox.isChecked()),
        }


class InforLimitionController:
    def __init__(self, model: InforLimitionModel, view: InforLimitionView) -> None:
        self.model = model
        self.view = view
        self.result_values: Optional[Dict[str, Any]] = None
        self._bind()
        self._init_values()

    def _bind(self) -> None:
        self.view.confirm_btn.clicked.connect(self.on_confirm)
        self.view.cancel_btn.clicked.connect(self.on_cancel)
        self.view.enable_checkbox.toggled.connect(self.on_toggle_enable_limit)

    def _init_values(self) -> None:
        self.view.set_values(
            duration_min=self.model.duration_min,
            max_count=self.model.max_count,
            enable_limit=self.model.enable_limit,
        )

    def on_confirm(self) -> None:
        values = self.view.get_values()
        self.result_values = dict(values)
        self.model.save(
            duration_min=values["duration_min"],
            max_count=values["max_count"],
            enable_limit=values["enable_limit"],
        )
        self.view.accept()

    def on_cancel(self) -> None:
        self.view.reject()

    def on_toggle_enable_limit(self, checked: bool) -> None:
        self.view.set_inputs_enabled(bool(checked))


def open_infor_limition_dialog(parent: QWidget = None, initial: Optional[Dict[str, Any]] = None) -> (int, Optional[Dict[str, Any]]):
    model = InforLimitionModel(initial=initial)
    view = InforLimitionView()
    if parent is not None:
        view.setParent(parent, Qt.Dialog)
    controller = InforLimitionController(model, view)
    code = view.exec_()
    if code == QDialog.Accepted:
        return code, controller.result_values
    return code, None


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    # code, values = open_infor_limition_dialog(None)
    code, values = open_infor_limition_dialog(None, None)
    # code, values = open_infor_limition_dialog(None, initial={"duration_min": 10, "max_count": 10, "eable_limit": True})
    if code == QDialog.Accepted:
        print(values)
    sys.exit(0)


