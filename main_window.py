import sys
import random
import os
import json
import tempfile

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QStatusBar, QLabel, QAction

from base.data_struct.data_deal_struct import DataDealStruct
from base.log_manager import LogManager
from base.save_audio import save_and_log_warning_segment
from consts.model_consts import DEFAULT_DIR
from ui.ai.ai_analysis_config_mvc import AIConfigView, AIConfigController, AIModelStore
from ui.center_widget import CenterWidget
from ui.infor_limition import open_infor_limition_dialog
from ui.tcp_config import open_tcp_config_dialog


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
        if r > 0.25:
            desired = "OK"
            evaluations[ch] = "良好"
        else:
            desired = "NG"
            if r > 0.15:
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
        self.setWindowIcon(QIcon(DEFAULT_DIR + "ui/ui_pic/sys_ico/icon.ico"))
        self.logger = LogManager.set_log_handler("core")

        self.init_ui()
        self.load_model_analysis_config()

    def init_ui(self):
        self.setWindowTitle("设备健康状态监测")
        self.center_widget = CenterWidget(self)

        self.setCentralWidget(self.center_widget)
        self.set_menu_bar()

        try:
            self.center_widget.analysis_completed.connect(self.on_analysis_completed)
        except Exception:
            pass

    def set_menu_bar(self):
        menu_bar = QMenuBar()
        function_menu = menu_bar.addMenu("功能")
        ai_analysis_action = QAction("AI 分析", self)
        ai_analysis_action.triggered.connect(self.show_ai_analysis_window)
        function_menu.addAction(ai_analysis_action)
        infor_limit_action = QAction("通知限制", self)
        infor_limit_action.triggered.connect(self.show_infor_limit_window)
        function_menu.addAction(infor_limit_action)
        tcp_config_action = QAction("TCP 配置", self)
        tcp_config_action.triggered.connect(self.show_tcp_config_window)
        function_menu.addAction(tcp_config_action)
        hardware_menu = menu_bar.addMenu("硬件")
        user_menu = menu_bar.addMenu("用户")
        help_menu = menu_bar.addMenu("帮助")

        self.setMenuBar(menu_bar)
        # 连接录音开始/停止信号以禁用/启用菜单
        try:
            self.center_widget.recording_started.connect(lambda: self.menuBar().setEnabled(False))
            self.center_widget.recording_stopped.connect(lambda: self.menuBar().setEnabled(True))
        except Exception:
            pass

    def show_ai_analysis_window(self):
        json_path = DEFAULT_DIR + "ui/ui_config/models.json"
        model_store = AIModelStore.from_json_or_default(json_path)

        view = AIConfigView(forced_sample_rate=self.center_widget.rm_model.sampling_rate)
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

        self.center_widget.rm_controller.build_audio_segment_extractor(
            extract_flag=bool(self.model_analysis_config.get("use_ai", False)),
            extract_interval=float(self.model_analysis_config.get("analysis_interval", 2.0)),
            segment_duration=float(self.model_analysis_config.get("time", 4.0)),
        )
        self.center_widget.rm_controller.update_model_name(self.model_analysis_config.get("model_name", ""))
        if self.model_analysis_config.get("use_ai", False):
            self.center_widget.rm_controller.start_analysis_process()
        else:
            self.center_widget.rm_controller.stop_analysis_process()
    
    def show_infor_limit_window(self):
        code, values = open_infor_limition_dialog(None, initial=self.center_widget.rm_model.infor_limit_config)
        if code == 1:
            self.center_widget.rm_model.infor_limit_config = values

    def show_tcp_config_window(self):
        code, values = open_tcp_config_dialog(None, initial=self.center_widget.rm_model.tcp_config)
        if code == 1:
            self.center_widget.rm_model.tcp_config = values

    def load_model_analysis_config(self):
        analysis_json_path = os.path.normpath(DEFAULT_DIR + "ui/ui_config/model_analysis.json")
        if os.path.exists(analysis_json_path):
            with open(analysis_json_path, "r", encoding="utf-8") as f:
                self.model_analysis_config = json.load(f)
        self.center_widget.rm_controller.build_audio_segment_extractor(
            extract_flag=bool(self.model_analysis_config.get("use_ai", False)),
            extract_interval=float(self.model_analysis_config.get("analysis_interval", 3.5)),
            segment_duration=float(self.model_analysis_config.get("time", 4.0)),
        )
        self.center_widget.rm_controller.update_model_name(self.model_analysis_config.get("model_name", ""))

        if self.model_analysis_config.get("use_ai", False):
            self.center_widget.rm_controller.start_analysis_process()

    @staticmethod
    def _evaluate_results(results):
        result = results[0]["result"][0][1]
        if result == "OK":
            return "良好"
        else:
            return "错误"

    def on_analysis_completed(self, results):
        try:
            # 未录音则不处理
            try:
                if not self.center_widget.rm_model.data_struct.record_flag:
                    return
            except Exception:
                pass

            analysis_level = self._evaluate_results(results)

            se = getattr(self.center_widget.rm_model, "segment_extractor", None)
            if se is not None and getattr(se, "is_running", False):
                segs = se.get_extracted_segments()
                info = se.get_segment_info()
                sr = int(info.get("sampling_rate") or getattr(self.center_widget.rm_model, "sampling_rate", 44100))
                dur = float(info.get("segment_duration") or 4.0)
                create_time_list = info.get("create_time_list") or []
                if segs is not None:
                    for entry in results:
                        try:
                            res_list = entry.get("result") or []
                            if not res_list:
                                continue
                            first = res_list[0]
                            result_str = str(first[1]).upper() if len(first) > 1 else "OK"
                        except Exception:
                            continue

                        if result_str == "NG":
                            try:
                                save_and_log_warning_segment(
                                    segment=segs,
                                    sampling_rate=sr,
                                    segment_duration_sec=dur,
                                    warning_level=analysis_level,
                                    create_time=create_time_list[0],
                                )
                            except Exception as e:
                                self.logger.error(e)
                create_time_list.pop(0)
        except Exception as e:
            self.logger.error(e)


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
        self.center_widget.rm_model.audio_manager.stop_recording()
        self.center_widget.rm_model.audio_manager.quit()
        self.center_widget.rm_model.audio_manager.wait()
        self.data_struct.record_flag = False
        temp_dir = os.path.join(tempfile.gettempdir(), "audio_segments_tmp")
        try:
            if os.path.isdir(temp_dir):
                for name in os.listdir(temp_dir):
                    fp = os.path.join(temp_dir, name)
                    if os.path.isfile(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
            else:
                os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            print(f"清理临时目录失败: {e}")
        event.accept()


if __name__ == "__main__":
    import multiprocessing as mp
    mp.freeze_support()  # 关键：PyInstaller 下多进
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
