"""
历史数据窗口（HistoryDataWindow）模块

对外接口（推荐调用）：
- HistoryDataWindow.load_history_data():
    从数据库查询历史录音数据并写入表格（清空旧数据后再填充）。
- HistoryDataWindow.show():
    已重载，展示窗口前自动调用 load_history_data()，保证数据为最新。
- HistoryDataWindow.add_history_data(audio_datas):
    批量将外部已查询的数据写入表格。
- HistoryDataWindow.add_history_data_to_table(...):
    将单条历史记录写入表格。
- HistoryDataWindow.on_cell_clicked(index):
    响应“操作”列播放/暂停的交互。
- HistoryDataWindow.load_wave_data(path):
    从指定路径加载波形数据用于播放。
- HistoryDataWindow.player_wave_data(wave_data):
    播放给定的波形数据。

使用示例：
    from ui.historical_data import HistoryDataWindow

    dlg = HistoryDataWindow()
    # 方式一：手动加载
    dlg.load_history_data()
    dlg.show()

    # 方式二：直接 show（内部会自动加载）
    dlg = HistoryDataWindow()
    dlg.show()

注意：
- 数据库查询依赖 base.audio_data_manager.get_record_audio_data_from_db 与 get_record_audio_data_path。
- 播放依赖 base.player_audio.AudioPlayer；读取音频依赖 librosa。
"""

import sys
import librosa

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QTableView, QHeaderView

from base.audio_data_manager import get_record_audio_data_from_db, get_record_audio_data_path
from base.player_audio import AudioPlayer
from consts.running_consts import DEFAULT_DIR


class HistoryDataWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.history_data_table = QTableView()
        self.history_data_table.setIconSize(QSize(25, 25))
        self.history_data_model = CustomStandardItemModel(0, 6, [4])
        self.history_data_table.setModel(self.history_data_model)
        self.paly_flag = False

        self.player = None

        self.play_icon = QIcon(DEFAULT_DIR + "ui/ui_pic/sequence_pic/play.png")
        self.pause_icon = QIcon(DEFAULT_DIR + "ui/ui_pic/sequence_pic/pause.png")
        self.history_data_table.clicked.connect(self.on_cell_clicked)

        self.init_ui()

    def init_ui(self):
        history_data_table_layout = self.create_history_data_table_layout()

        self.setLayout(history_data_table_layout)

    def create_history_data_table_layout(self):
        self.history_data_table.setColumnWidth(4, 100)  # 设置操作列宽度为 100 像素
        self.history_data_table.verticalHeader().setDefaultSectionSize(40)
        self.history_data_table.setStyleSheet(
            """QTableView::item {
                    border-top: 1px solid rgb(130, 135, 144);
                    color: black;
            }"""
        )
        self.history_data_table.model().setHorizontalHeaderLabels(
            ["文件名称", "录制时间", "结束时间", "操作员", "备注", "操作"]
        )
        # self.history_data_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        header = self.history_data_table.horizontalHeader()
        for i in range(self.history_data_model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        # header.setStretchLastSection(True)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        # 数据加载改为显式接口调用：请调用 load_history_data()

        history_data_table_layout = QVBoxLayout()
        history_data_table_layout.addWidget(self.history_data_table)

        return history_data_table_layout

    def load_history_data(self):
        """
        显式从数据库查询历史录音数据并填充表格。
        可在外部初始化完控件后调用，以避免在构造阶段自动加载。
        """
        result = get_record_audio_data_from_db()
        try:
            self.history_data_model.removeRows(0, self.history_data_model.rowCount())
        except Exception:
            pass

        if result:
            self.add_history_data(result)
        self.history_data_table.viewport().update()

    def add_history_data(self, audio_datas):
        for audio_data in audio_datas:
            record_audio_data_path, record_time, stop_time, operator, description = audio_data
            # print(record_audio_data_path, record_time, stop_time, operator, description)
            self.add_history_data_to_table(record_audio_data_path, record_time, stop_time, operator, description)

    def add_history_data_to_table(
        self, record_audio_data_path: str, record_time: str, stop_time: str, operator: str, description: str
    ):
        audio_data_items = []
        record_audio_name = self.get_record_audio_data_name(record_audio_data_path)
        play_item = CustomStandardItem(DEFAULT_DIR + "ui/ui_pic/sequence_pic/play.png", "播放")
        record_audio_name_item = QStandardItem(record_audio_name)
        record_time_item = QStandardItem(str(record_time))
        stop_time_item = QStandardItem(str(stop_time))
        operator_item = QStandardItem(operator)
        description_item = QStandardItem(description)
        audio_data_items.append(record_audio_name_item)
        audio_data_items.append(record_time_item)
        audio_data_items.append(stop_time_item)
        audio_data_items.append(operator_item)
        audio_data_items.append(description_item)
        audio_data_items.append(play_item)
        self.history_data_model.appendRow(audio_data_items)

    def get_record_audio_data_name(self, record_audio_data_path: str):
        if record_audio_data_path:
            return record_audio_data_path.split("/")[-1].split(".")[0]
        return ""

    def on_cell_clicked(self, index):
        if index.column() == 5:
            item = self.history_data_model.item(index.row(), index.column())
            if item.flag:
                if self.paly_flag:
                    return
                record_time = self.get_cell_content(index.row(), 1)
                wave_file_path = get_record_audio_data_path(record_time)
                print(wave_file_path)
                wave_data = self.load_wave_data(wave_file_path)
                self.player_wave_data(wave_data)
                item.setIcon(self.pause_icon)
                item.setText("暂停")
                item.flag = False
                self.paly_flag = True
            else:
                self.player.stop()
                item.setIcon(self.play_icon)
                item.setText("播放")
                item.flag = True
                self.paly_flag = False
            # 通知视图更新图标
            self.history_data_model.dataChanged.emit(index, index, [Qt.DecorationRole])

    def get_cell_content(self, row, column):
        item = self.history_data_model.item(row, column)
        if item:
            return item.text()
        return None

    def load_wave_data(self, wave_file_path):
        wave_data = librosa.load(wave_file_path, sr=44100, mono=False)[0]
        if len(wave_data.shape) == 2:
            wave_data = wave_data.T
        return wave_data

    def player_wave_data(self, wave_data):
        self.player = AudioPlayer(wave_data)
        self.player.playback_finished.connect(self.on_playback_finished)
        self.player.start()

    def on_playback_finished(self):
        print("播放完成")

    def show(self):
        # 展示前自动刷新一次数据
        self.load_history_data()    
        super().show()


class CustomStandardItemModel(QStandardItemModel):
    def __init__(self, rows, columns, editable_column: list, parent=None):
        super().__init__(rows, columns, parent)
        self.editable_column = editable_column

    def flags(self, index):
        if index.isValid():
            if index.column() in self.editable_column:
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
            else:
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return super().flags(index)


class CustomStandardItem(QStandardItem):
    def __init__(self, icon_url: str, text: str = None):
        super().__init__(text)

        self.flag = True

        if icon_url:
            self.setIcon(QIcon(icon_url))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HistoryDataWindow()
    window.setWindowTitle("历史数据")
    window.setGeometry(100, 100, 800, 600)
    window.show()
    sys.exit(app.exec_())
