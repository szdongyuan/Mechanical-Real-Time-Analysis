import sys
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Protocol

import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets

# pyqtgraph 用于OpenGL渲染
import pyqtgraph as pg
import pyqtgraph.opengl as gl


from consts.running_consts import DEFAULT_DIR


# -----------------------------
# Model 层
# -----------------------------

@dataclass
class MeshData:
    vertices: np.ndarray  # (N, 3) float64
    faces: np.ndarray     # (M, 3) int32/64

    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.vertices.size == 0:
            return np.zeros(3), np.zeros(3)
        vmin = self.vertices.min(axis=0)
        vmax = self.vertices.max(axis=0)
        return vmin, vmax


class MeshLoader(Protocol):
    def load(self, file_path: str) -> MeshData:
        ...


class GmshStepLoader:
    """使用 gmsh 读取 STEP 并三角化为网格。
    不依赖 pythonocc。
    """

    def load(self, file_path: str) -> MeshData:
        try:
            import gmsh  # type: ignore
        except Exception as exc:  # pragma: no cover - 依赖环境
            raise RuntimeError(
                "未安装 gmsh。请先安装：pip install gmsh"
            ) from exc

        gmsh.initialize()
        try:
            gmsh.model.add("step_model")
            # 导入STEP几何（基于OpenCASCADE内核）
            # gmsh 4.x: importShapes 支持STEP/IGES/BREP
            gmsh.model.occ.importShapes(file_path)
            gmsh.model.occ.synchronize()

            # 生成曲面三角网格（2维面片用于可视化）
            # 依据几何包围盒自适应网格尺寸，避免 lc=0 错误
            try:
                xmin = ymin = zmin = float("inf")
                xmax = ymax = zmax = float("-inf")
                for dim in (0, 1, 2, 3):
                    for d, tag in gmsh.model.getEntities(dim):
                        bxmin, bymin, bzmin, bxmax, bymax, bzmax = gmsh.model.occ.getBoundingBox(d, tag)
                        xmin, ymin, zmin = min(xmin, bxmin), min(ymin, bymin), min(zmin, bzmin)
                        xmax, ymax, zmax = max(xmax, bxmax), max(ymax, bymax), max(zmax, bzmax)

                span = math.sqrt(max((xmax - xmin), 0.0) ** 2 +
                                  max((ymax - ymin), 0.0) ** 2 +
                                  max((zmax - zmin), 0.0) ** 2)
                if not math.isfinite(span) or span <= 0.0:
                    span = 1.0

                base = span / 80.0
                min_lc = max(base / 2.0, span / 2000.0)
                max_lc = max(base * 2.0, min_lc * 1.2)
                gmsh.option.setNumber("Mesh.CharacteristicLengthMin", float(min_lc))
                gmsh.option.setNumber("Mesh.CharacteristicLengthMax", float(max_lc))
                gmsh.option.setNumber("Mesh.CharacteristicLengthFromCurvature", 1)
            except Exception:
                # 回退到默认网格设置
                pass

            gmsh.model.mesh.generate(2)

            # 读取节点
            node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
            if node_coords is None or len(node_coords) == 0:
                raise RuntimeError("STEP 网格为空，无法渲染")
            vertices = np.array(node_coords, dtype=np.float64).reshape(-1, 3)

            # 读取面要素（三角形），维度=2
            # 可能存在多种元素类型，提取所有三角形（type=2）
            element_types, element_tags, element_node_tags = gmsh.model.mesh.getElements(2)

            # 建立 node_tag -> 索引 的映射
            tag_to_index = {int(t): i for i, t in enumerate(node_tags.tolist())}

            faces_list: List[np.ndarray] = []
            for etype, enodes in zip(element_types, element_node_tags):
                # 2: 3-node triangle; 9: 6-node triangle 等
                if etype == 2:  # 仅使用线性三角形
                    tri_nodes = np.array(enodes, dtype=np.int64).reshape(-1, 3)
                    # 将 gmsh 的节点 tag 转换为 0-based 索引
                    idx_tri = np.vectorize(lambda t: tag_to_index[int(t)])(tri_nodes)
                    faces_list.append(idx_tri.astype(np.int64))
                else:
                    # 对于高阶单元，取其前3个顶点近似显示
                    # 以保证通用性，同时保持开闭原则，可扩展新的处理器
                    tri_nodes = np.array(enodes, dtype=np.int64).reshape(-1, -1)
                    if tri_nodes.shape[1] >= 3:
                        approx = tri_nodes[:, :3]
                        idx_tri = np.vectorize(lambda t: tag_to_index[int(t)])(approx)
                        faces_list.append(idx_tri.astype(np.int64))

            if not faces_list:
                raise RuntimeError("未发现可用于显示的三角网格")

            faces = np.vstack(faces_list)
            return MeshData(vertices=vertices, faces=faces)
        finally:
            gmsh.finalize()


class MeshModel:
    """网格与交互状态。"""

    def __init__(self, mesh_loader: MeshLoader) -> None:
        self.mesh_loader = mesh_loader
        self.mesh: Optional[MeshData] = None
        # 视角状态：以相机绕模型旋转的方式实现
        self.azimuth_deg: float = 45.0
        self.elevation_deg: float = 20.0
        self.distance: float = 10.0

    def load_from(self, file_path: str) -> None:
        self.mesh = self.mesh_loader.load(file_path)
        vmin, vmax = self.mesh.bounds()
        diag = float(np.linalg.norm(vmax - vmin))
        if diag <= 1e-9:
            diag = 1.0
        # 初始相机距离按对角线长度设置
        self.distance = diag * 1.5


# -----------------------------
# View 层
# -----------------------------

class MeshView(gl.GLViewWidget):
    """负责渲染（着色 + 描边）。不直接处理业务逻辑。"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setBackgroundColor((40, 44, 45))

        # 内容项
        self.mesh_item: Optional[gl.GLMeshItem] = None
        self.edge_item: Optional[gl.GLLinePlotItem] = None

        # 记录拖拽状态
        self._dragging: bool = False
        self._drag_btn: Optional[QtCore.Qt.MouseButton] = None
        self._last_pos: Optional[QtCore.QPoint] = None

        # 绑定的模型对象，用于获取/更新视角状态
        self.model: Optional[MeshModel] = None

    # ---- 显示与更新 ----
    def set_model(self, model: MeshModel) -> None:
        self.model = model
        if not model.mesh:
            return

        vertices = model.mesh.vertices
        faces = model.mesh.faces

        # 构建MeshData并着色显示（标准着色，显式设置零件颜色）
        md = gl.MeshData(vertexes=vertices, faces=faces)
        # mesh_item = gl.GLMeshItem(
        #     meshdata=md,
        #     smooth=True,
        #     shader='balloon',
        #     color=(140/255.0, 149/255.0, 159/255.0, 1.0),
        # )
        mesh_item = gl.GLMeshItem(
            meshdata=md,
            smooth=True,
            shader='shaded',
            color=(140/255.0, 149/255.0, 159/255.0, 1.0),
        )
        mesh_item.setGLOptions('opaque')

        # 生成边线（按端点对绘制线段：0-1, 2-3, ...）
        edges_pos = self._build_edges(vertices, faces)
        # edge_item = gl.GLLinePlotItem(pos=edges_pos, color=(0, 0, 0, 1), width=2.0, mode='lines', antialias=True)
        edge_item = gl.GLLinePlotItem(pos=edges_pos, color=(0, 0, 0, 1), width=2.0, mode='lines')

        # 清理旧项并添加
        if self.mesh_item:
            self.removeItem(self.mesh_item)
        if self.edge_item:
            self.removeItem(self.edge_item)

        self.mesh_item = mesh_item
        self.edge_item = edge_item
        self.addItem(self.mesh_item)
        self.addItem(self.edge_item)

        # 自适应居中与距离
        self._fit_view_to_model()

    def _fit_view_to_model(self) -> None:
        if not self.model or not self.model.mesh:
            return
        vmin, vmax = self.model.mesh.bounds()
        center = (vmin + vmax) * 0.5
        diag = float(np.linalg.norm(vmax - vmin))
        if diag <= 1e-9:
            diag = 1.0

        self.opts['center'] = pg.Vector(center[0], center[1], center[2])
        self.model.distance = diag * 1.5
        self._apply_camera_from_model()

    def _apply_camera_from_model(self) -> None:
        if not self.model:
            return
        self.opts['azimuth'] = self.model.azimuth_deg
        self.opts['elevation'] = self.model.elevation_deg
        self.opts['distance'] = self.model.distance
        self.update()

    # ---- 模型绕坐标轴旋转辅助 ----
    def rotate_model_around_axis(self, angle_deg: float, x: float, y: float, z: float) -> None:
        """
        让模型绕指定轴旋转（右手坐标系，角度制）。
        说明：
            - 只改变模型自身的变换，不影响相机的 azimuth/elevation
            - 同步旋转 mesh 本体与边线
        """
        if self.mesh_item is None:
            return

        self.mesh_item.rotate(angle_deg, x, y, z)
        if self.edge_item is not None:
            self.edge_item.rotate(angle_deg, x, y, z)

    def rotate_model_around_y(self, angle_deg: float) -> None:
        """让模型绕世界坐标系的 Y 轴旋转（右手坐标系，角度制）。"""
        self.rotate_model_around_axis(angle_deg, 0, 1, 0)

    @staticmethod
    def _build_edges(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
        """从三角面提取无向唯一边，返回按端点对展开的顶点数组。"""
        edge_set = set()
        for tri in faces:
            i, j, k = int(tri[0]), int(tri[1]), int(tri[2])
            e1 = (min(i, j), max(i, j))
            e2 = (min(j, k), max(j, k))
            e3 = (min(k, i), max(k, i))
            edge_set.add(e1)
            edge_set.add(e2)
            edge_set.add(e3)

        edges = sorted(list(edge_set))
        # 为GLLinePlotItem准备：将所有端点平铺，按 pairs 连接（0-1,2-3,...）
        pos_list: List[np.ndarray] = []
        for a, b in edges:
            pos_list.append(vertices[a])
            pos_list.append(vertices[b])

        pos = np.array(pos_list, dtype=np.float64).reshape(-1, 3)
        # 将边线顶点相对模型中心轻微外扩，避免与面片深度冲突，确保轮廓始终可见
        if vertices.size > 0:
            vmin = vertices.min(axis=0)
            vmax = vertices.max(axis=0)
            center = (vmin + vmax) * 0.5
            # 轻微外扩比例（足够避免Z冲突，又不致明显偏移）
            scale = 1.002
            pos = center + (pos - center) * scale
        return pos

    @staticmethod
    def _compute_four_dir_lit_colors(
        vertices: np.ndarray,
        faces: np.ndarray,
        base_color: Tuple[float, float, float] = (0.92, 0.95, 1.0),
        ambient: float = 0.35,
    ) -> np.ndarray:
        """计算四向方向光(±X, ±Y) + 环境光的每顶点颜色。
        说明：此为简化顶点级漫反射，光照不随相机旋转变化。
        """
        num_vertices = vertices.shape[0]
        normals = np.zeros((num_vertices, 3), dtype=np.float64)

        # 按面累加法线（未归一化），然后对每个顶点归一化
        for tri in faces:
            i, j, k = int(tri[0]), int(tri[1]), int(tri[2])
            v0 = vertices[i]
            v1 = vertices[j]
            v2 = vertices[k]
            n = np.cross(v1 - v0, v2 - v0)
            nn = np.linalg.norm(n)
            if nn > 1e-12:
                n = n / nn
            normals[i] += n
            normals[j] += n
            normals[k] += n

        # 顶点法线归一化
        norms = np.linalg.norm(normals, axis=1)
        norms[norms < 1e-12] = 1.0
        normals = normals / norms[:, None]

        # 四个方向光（世界坐标）：左右/上下
        light_dirs = np.array([
            [1.0, 0.0, 0.0],   # +X 右
            [-1.0, 0.0, 0.0],  # -X 左
            [0.0, 1.0, 0.0],   # +Y 上
            [0.0, -1.0, 0.0],  # -Y 下
        ], dtype=np.float64)
        # 归一化（虽然是单位向量，但保持健壮性）
        light_dirs = light_dirs / np.linalg.norm(light_dirs, axis=1)[:, None]

        # 计算漫反射累计项
        diffuse = np.zeros(num_vertices, dtype=np.float64)
        for ld in light_dirs:
            # dot(n, l) 取非负
            dl = np.einsum('ij,j->i', normals, ld)
            diffuse += np.maximum(dl, 0.0)

        # 归一/映射：将 diffuse 融合到 [ambient, 1.0]
        # 四个方向最大 diffuse 可达 4；做线性缩放
        diffuse = np.clip(diffuse / 4.0, 0.0, 1.0)
        intensity = np.clip(ambient + (1.0 - ambient) * diffuse, 0.0, 1.0)

        base = np.array(base_color, dtype=np.float64)
        colors_rgb = base[None, :] * intensity[:, None]
        # 组装 RGBA
        alpha = np.ones((num_vertices, 1), dtype=np.float64)
        vertex_colors = np.concatenate([colors_rgb, alpha], axis=1).astype(np.float32)
        return vertex_colors

    @staticmethod
    def _compute_emissive_colors(
        vertices: np.ndarray,
        base_color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
    ) -> np.ndarray:
        """生成自发光（与法线无关、恒定亮度）的每顶点颜色。"""
        num_vertices = vertices.shape[0]
        c = np.clip(np.array(base_color, dtype=np.float64) * float(intensity), 0.0, 1.0)
        rgb = np.repeat(c[None, :], num_vertices, axis=0)
        alpha = np.ones((num_vertices, 1), dtype=np.float64)
        return np.concatenate([rgb, alpha], axis=1).astype(np.float32)

    # ---- 交互（中键拖拽旋转模型 + 滚轮缩放） ----
    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if ev.button() == QtCore.Qt.MiddleButton:
            self._dragging = True
            self._drag_btn = QtCore.Qt.MiddleButton
            self._last_pos = ev.pos()
            ev.accept()
            return
        # 其他按键交给父类（保留默认平移/旋转等）
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if self._dragging and self._drag_btn == QtCore.Qt.MiddleButton and self._last_pos is not None:
            delta = ev.pos() - self._last_pos
            # 将像素偏移映射为角度变化（灵敏度可调整）
            sensitivity = 0.5
            # 水平拖动：模型绕 Y 轴旋转
            if delta.x() != 0:
                self.rotate_model_around_axis(-delta.x() * sensitivity, 0, 1, 0)
            # 垂直拖动：模型绕 X 轴旋转
            if delta.y() != 0:
                self.rotate_model_around_axis(delta.y() * sensitivity, 1, 0, 0)
            self._last_pos = ev.pos()
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if ev.button() == QtCore.Qt.MiddleButton:
            self._dragging = False
            self._drag_btn = None
            self._last_pos = None
            ev.accept()
            return
        super().mouseReleaseEvent(ev)

    def wheelEvent(self, ev: QtGui.QWheelEvent) -> None:  # type: ignore[override]
        if not self.model:
            super().wheelEvent(ev)
            return
        # 缩放：基于距离缩放，滚轮方向与平台相关，取角度增量
        delta = ev.angleDelta().y() / 120.0  # 每档一般为120
        factor = 1.0 / (1.0 + 0.15 * delta)
        factor = float(np.clip(factor, 0.2, 5.0))
        self.model.distance *= factor
        self.model.distance = float(max(1e-3, self.model.distance))
        self._apply_camera_from_model()
        ev.accept()


# -----------------------------
# Controller 层 + 应用窗口
# -----------------------------

class ShowSolidWindow:
    """3D 模型查看器控制器（不继承 Qt 类）"""
    
    def __init__(self, step_path: Optional[str] = None) -> None:
        # MVC 组装
        self.model = MeshModel(mesh_loader=GmshStepLoader())
        self.view = MeshView()
        
        # 创建容器 widget
        self._widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        if step_path:
            self.load_and_show(step_path)
        
        # 键盘快捷键：让模型绕 Y 轴旋转（模拟"Z 轴绕 Y 轴转动"的效果）
        self._init_shortcuts()
    
    def get_widget(self) -> QtWidgets.QWidget:
        """获取可嵌入的 widget 组件"""
        return self._widget
    
    def _init_shortcuts(self) -> None:
        """初始化键盘快捷键：Q/E 控制模型绕 Y 轴旋转。"""
        rotate_left = QtWidgets.QShortcut(QtGui.QKeySequence("Q"), self._widget)
        rotate_left.activated.connect(lambda: self.view.rotate_model_around_y(-10.0))
        
        rotate_right = QtWidgets.QShortcut(QtGui.QKeySequence("E"), self._widget)
        rotate_right.activated.connect(lambda: self.view.rotate_model_around_y(10.0))
    
    def load_and_show(self, step_path: str) -> None:
        try:
            self.model.load_from(step_path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self._widget, "加载失败", f"无法加载STEP文件:\n{exc}")
            return
        self.view.set_model(self.model)


def _parse_cli_path() -> Optional[str]:
    if len(sys.argv) >= 2:
        return sys.argv[1]
    return None


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    # step_path = _parse_cli_path()
    step_path = DEFAULT_DIR + "R87-Y160M.stp"
    
    # 创建一个主窗口来包装组件
    main_window = QtWidgets.QMainWindow()
    main_window.setWindowTitle("STEP 实体查看器（中键拖动旋转模型 / 滚轮缩放）")
    # main_window.setFixedSize(500, 350)
    
    viewer = ShowSolidWindow(step_path)
    main_window.setCentralWidget(viewer.get_widget())
    main_window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


