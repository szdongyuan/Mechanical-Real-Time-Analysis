import json
import os
import sys
from typing import Optional, Tuple, Dict

from consts.running_consts import DEFAULT_DIR

PROJECT_ROOT = DEFAULT_DIR.rstrip("/\\")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
UI_CONFIG_DIR = os.path.join(PROJECT_ROOT, "ui", "ui_config")

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

TCP_CONFIG_JSON_REL = "ui/ui_config/tcp_config.json"


class TcpConfigDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, initial: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("TCP 配置")
        self._config_path = os.path.normpath(os.path.join(UI_CONFIG_DIR, "tcp_config.json"))

        self.enable_checkbox = QCheckBox("启用 TCP")
        self.enable_audio_checkbox = QCheckBox("启用音频 TCP")
        self.ip_edit = QLineEdit()
        self.client_ip_edit = QLineEdit()
        self.port_spin = QSpinBox()
        self.audio_interval_spin = QSpinBox()
        self.tcp_audio_sample_rate_spin = QSpinBox()
        self.tcp_audio_bit_depth_spin = QSpinBox()

        # IP 输入：默认 127.0.0.1，正则约束每段 0-255
        self.ip_edit.setPlaceholderText("192.168.2.141")
        self.client_ip_edit.setPlaceholderText("192.168.2.168")
        ip_regex = QRegularExpression(
            r"^(25[0-5]|2[0-4]\d|1?\d?\d)\."
            r"(25[0-5]|2[0-4]\d|1?\d?\d)\."
            r"(25[0-5]|2[0-4]\d|1?\d?\d)\."
            r"(25[0-5]|2[0-4]\d|1?\d?\d)$"
        )
        self.ip_edit.setValidator(QRegularExpressionValidator(ip_regex, self))
        self.client_ip_edit.setValidator(QRegularExpressionValidator(ip_regex, self))

        # 端口范围：49152-65535，默认 50000
        self.port_spin.setRange(49152, 65535)
        self.port_spin.setValue(50000)
        self.audio_interval_spin.setRange(1, 600)
        self.audio_interval_spin.setValue(60)
        self.audio_interval_spin.setSuffix(" s")
        self.tcp_audio_sample_rate_spin.setRange(1000, 192000)
        self.tcp_audio_sample_rate_spin.setValue(16000)
        self.tcp_audio_sample_rate_spin.setSuffix(" Hz")
        self.tcp_audio_bit_depth_spin.setRange(8, 32)
        self.tcp_audio_bit_depth_spin.setSingleStep(8)
        self.tcp_audio_bit_depth_spin.setValue(16)
        self.tcp_audio_bit_depth_spin.setSuffix(" bit")

        # 默认值
        self.enable_checkbox.setChecked(False)
        self.enable_audio_checkbox.setChecked(False)
        self.ip_edit.setText("192.168.2.141")
        self.client_ip_edit.setText("192.168.2.168")

        # 从 initial 或已有配置加载
        cfg = self._load_initial(initial)
        self.enable_checkbox.setChecked(bool(cfg.get("enable_tcp", False)))
        self.enable_audio_checkbox.setChecked(bool(cfg.get("enable_audio_tcp", False)))
        server_ip = str(cfg.get("server_ip", cfg.get("ip", "192.168.2.141"))) or "192.168.2.141"
        self.ip_edit.setText(server_ip)
        self.client_ip_edit.setText(str(cfg.get("client_ip", "192.168.2.168")) or "192.168.2.168")
        try:
            self.port_spin.setValue(int(cfg.get("port", 50000)))
        except Exception:
            self.port_spin.setValue(50000)
        try:
            self.audio_interval_spin.setValue(int(cfg.get("audio_interval_sec", 60)))
        except Exception:
            self.audio_interval_spin.setValue(60)
        try:
            self.tcp_audio_sample_rate_spin.setValue(int(cfg.get("tcp_audio_sample_rate", 16000)))
        except Exception:
            self.tcp_audio_sample_rate_spin.setValue(16000)
        try:
            self.tcp_audio_bit_depth_spin.setValue(int(cfg.get("tcp_audio_bit_depth", 16)))
        except Exception:
            self.tcp_audio_bit_depth_spin.setValue(16)

        # 表单布局
        form = QFormLayout()
        form.addRow(self.enable_checkbox)
        form.addRow(self.enable_audio_checkbox)
        form.addRow("服务端 IP", self.ip_edit)
        form.addRow("客户端 IP", self.client_ip_edit)
        form.addRow("端口号", self.port_spin)
        form.addRow("音频发送间隔", self.audio_interval_spin)
        form.addRow("TCP 音频采样率", self.tcp_audio_sample_rate_spin)
        form.addRow("TCP 音频位深度", self.tcp_audio_bit_depth_spin)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        root_layout = QVBoxLayout()
        root_layout.addLayout(form)
        root_layout.addWidget(buttons)
        self.setLayout(root_layout)

    def _load_initial(self, initial: Optional[Dict]) -> Dict:
        if isinstance(initial, dict) and initial:
            return initial
        # 若无 initial，尝试从 json 读取
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def _validate(self) -> Tuple[bool, str]:
        for label, edit in (("服务端 IP", self.ip_edit), ("客户端 IP", self.client_ip_edit)):
            ip = edit.text().strip()
            if not ip:
                return False, f"{label}不能为空"
            # 运行时再校验一次
            parts = ip.split(".")
            if len(parts) != 4:
                return False, f"{label}格式不正确"
            try:
                for p in parts:
                    v = int(p)
                    if v < 0 or v > 255:
                        return False, f"{label}每段应在 0-255 之间"
            except Exception:
                return False, f"{label}格式不正确"
        port = int(self.port_spin.value())
        if port < 49152 or port > 65535:
            return False, "端口号应在 49152-65535 范围内"
        audio_interval_sec = int(self.audio_interval_spin.value())
        if audio_interval_sec < 1 or audio_interval_sec > 600:
            return False, "音频发送间隔应在 1-600 秒之间"
        bit_depth = int(self.tcp_audio_bit_depth_spin.value())
        if bit_depth not in (8, 16, 32):
            return False, "TCP 音频位深度仅支持 8、16、32"
        return True, ""

    def _on_accept(self):
        ok, msg = self._validate()
        if not ok:
            QMessageBox.warning(self, "提示", msg)
            return
        cfg = {
            "enable_tcp": bool(self.enable_checkbox.isChecked()),
            "enable_audio_tcp": bool(self.enable_audio_checkbox.isChecked()),
            "server_ip": self.ip_edit.text().strip(),
            "client_ip": self.client_ip_edit.text().strip(),
            "ip": self.ip_edit.text().strip(),
            "port": int(self.port_spin.value()),
            "audio_interval_sec": int(self.audio_interval_spin.value()),
            "tcp_audio_sample_rate": int(self.tcp_audio_sample_rate_spin.value()),
            "tcp_audio_bit_depth": int(self.tcp_audio_bit_depth_spin.value()),
        }
        # 保存到 json
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败：{e}")
            return
        # 设置结果并关闭
        self._result_config = cfg
        self.accept()

    def get_config(self) -> Dict:
        return getattr(self, "_result_config", {
            "enable_tcp": bool(self.enable_checkbox.isChecked()),
            "enable_audio_tcp": bool(self.enable_audio_checkbox.isChecked()),
            "server_ip": self.ip_edit.text().strip() or "192.168.2.141",
            "client_ip": self.client_ip_edit.text().strip() or "192.168.2.168",
            "ip": self.ip_edit.text().strip() or "192.168.2.141",
            "port": int(self.port_spin.value()),
            "audio_interval_sec": int(self.audio_interval_spin.value()),
            "tcp_audio_sample_rate": int(self.tcp_audio_sample_rate_spin.value()),
            "tcp_audio_bit_depth": int(self.tcp_audio_bit_depth_spin.value()),
        })


def open_tcp_config_dialog(parent: Optional[QWidget] = None, initial: Optional[Dict] = None) -> Tuple[int, Dict]:
    """
    打开 TCP 配置窗口。
    返回：(code, values)
    - code == 1 表示确认（Accepted），values 为配置字典
    - code == 0 表示取消（Rejected），values 为空字典
    """
    dlg = TcpConfigDialog(parent, initial=initial)
    code = dlg.exec_()
    if code == QDialog.Accepted:
        return 1, dlg.get_config()
    return 0, {}


if __name__ == "__main__":
    # 独立运行入口：启动应用并打开 TCP 配置窗口
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    code, values = open_tcp_config_dialog(None, None)
    # 控制台输出结果，便于调试
    if code == 1:
        print(json.dumps(values, ensure_ascii=False, indent=2))
    else:
        print("Cancelled")
    sys.exit(0)


