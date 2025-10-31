import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QStatusBar, QLabel, QAction

from base.data_struct.data_deal_struct import DataDealStruct
from consts.model_consts import DEFAULT_DIR
from ui.ai.ai_analysis_config_mvc import AIConfigView, AIConfigController, AIModelStore
from ui.center_widget import CenterWidget
from base.indicator_engine import IndicatorEngine, parse_raw_input


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.data_struct = DataDealStruct()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("实时波形显示")
        self.center_widget = CenterWidget(self)

        self.setCentralWidget(self.center_widget)
        self.set_menu_bar()
        # 连接分析完成信号（若存在）
        try:
            self.center_widget.main_widget.analysis_completed.connect(self.on_analysis_completed)
        except Exception:
            pass

        # 指示灯引擎与定时器
        self._indicator_engine = IndicatorEngine(red_add_seconds=0.5)
        self._light_timer = QTimer(self)
        self._light_timer.setInterval(100)  # 100ms 刷新
        self._light_timer.timeout.connect(self._on_light_tick)
        self._light_timer.start()

    def set_menu_bar(self):
        menu_bar = QMenuBar()
        function_menu = menu_bar.addMenu("功能")
        ai_analysis_action = QAction("AI 分析", self)
        ai_analysis_action.triggered.connect(self.show_ai_analysis_window)
        function_menu.addAction(ai_analysis_action)
        hardware_menu = menu_bar.addMenu("硬件")
        user_menu = menu_bar.addMenu("用户")
        help_menu = menu_bar.addMenu("帮助")

        self.setMenuBar(menu_bar)
        # 连接录音开始/停止信号以禁用/启用菜单
        try:
            self.center_widget.main_widget.recording_started.connect(lambda: self.menuBar().setEnabled(False))
            self.center_widget.main_widget.recording_stopped.connect(lambda: self.menuBar().setEnabled(True))
        except Exception:
            pass

    def show_ai_analysis_window(self):
        json_path = DEFAULT_DIR + "ui/ui_config/models.json"
        model_store = AIModelStore.from_json_or_default(json_path)

        view = AIConfigView(forced_sample_rate=self.center_widget.main_widget.sampling_rate)
        controller = AIConfigController(model_store, view, models_json_path=json_path)  # noqa: F841 (保持引用)

        view.resize(420, 240)
        if view.exec_() != view.Accepted:
            return
        result = view.get_result_data()
        # print(result)

        self.center_widget.main_widget.build_audio_segment_extractor(
            extract_flag=bool(result.get("use_ai", False)),
            extract_interval=float(result.get("analysis_interval", 2.0)),
            segment_duration=float(result.get("time", 4.0)),
        )

        self.center_widget.main_widget.update_model_name(result.get("model_name", ""))

    def on_analysis_completed(self, results):
        """接收每轮多通道分析结果，可在此更新UI或记录日志。"""
        try:
            # 未录音则不处理、且保持指示灯关闭
            try:
                if not self.center_widget.main_widget.data_struct.record_flag:
                    self._update_lights_off()
                    return
            except Exception:
                pass
            # 驱动引擎
            items = parse_raw_input(results)
            self._indicator_engine.process_predictions(items)
            self._update_lights_ui_from_engine()
        except Exception:
            pass

    def _on_light_tick(self):
        try:
            # 未录音则不点亮指示灯
            try:
                if not self.center_widget.main_widget.data_struct.record_flag:
                    self._update_lights_off()
                    return
            except Exception:
                pass
            self._indicator_engine.tick(self._light_timer.interval() / 1000.0)
            self._update_lights_ui_from_engine()
        except Exception:
            pass

    def _update_lights_ui_from_engine(self):
        """聚合显示：若任一通道红灯亮 -> 总红灯亮；否则若存在 GREEN -> 总绿灯亮；否则全灰。"""
        # 未录音则关闭灯
        try:
            if not self.center_widget.main_widget.data_struct.record_flag:
                self._update_lights_off()
                return
        except Exception:
            pass
        snapshot = self._indicator_engine.render_snapshot()
        # 若尚无任何数据/通道，默认点亮绿灯
        if not snapshot:
            try:
                w = self.center_widget.main_widget
                w.set_light_color(w.red_light, "gray")
                w.set_light_color(w.green_light, "green")
            except Exception:
                pass
            return
        any_red = any(v.get("color") == "RED" for v in snapshot.values())
        any_green = any(v.get("color") == "GREEN" for v in snapshot.values())

        try:
            w = self.center_widget.main_widget
            if any_red:
                w.set_light_color(w.red_light, "red")
                w.set_light_color(w.green_light, "gray")
            elif any_green:
                w.set_light_color(w.red_light, "gray")
                w.set_light_color(w.green_light, "green")
            else:
                w.set_light_color(w.red_light, "gray")
                w.set_light_color(w.green_light, "gray")
        except Exception:
            pass

    def _update_lights_off(self):
        try:
            w = self.center_widget.main_widget
            w.set_light_color(w.red_light, "gray")
            w.set_light_color(w.green_light, "gray")
        except Exception:
            pass

    def show_statusbar_layout(self):
        # create status bar, show the user data and device data, and close drag status bar modify window size
        self.user_label = QLabel()
        self.user_label.setAlignment(Qt.AlignLeft)
        self.user_label.setText(
            "当前用户：{name}  用户等级：{level}".format(name=self.user_name, level=self.access_lvl)
        )
        self.device_label = QLabel()
        device_txt = "麦克风：{mic}  扬声器：{speaker}".format(mic=self.mic["name"], speaker=self.speaker["name"])
        self.device_label.setText(device_txt)

        statusbar = QStatusBar()
        statusbar.setSizeGripEnabled(False)
        statusbar.addWidget(self.user_label)
        statusbar.addPermanentWidget(self.device_label)
        self.setStatusBar(statusbar)

    def closeEvent(self, event):
        self.center_widget.main_widget.audio_manager.stop_recording()
        self.center_widget.main_widget.audio_manager.quit()
        self.center_widget.main_widget.audio_manager.wait()
        self.data_struct.record_flag = False
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
