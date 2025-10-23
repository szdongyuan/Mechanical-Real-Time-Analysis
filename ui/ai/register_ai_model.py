import json
import os
import sys
import shutil
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QCheckBox,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDialog,
)


def get_json_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "models.json")


class NewModelDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建模型")

        self.name_edit = QLineEdit(self)
        self.dim_spin = QSpinBox(self)
        self.dim_spin.setRange(1, 1_000_000)
        self.path_edit = QLineEdit(self)
        self.browse_btn = QPushButton("浏览…", self)
        self.browse_btn.clicked.connect(self.on_browse)

        form = QFormLayout()
        form.addRow("模型名", self.name_edit)
        form.addRow("维度", self.dim_spin)

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit)
        path_row.addWidget(self.browse_btn)
        form.addRow("保存目录", path_row)

        self.ok_btn = QPushButton("确定", self)
        self.cancel_btn = QPushButton("取消", self)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.ok_btn)
        btns.addWidget(self.cancel_btn)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addLayout(btns)

    def on_browse(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "选择保存目录", os.path.expanduser("~"))
        if dir_path:
            self.path_edit.setText(dir_path)

    def accept(self) -> None:  # type: ignore[override]
        name = self.name_edit.text().strip()
        dim = int(self.dim_spin.value())
        path = self.path_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "模型名不能为空")
            return
        if dim <= 0:
            QMessageBox.warning(self, "提示", "维度必须为正整数")
            return
        if not path:
            QMessageBox.warning(self, "提示", "保存目录不能为空")
            return
        super().accept()

    def get_data(self) -> Dict[str, object]:
        return {
            "model_name": self.name_edit.text().strip(),
            "input_dim": int(self.dim_spin.value()),
            "model_path": self.path_edit.text().strip(),
        }


class ModelManagerApp(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 模型管理")

        self.models: List[Dict[str, object]] = []
        self._load_models()
        self._build_ui()
        self._populate_table()

    # ---------- JSON 读写 ----------
    def _load_models(self) -> None:
        path = get_json_path()
        if not os.path.exists(path):
            self.models = []
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                # 仅保留需要的字段
                sanitized: List[Dict[str, object]] = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("model_name", "")).strip()
                    path_val = str(item.get("model_path", "")).strip()
                    try:
                        dim_val = int(item.get("input_dim", 0))
                    except Exception:
                        dim_val = 0
                    if name and path_val and dim_val > 0:
                        sanitized.append(
                            {
                                "model_name": name,
                                "input_dim": dim_val,
                                "model_path": path_val,
                            }
                        )
                self.models = sanitized
            else:
                self.models = []
        except Exception as exc:
            self.models = []
            QMessageBox.warning(self, "读取失败", f"解析 models.json 失败：{exc}")

    def _save_models(self) -> None:
        path = get_json_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.models, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", f"写入 models.json 失败：{exc}")

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["", "模型名", "维度", "模型路径"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.table.horizontalHeader()
        try:
            from PyQt5.QtWidgets import QHeaderView  # type: ignore

            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.Stretch)
        except Exception:
            pass

        # 左侧三个按钮
        self.btn_new = QPushButton("新建模型", self)
        self.btn_register = QPushButton("注册模型", self)
        self.btn_delete = QPushButton("删除模型", self)
        # 右侧两个按钮
        self.btn_ok = QPushButton("确认", self)
        self.btn_cancel = QPushButton("取消", self)

        self.btn_new.clicked.connect(self.on_new_model)
        self.btn_register.clicked.connect(self.on_register_model)
        self.btn_delete.clicked.connect(self.on_delete_model)
        self.btn_ok.clicked.connect(self.on_confirm)
        self.btn_cancel.clicked.connect(self.on_cancel)

        left_btns = QHBoxLayout()
        left_btns.addWidget(self.btn_new)
        left_btns.addWidget(self.btn_register)
        left_btns.addWidget(self.btn_delete)
        left_container = QWidget(self)
        left_container.setLayout(left_btns)

        right_btns = QHBoxLayout()
        right_btns.addWidget(self.btn_ok)
        right_btns.addWidget(self.btn_cancel)
        right_container = QWidget(self)
        right_container.setLayout(right_btns)

        bottom = QHBoxLayout()
        bottom.addWidget(left_container, 0, Qt.AlignLeft | Qt.AlignVCenter)
        bottom.addStretch(1)
        bottom.addWidget(right_container, 0, Qt.AlignRight | Qt.AlignVCenter)

        root = QVBoxLayout(self)
        root.addWidget(self.table)
        root.addLayout(bottom)

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self.models))
        for row, model in enumerate(self.models):
            # 1) 单选复选框
            checkbox = self._create_checkbox(row)
            container = QWidget(self.table)
            lay = QHBoxLayout(container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(checkbox, 0, Qt.AlignCenter)
            container.setLayout(lay)
            self.table.setCellWidget(row, 0, container)

            # 2) 模型名
            name_item = QTableWidgetItem(str(model.get("model_name", "")))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name_item)

            # 3) 维度
            dim_item = QTableWidgetItem(str(model.get("input_dim", "")))
            dim_item.setFlags(dim_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, dim_item)

            # 4) 路径
            path_item = QTableWidgetItem(str(model.get("model_path", "")))
            path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, path_item)

    # ---------- Helpers ----------
    def _create_checkbox(self, row: int) -> QCheckBox:
        cb = QCheckBox(self.table)
        cb.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(r, state))
        return cb

    def _get_checkbox(self, row: int) -> Optional[QCheckBox]:
        container = self.table.cellWidget(row, 0)
        if not isinstance(container, QWidget):
            return None
        return container.findChild(QCheckBox)

    def _selected_row(self) -> int:
        for r in range(self.table.rowCount()):
            cb = self._get_checkbox(r)
            if cb is not None and cb.isChecked():
                return r
        return -1

    # ---------- 事件 ----------
    def on_checkbox_changed(self, row: int, state: int) -> None:
        if state == Qt.Checked:
            for r in range(self.table.rowCount()):
                if r == row:
                    continue
                cb = self._get_checkbox(r)
                if cb is not None and cb.isChecked():
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)

    def on_new_model(self) -> None:
        # 必须先勾选一个现有模型作为复制来源
        src_idx = self._selected_row()
        if src_idx < 0:
            QMessageBox.information(self, "提示", "请先勾选一个模型作为模板")
            return

        src_model = self.models[src_idx]
        src_path = str(src_model.get("model_path", "")).strip()

        dlg = NewModelDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            # 读取输入
            name = dlg.name_edit.text().strip()
            dim = int(dlg.dim_spin.value())
            save_dir = dlg.path_edit.text().strip()

            if not os.path.isfile(src_path):
                QMessageBox.warning(self, "复制失败", f"源模型文件不存在：\n{src_path}")
                return

            # 目标路径（保留源扩展名）
            ext = os.path.splitext(src_path)[1]
            os.makedirs(save_dir, exist_ok=True)
            dest_path = os.path.join(save_dir, f"{name}{ext}")

            # 已存在时确认是否覆盖
            if os.path.exists(dest_path):
                ret = QMessageBox.question(
                    self,
                    "覆盖确认",
                    f"文件已存在：\n{dest_path}\n是否覆盖？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if ret != QMessageBox.Yes:
                    return

            try:
                shutil.copyfile(src_path, dest_path)
            except Exception as exc:
                QMessageBox.critical(self, "复制失败", f"复制文件时出错：{exc}")
                return

            # 添加到内存并刷新表格
            new_model = {
                "model_name": name,
                "input_dim": dim,
                "model_path": dest_path,
            }
            self.models.append(new_model)
            self._populate_table()

    def on_register_model(self) -> None:
        idx = self._selected_row()
        if idx < 0:
            QMessageBox.information(self, "提示", "请先勾选一个模型")
            return
        name = str(self.models[idx].get("model_name", ""))
        print(f"模型 {name} 已注册")
        QMessageBox.information(self, "注册", f"模型 {name} 已注册")

    def on_delete_model(self) -> None:
        idx = self._selected_row()
        if idx < 0:
            QMessageBox.information(self, "提示", "请先勾选一个模型")
            return
        del self.models[idx]
        self._populate_table()

    def on_confirm(self) -> None:
        self._save_models()
        QMessageBox.information(self, "已保存", "已保存到 models.json")

    def on_cancel(self) -> None:
        self._load_models()
        self._populate_table()


def main() -> None:
    app = QApplication(sys.argv)
    window = ModelManagerApp()
    window.resize(900, 520)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


