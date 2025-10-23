qpushbutton_stytle = """
            QPushButton {
                border-left: 1px solid rgb(128, 128, 128);
                border-top: 1px solid rgb(128, 128, 128);
                border-right: 3px solid rgb(128, 128, 128);
                border-bottom: 3px solid rgb(128, 128, 128);
                background-color: rgb(225, 225, 225);
                font-family: 'SimSun';
                font-size: 20px;
                border-radius: 3px;
                padding: 3px;
            }
            QPushButton:hover {
                background-color: #5099ccff;
                color: black;
                border-color: #803333ff;
            }
            QPushButton:pressed {
                background-color: #8099ccff;
                border-color: #3333ff;
            }
        """

qlineedit_stytle = """
            QLineEdit {
                border: 1px solid rgb(122, 122, 122);
                font-family: 'SimSun';
                font-size: 20px;
                border-radius: 3px;
                padding: 3px;
            }
            QLineEdit:disabled {
                background-color: #d3d3d3;
                color: #808080;
            }
        """

qcombobox_stytle = """
            QComboBox {
                background-color: rgb(255, 255, 255);
                border: None;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 12px;

                border: None;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: url(./ui/ui_pic/shanglajiantou.png);
                width: 12px;
                height: 12px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }
        """

login_qcombobox_stytle = """
            QComboBox {
                border: 1px solid rgb(122, 122, 122);
                background-color: rgb(255, 255, 255);
                font-size: 20px;
                border: None;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 12px;

                border: None;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: url(./ui/ui_pic/shanglajiantou.png);
                width: 12px;
                height: 12px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }
        """

qgroupbox_stytle = """
            QGroupBox {
                background: transparent;
                font-size: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: padding;
                subcontrol-position: top left;
                padding-left: 0px;
                padding-top: 0px;
                margin-top: 0px;
            }
        """

qdialog_stytle = """
            QDialog {
                border-radius: 20px;
            }
"""

qlabel_stytle = """
            QLabel {
                font-family: 'SimSun';
                font-size: 20px;
                color: black;
            }
"""

main_window_menubar_stytle = """
            QMenuBar {
                background-color:transparent;
                font-family: 'SimSun';
                font-size: 20px;
            }
            QMenu {
                font-family: 'SimSun';
                font-size: 20px;
            }
            QMenu::item {
                font-family: 'SimSun';
                font-size: 20px;
                padding-left: 30px;
                padding-right: 10px;
            }
            QMenu::item:selected {
                background-color: #8099ccff;
            }
"""

qframe_stytle = """
            QFrame {
                color: rgb(173, 173, 173);
            }
"""
hardware_qframe_stytle = """
            QFrame {
                color: rgb(204, 204, 204);
            }
"""

toolbar_button_stytle = """
            QPushButton {
                background-color: #4bb7f8;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #85cefa;;
            }
            QPushButton:pressed {
                background-color: #22a7f7;
            }
"""

qcheckbox_stytle = """
            QCheckBox {
                font-family: 'SimSun';
                font-size: 20px;
            }
"""

qlistview_stytle = """
            QListView {
                font-family: 'SimSun';
                font-size: 20px;
            }
"""

qradiobutton_stytle = """
            QRadioButton {
                font-family: 'SimSun';
                font-size: 20px;
            }
"""

qtabwidget_stytle = """
            QTabWidget {
                font-family: 'SimSun';
                font-size: 20px;
            }
"""

qtextedit_stytle = """                    
            QTextEdit{
                background-color: white;
                font-family: 'SimSun';
                font-size: 30px;
            }
             QTextEdit:disabled {
                color: rgb(0, 0, 0);
            }
"""
