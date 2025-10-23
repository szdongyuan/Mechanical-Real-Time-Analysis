"""
AI配置窗口使用示例
"""

import sys
import json
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel

# 假设这些是必要的导入
from ui.ai.ai_config_ui import AIConfigWindow

class ConfigManager:
    """配置管理器示例实现"""
    
    def __init__(self, config_file="ai_config.json"):
        self.config_file = config_file
        
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_default_config(self, model_type, config_data):
        """保存配置"""
        config = self.load_config()
        config[model_type] = config_data
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True

class MainWindow(QMainWindow):
    """主窗口示例"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("AI配置窗口使用示例")
        self.setGeometry(300, 300, 400, 200)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 创建打开AI配置窗口的按钮
        open_ai_config_btn = QPushButton("打开AI配置窗口")
        open_ai_config_btn.clicked.connect(self.open_ai_config)
        layout.addWidget(open_ai_config_btn)
        
        # 显示当前配置的标签
        self.config_label = QLabel("当前配置将显示在这里")
        layout.addWidget(self.config_label)
        
        # 初始化模型文件
        self.init_model_file()
        
    def init_model_file(self):
        """初始化示例模型文件"""
        models_data = {
            "models": [
                {"name": "CNN_mirror_chirp_002", "input_dim": "176400 x 1"},
                {"name": "RNN_model_001", "input_dim": "176400 x 1"},
                {"name": "Transformer_v2", "input_dim": "88200 x 1"}
            ]
        }
        
        with open("models.json", "w", encoding="utf-8") as f:
            json.dump(models_data, f, ensure_ascii=False, indent=4)
            
    def open_ai_config(self):
        """打开AI配置窗口"""
        # 创建AI配置窗口实例 (signal_len参数可选)
        ai_config_window = AIConfigWindow(self.config_manager, "AI", signal_len=176400)
        # ai_config_window = AIConfigWindow(self.config_manager, "AI", signal_len=88200)
        
        # 显示窗口并获取结果
        if ai_config_window.exec_() == AIConfigWindow.Accepted:
            config_data = ai_config_window.on_click_ok_btn()
            self.config_label.setText(f"选择的模型: {config_data['analyse_model_name']}")

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()