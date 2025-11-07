import os
import sys
import json
import shutil
from dataclasses import dataclass
from typing import List, Optional, Tuple, Callable

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QRegularExpressionValidator
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)
from PyQt5.QtCore import QRegularExpression
from consts.running_consts import DEFAULT_DIR
from consts import model_consts


# ========================= Model 层 ========================= #


@dataclass
class ModelItem:
    model_name: str
    input_dim: str  # 形如 "176400 x 1"
    model_path: str
    config_path: str = ""
    copied_from_source: Optional[str] = None  # 仅“复制模型”产生：源模型文件路径
    copied_dest_dir: Optional[str] = None     # 仅“复制模型”产生：目标保存目录
    registered_from_file: bool = False        # 仅“注册模型”产生：是否来自文件注册


class AIModelsRepository:
    """
    负责：
    - 从 JSON 加载与保存模型数据
    - 管理内存中的模型列表与选中项
    - 兼容多种 JSON 结构与键名
    """

    def __init__(self, json_path: str) -> None:
        self.json_path = json_path
        self.models: List[ModelItem] = []
        self.selected_index: Optional[int] = None
        # 保存原始 JSON 结构信息，用于写回时尽量保持兼容
        self._loaded_container: str = "models_key"  # "list" 或 "models_key"
        self._key_style: str = "name_path"  # "name_path" 或 "model_name_model_path"

    # -------- JSON 读写 -------- #
    def load(self) -> None:
        if not os.path.exists(self.json_path):
            self.models = []
            return
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self.models = []
            return

        raw_list: Optional[List[dict]] = None
        if isinstance(data, list):
            raw_list = data
            self._loaded_container = "list"
        elif isinstance(data, dict) and isinstance(data.get("models"), list):
            raw_list = data.get("models")
            self._loaded_container = "models_key"

        if raw_list is None:
            self.models = []
            return

        parsed: List[ModelItem] = []
        key_style_detected = None
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            if {"name", "input_dim"}.issubset(item.keys()):
                key_style_detected = "name_path"
                parsed.append(
                    ModelItem(
                        model_name=str(item.get("name", "")),
                        input_dim=str(item.get("input_dim", "")),
                        model_path=str(item.get("path", "")),
                        config_path=str(item.get("config_path", "")),
                    )
                )
                continue
            if {"model_name", "input_dim"}.issubset(item.keys()):
                key_style_detected = "model_name_model_path"
                parsed.append(
                    ModelItem(
                        model_name=str(item.get("model_name", "")),
                        input_dim=str(item.get("input_dim", "")),
                        model_path=str(item.get("model_path", "")),
                        config_path=str(item.get("config_path", "")),
                    )
                )
                continue

        self.models = parsed
        if key_style_detected is not None:
            self._key_style = key_style_detected

    def save(self) -> Tuple[bool, str]:
        """
        将当前内存数据写回 JSON。
        - 优先保持原结构；若无原结构，则写为 {"models": [...]} 且键名使用 name/input_dim/path。
        返回: (success, message)
        """
        serializable: List[dict] = []
        # 保存时不包含临时字段（created_*）
        if self._key_style == "model_name_model_path":
            serializable = [
                {
                    "model_name": m.model_name,
                    "input_dim": m.input_dim,
                    "model_path": m.model_path,
                    "config_path": m.config_path,
                }
                for m in self.models
            ]
        else:
            serializable = [
                {
                    "name": m.model_name,
                    "input_dim": m.input_dim,
                    "path": m.model_path,
                    "config_path": m.config_path,
                }
                for m in self.models
            ]

        out_data = serializable if self._loaded_container == "list" else {"models": serializable}

        try:
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(out_data, f, ensure_ascii=False, indent=4)
            return True, ""
        except Exception as exc:  # pragma: no cover
            return False, str(exc)

    # -------- 管理操作 -------- #
    def add_model(self, item: ModelItem) -> int:
        self.models.append(item)
        return len(self.models) - 1

    def delete_model(self, index: int) -> bool:
        if 0 <= index < len(self.models):
            del self.models[index]
            # 调整选中索引
            if self.selected_index == index:
                self.selected_index = None
            elif self.selected_index is not None and self.selected_index > index:
                self.selected_index -= 1
            return True
        return False

    def set_selected_index(self, index: Optional[int]) -> None:
        self.selected_index = index

    def get_selected_index(self) -> Optional[int]:
        return self.selected_index


# ========================= View 层 ========================= #


class ModelEditDialog(QDialog):
    """
    通用对话框：用于“复制模型”与“注册模型”。
    - mode == "copy": 选择保存目录
    - mode == "register": 选择已有模型文件
    """

    def __init__(self, mode: str, parent: Optional[QWidget] = None, initial_dim: Optional[str] = None, lock_dim: bool = False, initial_config_path: Optional[str] = None, lock_config: bool = False) -> None:
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle("复制模型" if mode == "copy" else "注册模型")
        self.setModal(True)
        self._name_exists_checker: Optional[Callable[[str], bool]] = None
        # 项目根目录，使用 DEFAULT_DIR
        self._project_root = os.path.normpath(DEFAULT_DIR)

        name_label = QLabel("模型名称")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：MyModel")

        dim_label = QLabel("维    度")
        self.dim_a_edit = QLineEdit()
        self.dim_a_edit.setPlaceholderText("176400")
        self.dim_a_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\s*\d+\s*$")))
        self.dim_a_edit.setText("176400")
        x_label = QLabel(" x ")
        self.dim_b_edit = QLineEdit()
        self.dim_b_edit.setPlaceholderText("1")
        self.dim_b_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\s*\d+\s*$")))
        self.dim_b_edit.setText("1")

        # 配置路径（下拉选择 .yml/.yaml）
        config_label = QLabel("模型配置")
        self.config_combo = QComboBox()
        self._config_options = self._load_config_options()
        for rel_path in self._config_options:
            self.config_combo.addItem(os.path.basename(rel_path), rel_path)

        # 若提供初始维度则解析并填入
        if initial_dim:
            try:
                parts = [p.strip() for p in initial_dim.replace("×", "x").split("x")]
                if len(parts) >= 2:
                    a_digits = "".join(ch for ch in parts[0] if ch.isdigit())
                    b_digits = "".join(ch for ch in parts[1] if ch.isdigit())
                    if a_digits:
                        self.dim_a_edit.setText(str(int(a_digits)))
                    if b_digits:
                        self.dim_b_edit.setText(str(int(b_digits)))
            except Exception:
                pass

        # 复制模式下可选锁定维度，禁止修改且置灰显示
        if lock_dim:
            self.dim_a_edit.setReadOnly(True)
            self.dim_b_edit.setReadOnly(True)
            self.dim_a_edit.setEnabled(False)
            self.dim_b_edit.setEnabled(False)

        # 配置路径初始化与锁定
        if initial_config_path:
            self._select_config(initial_config_path)
        if lock_config:
            self.config_combo.setEnabled(False)

        path_label = QLabel("保存目录" if mode == "copy" else "模型路径")
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._on_browse_model)

        form_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.addWidget(name_label)
        row1.addWidget(self.name_edit)
        row2 = QHBoxLayout()
        row2.addWidget(dim_label)
        row2.addWidget(self.dim_a_edit)
        row2.addWidget(x_label)
        row2.addWidget(self.dim_b_edit)
        row3 = QHBoxLayout()
        row3.addWidget(config_label)
        row3.addWidget(self.config_combo)
        row4 = QHBoxLayout()
        row4.addWidget(path_label)
        row4.addWidget(self.path_edit)
        row4.addWidget(browse_btn)
        form_layout.addLayout(row1)
        form_layout.addLayout(row2)
        form_layout.addLayout(row3)
        form_layout.addLayout(row4)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("确定")
        self.button_box.button(QDialogButtonBox.Cancel).setText("取消")
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        root = QVBoxLayout()
        root.addLayout(form_layout)
        root.addWidget(self.button_box)
        self.setLayout(root)

        self._accepted: bool = False

    def set_name_exists_checker(self, checker: Optional[Callable[[str], bool]]) -> None:
        self._name_exists_checker = checker

    def _on_browse_model(self) -> None:
        if self.mode == "copy":
            directory = QFileDialog.getExistingDirectory(self, "选择保存目录", os.getcwd())
            if directory:
                self.path_edit.setText(directory)
        else:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择模型文件", os.getcwd(), "所有文件 (*.*)")
            if file_path:
                self.path_edit.setText(file_path)
                # 自动将文件名（不含扩展名）填入模型名称
                base = os.path.basename(file_path)
                name_without_ext = os.path.splitext(base)[0]
                if not self.name_edit.text().strip():
                    self.name_edit.setText(name_without_ext)

    def _load_config_options(self) -> List[str]:
        base = model_consts.CONFIG_PATH
        try:
            if not os.path.isabs(base):
                base_abs = os.path.normpath(os.path.join(self._project_root, base))
            else:
                base_abs = os.path.normpath(base)
            config_dir = os.path.dirname(base_abs)
            result: List[str] = []
            for fname in os.listdir(config_dir):
                if fname.lower().endswith((".yml", ".yaml")):
                    abs_path = os.path.join(config_dir, fname)
                    rel = os.path.relpath(abs_path, self._project_root).replace("\\", "/")
                    result.append(rel)
            result.sort()
            return result
        except Exception:
            return []

    def _select_config(self, path: str) -> None:
        try:
            norm = os.path.normpath(path)
            try:
                common = os.path.commonpath([norm, self._project_root])
            except Exception:
                common = None
            if common and common == self._project_root:
                rel = os.path.relpath(norm, self._project_root).replace("\\", "/")
            else:
                rel = path.replace("\\", "/")
            base = os.path.basename(rel)
            # 优先匹配 userData（相对路径），其次匹配文件名
            for i in range(self.config_combo.count()):
                data = self.config_combo.itemData(i)
                text = self.config_combo.itemText(i)
                if data == rel or text == base:
                    self.config_combo.setCurrentIndex(i)
                    return
        except Exception:
            pass

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        a_text = self.dim_a_edit.text().strip()
        b_text = self.dim_b_edit.text().strip()
        path_text = self.path_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "提示", "请填写模型名")
            return
        if not a_text or not QRegularExpression(r"^\s*\d+\s*$").match(a_text).hasMatch():
            QMessageBox.warning(self, "提示", "维度前项应为正整数，例如 176400")
            return
        if not b_text or not QRegularExpression(r"^\s*\d+\s*$").match(b_text).hasMatch():
            QMessageBox.warning(self, "提示", "维度后项应为正整数，例如 1")
            return
        if not path_text:
            QMessageBox.warning(self, "提示", "请选择路径")
            return

        # 名称唯一性校验：若重复，则仅提示并保持对话框打开
        if self._name_exists_checker is not None:
            try:
                if self._name_exists_checker(name):
                    QMessageBox.warning(self, "提示", "模型名称已存在，请更换名称")
                    return
            except Exception:
                # 忽略外部校验器异常，以免影响基本流程
                pass

        self._accepted = True
        self.accept()

    def get_values(self) -> Tuple[str, str, str, str]:
        a_text = self.dim_a_edit.text().strip()
        b_text = self.dim_b_edit.text().strip()
        a_digits = "".join(ch for ch in a_text if ch.isdigit()) or "0"
        b_digits = "".join(ch for ch in b_text if ch.isdigit()) or "0"
        dim = f"{int(a_digits)} x {int(b_digits)}"
        cfg = self.config_combo.currentData() or ""
        return self.name_edit.text().strip(), dim, self.path_edit.text().strip(), cfg


class ModelManagerView(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI 模型管理")
        self.setModal(True)
        # 图标可按需设置
        icon_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../ui_pic/logo_pic/ting.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 表格
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["选择", "模型名", "维度", "配置", "模型路径"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 按钮
        self.btn_new = QPushButton("复制模型")
        self.btn_register = QPushButton("注册模型")
        self.btn_delete = QPushButton("删除模型")
        self.btn_confirm = QPushButton("确认")
        self.btn_cancel = QPushButton("取消")

        # 底部布局：左三右二，中间留白
        left_layout = QHBoxLayout()
        left_layout.addWidget(self.btn_new)
        left_layout.addWidget(self.btn_register)
        left_layout.addWidget(self.btn_delete)

        right_layout = QHBoxLayout()
        right_layout.addWidget(self.btn_confirm)
        right_layout.addWidget(self.btn_cancel)

        bottom = QHBoxLayout()
        # bottom.addStretch(1)
        bottom.addLayout(left_layout)
        bottom.addStretch(2)
        bottom.addLayout(right_layout)
        # bottom.addStretch(1)

        root = QVBoxLayout()
        root.addWidget(self.table)
        root.addLayout(bottom)
        self.setLayout(root)

    # -------- View helpers -------- #
    def clear_table(self) -> None:
        self.table.setRowCount(0)

    def add_row(self, item: ModelItem, checked: bool = False) -> int:
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 0: 选择（CheckBox 单选）
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        self.table.setCellWidget(row, 0, checkbox)

        # 1: 模型名
        self.table.setItem(row, 1, QTableWidgetItem(item.model_name))
        # 2: 维度
        self.table.setItem(row, 2, QTableWidgetItem(item.input_dim))
        # 3: 配置（仅文件名）
        config_name = os.path.basename(item.config_path) if item.config_path else ""
        self.table.setItem(row, 3, QTableWidgetItem(config_name))
        # 4: 路径
        self.table.setItem(row, 4, QTableWidgetItem(item.model_path))

        return row

    def remove_row(self, row: int) -> None:
        if 0 <= row < self.table.rowCount():
            self.table.removeRow(row)

    def set_row_checked_exclusive(self, row_to_check: Optional[int]) -> None:
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, 0)
            if isinstance(w, QCheckBox):
                w.blockSignals(True)
                w.setChecked(r == row_to_check)
                w.blockSignals(False)

    def get_row_checkbox(self, row: int) -> Optional[QCheckBox]:
        w = self.table.cellWidget(row, 0)
        return w if isinstance(w, QCheckBox) else None

    def show_info(self, text: str) -> None:
        QMessageBox.information(self, "提示", text)

    def show_warning(self, text: str) -> None:
        QMessageBox.warning(self, "提示", text)


# ========================= Controller 层 ========================= #


class ModelManagerController:
    def __init__(self, repo: AIModelsRepository, view: ModelManagerView) -> None:
        self.repo = repo
        self.view = view

        # 初始化表格
        self._init_table()

        # 绑定事件
        self.view.btn_new.clicked.connect(self.on_copy_model)
        self.view.btn_register.clicked.connect(self.on_register_model)
        self.view.btn_delete.clicked.connect(self.on_delete_model)
        self.view.btn_confirm.clicked.connect(self.on_confirm)
        self.view.btn_cancel.clicked.connect(self.on_cancel)

    # -------- 初始化与刷新 -------- #
    def _init_table(self) -> None:
        self.view.clear_table()
        for idx, m in enumerate(self.repo.models):
            row = self.view.add_row(m, checked=(idx == (self.repo.get_selected_index() or -1)))
            checkbox = self.view.get_row_checkbox(row)
            if checkbox is not None:
                checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(r, state))

    def _append_table_row(self, item: ModelItem, select_new: bool = False) -> None:
        row = self.view.add_row(item, checked=select_new)
        checkbox = self.view.get_row_checkbox(row)
        if checkbox is not None:
            checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(r, state))
        if select_new:
            self.repo.set_selected_index(row)
            self.view.set_row_checked_exclusive(row)

    def _clear_all_selection(self) -> None:
        self.repo.set_selected_index(None)
        self.view.set_row_checked_exclusive(None)

    def _current_selected_row(self) -> Optional[int]:
        # 依据复选框状态判断
        for r in range(self.view.table.rowCount()):
            w = self.view.get_row_checkbox(r)
            if w is not None and w.isChecked():
                return r
        return None

    def _is_duplicate_name(self, name: str) -> bool:
        target = name.strip().lower()
        for m in self.repo.models:
            if m.model_name.strip().lower() == target:
                return True
        return False

    # -------- 事件处理 -------- #
    def on_checkbox_changed(self, row: int, state: int) -> None:
        if state == Qt.Checked:
            self.repo.set_selected_index(row)
            self.view.set_row_checked_exclusive(row)
        else:
            # 若取消勾选当前项，清空选中
            if self.repo.get_selected_index() == row:
                self.repo.set_selected_index(None)

    def on_copy_model(self) -> None:
        src_row = self._current_selected_row()
        if src_row is None:
            self.view.show_warning("请先勾选一个现有模型作为复制的源模型")
            return
        source_path = self.view.table.item(src_row, 4).text().strip()
        if not source_path or not os.path.exists(source_path):
            self.view.show_warning("选中模型的源文件不存在，无法复制")
            return

        # 复制模式：维度使用被勾选模型的维度，且禁止修改
        initial_dim = self.view.table.item(src_row, 2).text().strip()
        # 从表格“配置”列（索引3）拿到文件名，再从repo中取全路径
        config_name_item = self.view.table.item(src_row, 3)
        initial_config = ""
        if config_name_item is not None:
            # 在 repo 中以模型名匹配找到完整 config_path
            model_name = self.view.table.item(src_row, 1).text().strip()
            for m in self.repo.models:
                if m.model_name == model_name:
                    initial_config = m.config_path
                    break
        dlg = ModelEditDialog(mode="copy", parent=self.view, initial_dim=initial_dim, lock_dim=True, initial_config_path=initial_config, lock_config=True)
        dlg.set_name_exists_checker(lambda n: self._is_duplicate_name(n))
        if dlg.exec_() == QDialog.Accepted:
            name, dim, dest_dir, config_path = dlg.get_values()
            # 先用占位路径（确认时再复制文件），此处预估最终文件名
            ext = os.path.splitext(source_path)[1] or ".model"
            final_path = os.path.join(dest_dir, f"{name}{ext}")
            item = ModelItem(
                model_name=name,
                input_dim=dim,
                model_path=final_path,
                config_path=config_path,
                copied_from_source=source_path,
                copied_dest_dir=dest_dir,
            )
            self.repo.add_model(item)
            self._append_table_row(item, select_new=False)
            self._clear_all_selection()

    def on_register_model(self) -> None:
        dlg = ModelEditDialog(mode="register", parent=self.view)
        dlg.set_name_exists_checker(lambda n: self._is_duplicate_name(n))
        if dlg.exec_() == QDialog.Accepted:
            name, dim, file_path, config_path = dlg.get_values()
            if not os.path.exists(file_path):
                self.view.show_warning("所选模型文件不存在")
                return
            item = ModelItem(model_name=name, input_dim=dim, model_path=file_path, config_path=config_path, registered_from_file=True)
            self.repo.add_model(item)
            self._append_table_row(item, select_new=False)

    def on_delete_model(self) -> None:
        row = self._current_selected_row()
        if row is None:
            self.view.show_warning("请先勾选要删除的模型")
            return
        ok = self.repo.delete_model(row)
        if ok:
            self.view.remove_row(row)
            # 维持单选排他性
            self.view.set_row_checked_exclusive(self.repo.get_selected_index())
            self._clear_all_selection()

    def on_confirm(self) -> None:
        # 先执行文件复制（针对“复制模型”产生的项）
        copy_errors: List[str] = []
        for m in self.repo.models:
            if m.copied_from_source and m.copied_dest_dir:
                ext = os.path.splitext(m.copied_from_source)[1] or ".model"
                final_path = os.path.join(m.copied_dest_dir, f"{m.model_name}{ext}")
                try:
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    shutil.copy2(m.copied_from_source, final_path)
                    m.model_path = final_path
                except Exception as exc:
                    copy_errors.append(f"复制失败: {m.model_name} -> {final_path} ({exc})")

        # 对于注册模型：若用户修改了名称，则在原目录复制一份为新名称
        for m in self.repo.models:
            if m.registered_from_file and m.model_path and os.path.exists(m.model_path):
                dir_name = os.path.dirname(m.model_path)
                src_base = os.path.splitext(os.path.basename(m.model_path))[0]
                ext = os.path.splitext(m.model_path)[1]
                target = os.path.join(dir_name, f"{m.model_name}{ext}")
                try:
                    if m.model_name and m.model_name != src_base:
                        os.makedirs(dir_name, exist_ok=True)
                        shutil.copy2(m.model_path, target)
                        m.model_path = target
                except Exception as exc:
                    copy_errors.append(f"复制失败: {m.model_path} -> {target} ({exc})")

        # 再保存 JSON
        ok, msg = self.repo.save()
        if not ok:
            self.view.show_warning(f"保存 JSON 失败：{msg}")
            return

        if copy_errors:
            QMessageBox.warning(self.view, "部分失败", "\n".join(copy_errors))

        self.view.accept()

    def on_cancel(self) -> None:
        self.view.reject()


# ========================= 应用入口 ========================= #


class ModelManagerApp:
    def __init__(self, json_path: Optional[str] = None) -> None:
        # 默认路径：ui/ui_config/models.json（相对本文件）
        if json_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.normpath(os.path.join(current_dir, "../ui_config/models.json"))
        self.repo = AIModelsRepository(json_path)
        self.repo.load()
        self.view = ModelManagerView()
        self.controller = ModelManagerController(self.repo, self.view)
        self.view.setWindowIcon(QIcon(DEFAULT_DIR + "ui/ui_pic/sys_ico/icon.ico"))

    def run(self) -> Tuple[int, List[dict]]:
        self.view.resize(800, 500)
        code = self.view.exec_()
        models_info = [
            {"model_name": m.model_name, "input_dim": m.input_dim, "model_path": m.model_path, "config_path": m.config_path}
            for m in self.repo.models
        ]
        return code, models_info


def main() -> None:
    app = QApplication(sys.argv)
    # 支持从命令行传入 JSON 路径；否则使用默认
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    manager = ModelManagerApp(json_path)
    code, models_info = manager.run()
    if code == QDialog.Accepted:
        try:
            print(json.dumps(models_info, ensure_ascii=False))
        except Exception:
            pass
    sys.exit(0 if code == QDialog.Accepted else 0)


if __name__ == "__main__":
    main()