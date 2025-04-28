import sys
import time
from datetime import datetime
from concurrent import futures

import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QGroupBox, QHBoxLayout, QLineEdit, QLabel
from PyQt5.QtWidgets import QMessageBox, QTabWidget, QVBoxLayout, QPushButton, QSpacerItem
from PyQt5.QtWidgets import QSizePolicy, QWidget, QRadioButton

from base.pre_processing.audio_thd_frequency_response_analysis import AudioThdFrequencyResponseAnalysis
from base.soundcard_audio_processor import SoundcardAudioProcessor
from consts import ui_style_const, error_code


class CalibrationWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """
            Initialize the user interface for the calibration window.
            This function sets up the window icon, title, size, and layout, 
            and creates tabs for output and input calibration.
        """
        self.setWindowTitle("校准窗口")
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setMinimumSize(500, 550)
        self.setMaximumSize(600, 580)
        cal_wnd_layout = QVBoxLayout()

        self.tabwidget = QTabWidget()
        self.input_cal_wnd = InputCalibration()

        btn_layout = self.create_btn_box()

        cal_wnd_layout.addWidget(self.input_cal_wnd)
        cal_wnd_layout.addLayout(btn_layout)
        self.setLayout(cal_wnd_layout)

    def create_btn_box(self):
        """
            Create a button box

            This method creates a horizontal layout containing calibration, reset, and cancel buttons.
            Spacers are used to adjust the spacing between the buttons in the layout.
        """
        btn_layout = QHBoxLayout()
        self.cal_btn = QPushButton(" 校  准 ")
        self.cal_btn.clicked.connect(self.clicked_calibration_button)
        reset_btn = QPushButton(" 重  置 ")
        reset_btn.clicked.connect(self.clicked_reset_button)
        cancel_btn = QPushButton(" 退  出 ")
        cancel_btn.clicked.connect(self.clicked_close_button)
        h_spacer_btn1 = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        h_spacer_btn2 = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        btn_layout.addWidget(self.cal_btn)
        btn_layout.addItem(h_spacer_btn1)
        btn_layout.addWidget(reset_btn)
        btn_layout.addItem(h_spacer_btn2)
        btn_layout.addWidget(cancel_btn)
        return btn_layout

    def clicked_calibration_button(self):
        self.cal_btn.setDisabled(True)
        self.input_cal_wnd.clicked_calibration()

    def clicked_reset_button(self):
        self.input_cal_wnd.reset_btn_clicked()
        self.cal_btn.setDisabled(False)

    def clicked_close_button(self):
        self.input_cal_wnd.stop_timer = True
        self.close()



class InputCalibration(QWidget):
    def __init__(self):
        super().__init__()
        self.stop_timer = False      # Initializes the stop timer flag to False
        self.init_ui()
    def init_ui(self):
        self.setWindowTitle("输入校准")
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setMinimumSize(305, 373)
        self.setMaximumSize(520, 500)
        self.standard_spl_flag = True
        self.recorded_flag = False

        standard_spl_box = self.create_standard_spl_box()
        recorded_box = self.create_recorded_box()
        deviation_spl_box = self.create_deviation_spl_box()

        layout = QVBoxLayout()
        layout.addWidget(standard_spl_box)
        layout.addWidget(recorded_box)
        layout.addWidget(deviation_spl_box)

        self.setLayout(layout)

    def create_deviation_spl_box(self):
        deviation_spl_box = QGroupBox("校准结果")
        deviation_label = QLabel("声压偏差：")
        self.deviation_lineedit = QLineEdit()
        self.deviation_lineedit.setStyleSheet("background-color: white;")
        self.deviation_lineedit.setDisabled(True)

        standard_deviation_layout = QHBoxLayout()
        h_spacer_deviation_center = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        standard_deviation_layout.addWidget(deviation_label)
        standard_deviation_layout.addItem(h_spacer_deviation_center)
        standard_deviation_layout.addWidget(self.deviation_lineedit)
        deviation_spl_box.setLayout(standard_deviation_layout)

        return deviation_spl_box

    def create_recorded_box(self):
        recorded_box = QGroupBox("录制音频")
        recorded_label = QLabel("录制时间：")
        self.recorded_label = QLabel()
        self.recorded_label.setFixedSize(70, 30)
        self.recorded_label.setAlignment(Qt.AlignCenter)
        self.recorded_time = 10
        self.recorded_label.setText(f"<span style='color: red;'>{self.recorded_time} </span>"
                                    f"<span style='color: black;'>s</span>")

        self.recorded_label.setStyleSheet("background-color: white;"
                                          "border: 1px solid rgb(122, 122, 122);"
                                          "border-radius: 3px;")

        recorded_layout = QHBoxLayout()
        h_spacer_deviation_center = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        recorded_layout.addWidget(recorded_label)
        recorded_layout.addItem(h_spacer_deviation_center)
        recorded_layout.addWidget(self.recorded_label)
        recorded_box.setLayout(recorded_layout)

        return recorded_box

    def create_standard_spl_box(self):
        standard_spl_box = QGroupBox("标准声压")

        self.standard_spl_i = QRadioButton("94  dB")
        self.standard_spl_ii = QRadioButton("114 dB")
        self.standard_spl_i.clicked.connect(self.set_standard_spl)
        self.standard_spl_ii.clicked.connect(self.set_standard_spl)
        self.standard_spl_i.setChecked(True)

        h_spacer_standard_center = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        standard_spl_layout = QHBoxLayout()
        standard_spl_layout.addWidget(self.standard_spl_i)
        standard_spl_layout.addItem(h_spacer_standard_center)
        standard_spl_layout.addWidget(self.standard_spl_ii)
        standard_spl_layout.setContentsMargins(30, 0, 30, 0)
        standard_spl_box.setLayout(standard_spl_layout)

        return standard_spl_box

    def set_standard_spl(self):
        if self.standard_spl_i.isChecked():
            self.standard_spl_flag = True
        elif self.standard_spl_ii.isChecked():
            self.standard_spl_flag = False

    def clicked_calibration(self):
        prolong = 1
        recorded_dict = {"channels": 1,
                         "sample_rate": 44100,
                         "num_frames": 10 * 44100,
                         "prolong_frames": int(prolong * 44100)
                         }

        with futures.ThreadPoolExecutor(max_workers=1) as executor:
            recorded_thread = executor.submit(self.calculate_average_spl, recorded_dict)
            self.update_recorded_time()

        self.average_value = recorded_thread.result()
        deviation_value = self.calculate_deviation(self.average_value)
        self.deviation_lineedit.setText(str(deviation_value))
        if not self.stop_timer:
            if str(deviation_value) == "inf":
                self.calibration_popup(success_flag=False)
            else:
                self.calibration_popup(success_flag=True)
                self.save_deviation_value_to_text(deviation_value)

    def calibration_popup(self, success_flag=True):
        cal_msg = QMessageBox(self)
        if success_flag:
            cal_msg.setIcon(QMessageBox.Information)
            cal_msg.setText("校准成功")
            cal_msg.setWindowTitle("校准成功")
        else:
            cal_msg.setIcon(QMessageBox.Critical)
            cal_msg.setText("校准失败，请重试")
            cal_msg.setWindowTitle("校准失败")
        cal_msg.setStandardButtons(QMessageBox.Ok)
        cal_msg.exec_()

    def calculate_average_spl(self, recorded_dict):
        rec_code, recorded_data = SoundcardAudioProcessor().sd_rec(recorded_dict)
        step = 100
        if rec_code == error_code.OK:
            spl_smooth = AudioThdFrequencyResponseAnalysis().spl_calculation(recorded_data)
            spl_smooth_mid = len(spl_smooth) // 2
            spl_smooth_start = spl_smooth_mid - step
            spl_smooth_end = spl_smooth_mid + step
            spl_sample = spl_smooth[spl_smooth_start:spl_smooth_end]
            self.average_value = np.sum(spl_sample) / (step * 2)
            return self.average_value

    def update_recorded_time(self):
        while self.recorded_time > 0 and not self.stop_timer:
            time.sleep(1)
            self.recorded_time -= 1
            # Update the time display on the interface, showing the remaining time in red and the unit "s" in black.
            self.recorded_label.setText(f"<span style='color: red;'>{self.recorded_time} </span>"
                                        f"<span style='color: black;'>s</span>")
            QApplication.processEvents()

    def calculate_deviation(self, average_value):
        if self.standard_spl_flag:
            deviation_value = round(94 - average_value, 3)
        else:
            deviation_value = round(114 - average_value, 3)
        return deviation_value

    @staticmethod
    def save_deviation_value_to_text(deviation_value):
        dir_path = 'D:/gqgit/new_project/ui/ui_config/'
        file_path = dir_path + "mic_calibration.txt"
        current_time = datetime.now().strftime("%Y-%m-%d")
        with open(file_path, 'w') as f:
            f.write(f"deviation_value: \n{deviation_value}\n")
            f.write(f"Datetime: \n{current_time}\n")

    def reset_btn_clicked(self):
        self.recorded_time = 10
        self.recorded_label.setText(f"<span style='color: red;'>{self.recorded_time} </span>"
                                    f"<span style='color: black;'>s</span>")
        self.deviation_lineedit.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalibrationWindow()
    window.show()
    window.exec()

