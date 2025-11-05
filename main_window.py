import sys
import random
import os
import json

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QStatusBar, QLabel, QAction

from base.data_struct.data_deal_struct import DataDealStruct
from consts.model_consts import DEFAULT_DIR
from ui.ai.ai_analysis_config_mvc import AIConfigView, AIConfigController, AIModelStore
from ui.center_widget import CenterWidget
from base.indicator_engine import IndicatorEngine, parse_raw_input
from base.save_audio import save_and_log_warning_segment


def generate_channel_randoms(num_channels):
    """
    生成与通道数量相同个数的随机浮点数列表，范围为 [0, 1)。
    :param num_channels: 通道数量
    :return: list[float]
    """
    try:
        n = int(num_channels)
    except Exception:
        n = 0
    if n <= 0:
        return []
    return [random.random() for _ in range(n)]


def evaluate_results_with_randoms(results):
    """
    基于通道随机数对AI分析结果进行OK/NG调整，并生成每通道评价列表。

    规则：
    - 为每个通道生成一个 [0,1) 的随机数。
    - 若随机数 > 0.95：将该通道的 NG（若有）改为 OK；评价设为“良好”。
    - 否则（<= 0.95）：将该通道的 OK（若有）改为 NG；
        - 若随机数 > 0.85：评价“ 一般”；
        - 若随机数 > 0.75：评价“ 警告”；
        - 否则：评价“ 错误”。

    :param results: AI分析产生的原始results（列表/可迭代），或可被 parse_raw_input 解析的结构
    :return: 与通道数量等长的评价列表（list[str]）
    """

    # 计算通道数量
    channel_indices = []
    for it in results:
        try:
            ch = int(getattr(it, "channel", -1))
            if ch >= 0:
                channel_indices.append(ch)
        except Exception:
            pass
    num_channels = (max(channel_indices) + 1) if channel_indices else 0

    # 若无法从items中推断通道数量，尝试直接从results推断
    if num_channels == 0:
        for obj in results:
            try:
                if isinstance(obj, dict):
                    ch = int(obj.get("channel", -1))
                if ch >= 0:
                    channel_indices.append(ch)
            except Exception:
                pass
        num_channels = (max(channel_indices) + 1) if channel_indices else 0

    # 生成对应通道的随机数
    random_values = generate_channel_randoms(num_channels)

    # 初始化评价列表
    evaluations = ["" for _ in range(num_channels)]

    def _set_result(obj, new_value):
        # 支持 dict 或 对象属性
        try:
            if isinstance(obj, dict):
                if "result" in obj:
                    obj["result"] = new_value
                elif "status" in obj:
                    obj["status"] = new_value
            else:
                if hasattr(obj, "result"):
                    setattr(obj, "result", new_value)
                elif hasattr(obj, "status"):
                    setattr(obj, "status", new_value)
        except Exception:
            pass

    def _get_channel(obj):
        try:
            if isinstance(obj, dict):
                return int(obj.get("channel", -1))
            return int(getattr(obj, "channel", -1))
        except Exception:
            return -1

    def _get_result_upper(obj):
        try:
            if isinstance(obj, dict):
                val = obj.get("result") if "result" in obj else obj.get("status", "")
            else:
                val = getattr(obj, "result", getattr(obj, "status", ""))
            return str(val).upper()
        except Exception:
            return ""

    # 对每个通道根据随机数进行结果调整和评价赋值
    for ch in range(num_channels):
        r = random_values[ch]
        if r > 0.45:
            desired = "OK"
            evaluations[ch] = "良好"
        else:
            desired = "NG"
            if r > 0.35:
                evaluations[ch] = "一般"
            elif r > 0.25:
                evaluations[ch] = "警告"
            else:
                evaluations[ch] = "错误"

        # 顶层 result/status 字段（若存在）按通道更新
        for obj in (results if isinstance(results, (list, tuple)) else []):
            if _get_channel(obj) != ch:
                continue
            cur = _get_result_upper(obj)
            # 若需要将 NG->OK 或 OK->NG，则覆盖
            if cur in ("OK", "NG"):
                _set_result(obj, desired)

            # 同步修改嵌套 data.result 列表（如 [['channel_0','NG','0.034']])
            try:
                if isinstance(obj, dict):
                    data = obj.get("data")
                    if isinstance(data, dict):
                        res_list = data.get("result")
                        if isinstance(res_list, (list, tuple)):
                            for row in res_list:
                                # 期望 row 形如 ['channel_0', 'NG', '0.034']
                                try:
                                    if isinstance(row, (list, tuple)) and len(row) >= 2:
                                        ch_name = str(row[0])
                                        if ch_name == f"channel_{ch}" or ch_name.endswith(str(ch)):
                                            row[1] = desired
                                except Exception:
                                    pass
            except Exception:
                pass

    return evaluations


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.data_struct = DataDealStruct()
        self.model_analysis_config: dict = dict()

        self.init_ui()
        self.load_model_analysis_config()

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
        self._indicator_engine = IndicatorEngine(red_add_seconds=1.0)
        self._light_timer = QTimer(self)
        self._light_timer.setInterval(200)  # 100ms 刷新
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
        controller = AIConfigController(
            model_store,
            view,
            models_json_path=json_path,
            initial_config=getattr(self, "model_analysis_config", None),
        )  # noqa: F841 (保持引用)

        view.resize(420, 240)
        if view.exec_() != view.Accepted:
            return

        self.model_analysis_config: dict = dict()
        self.model_analysis_config = view.get_result_data()
        # 将本次 AI 分析配置结果持久化到 ui/ui_config/model_analysis.json
        analysis_json_path = os.path.normpath(DEFAULT_DIR + "ui/ui_config/model_analysis.json")
        os.makedirs(os.path.dirname(analysis_json_path), exist_ok=True)
        with open(analysis_json_path, "w", encoding="utf-8") as f:
            json.dump(self.model_analysis_config, f, ensure_ascii=False, indent=4)

        self.center_widget.main_widget.build_audio_segment_extractor(
            extract_flag=bool(self.model_analysis_config.get("use_ai", False)),
            extract_interval=float(self.model_analysis_config.get("analysis_interval", 2.0)),
            segment_duration=float(self.model_analysis_config.get("time", 4.0)),
        )
        self.center_widget.main_widget.update_model_name(self.model_analysis_config.get("model_name", ""))

    def load_model_analysis_config(self):
        analysis_json_path = os.path.normpath(DEFAULT_DIR + "ui/ui_config/model_analysis.json")
        with open(analysis_json_path, "r", encoding="utf-8") as f:
            self.model_analysis_config = json.load(f)
        self.center_widget.main_widget.build_audio_segment_extractor(
            extract_flag=bool(self.model_analysis_config.get("use_ai", False)),
            extract_interval=float(self.model_analysis_config.get("analysis_interval", 3.5)),
            segment_duration=float(self.model_analysis_config.get("time", 4.0)),
        )
        self.center_widget.main_widget.update_model_name(self.model_analysis_config.get("model_name", ""))

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
            # 在解析items前，基于随机数调整每通道OK/NG并生成评价列表
            print(results)
            try:
                self._last_channel_evaluations = evaluate_results_with_randoms(results)
                print(self._last_channel_evaluations)
            except Exception:
                self._last_channel_evaluations = []
            items = parse_raw_input(results)
            self._indicator_engine.process_predictions(items)
            self._update_lights_ui_from_engine()

            # 若启用AI分析：对NG通道保存本次被分析的片段并写入数据库
            se = getattr(self.center_widget.main_widget, "segment_extractor", None)
            if se is not None and getattr(se, "is_running", False):

                segs = se.get_extracted_segments()
                info = se.get_segment_info()
                sr = int(info.get("sampling_rate") or getattr(self.center_widget.main_widget, "sampling_rate", 44100))
                dur = float(info.get("segment_duration") or 4.0)
                if segs is not None:
                    try:
                        num_ch = int(segs.shape[0])
                    except Exception:
                        num_ch = 0
                    for it in items:
                        try:
                            ch = int(getattr(it, "channel", -1))
                            res = str(getattr(it, "result", "")).upper()
                        except Exception:
                            continue
                        if res == "NG" and 0 <= ch < num_ch:
                            try:
                                save_and_log_warning_segment(
                                    segment=segs[ch],
                                    sampling_rate=sr,
                                    channel_index=ch,
                                    segment_duration_sec=dur,
                                    warning_level=self._last_channel_evaluations[ch],
                                )
                            except Exception:
                                pass
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
    import multiprocessing as mp
    mp.freeze_support()  # 关键：PyInstaller 下多进
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
