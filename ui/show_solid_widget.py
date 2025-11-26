import sys
import math
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Protocol
from collections import defaultdict

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
    edges_pos: Optional[np.ndarray] = field(default=None)  # 预计算的特征边顶点

    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.vertices.size == 0:
            return np.zeros(3), np.zeros(3)
        vmin = self.vertices.min(axis=0)
        vmax = self.vertices.max(axis=0)
        return vmin, vmax


class MeshLoader(Protocol):
    def load(self, file_path: str) -> MeshData:
        ...


def compute_feature_edges(vertices: np.ndarray, faces: np.ndarray, angle_threshold_deg: float = 1.0) -> np.ndarray:
    """从三角面提取外部特征边（边界边 + 锐边），返回按端点对展开的顶点数组。
    
    Args:
        vertices: 顶点数组 (N, 3)
        faces: 面索引数组 (M, 3)
        angle_threshold_deg: 锐边判定阈值（度），相邻面法线夹角超过此值的边会被保留
    """
    # 计算每个三角形的法线
    def compute_face_normal(tri_idx: int) -> np.ndarray:
        i, j, k = int(faces[tri_idx][0]), int(faces[tri_idx][1]), int(faces[tri_idx][2])
        v0, v1, v2 = vertices[i], vertices[j], vertices[k]
        n = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(n)
        if norm > 1e-12:
            n = n / norm
        return n
    
    # 建立边到面的映射
    edge_to_faces: dict = defaultdict(list)
    for face_idx, tri in enumerate(faces):
        i, j, k = int(tri[0]), int(tri[1]), int(tri[2])
        e1 = (min(i, j), max(i, j))
        e2 = (min(j, k), max(j, k))
        e3 = (min(k, i), max(k, i))
        edge_to_faces[e1].append(face_idx)
        edge_to_faces[e2].append(face_idx)
        edge_to_faces[e3].append(face_idx)
    
    # 筛选特征边：边界边（只属于1个面）或锐边（相邻面法线夹角大于阈值）
    angle_threshold_rad = np.radians(angle_threshold_deg)
    cos_threshold = np.cos(angle_threshold_rad)
    
    feature_edges: List[Tuple[int, int]] = []
    for edge, face_list in edge_to_faces.items():
        if len(face_list) == 1:
            # 边界边：只属于一个三角形
            feature_edges.append(edge)
        elif len(face_list) == 2:
            # 检查两个相邻面的法线夹角
            n1 = compute_face_normal(face_list[0])
            n2 = compute_face_normal(face_list[1])
            cos_angle = np.dot(n1, n2)
            # 夹角大于阈值 => cos值小于阈值
            if cos_angle < cos_threshold:
                feature_edges.append(edge)
        # len > 2 的情况（非流形边）也保留
        elif len(face_list) > 2:
            feature_edges.append(edge)
    
    # 为GLLinePlotItem准备：将所有端点平铺，按 pairs 连接（0-1,2-3,...）
    pos_list: List[np.ndarray] = []
    for a, b in feature_edges:
        pos_list.append(vertices[a])
        pos_list.append(vertices[b])

    if not pos_list:
        return np.zeros((0, 3), dtype=np.float64)
        
    pos = np.array(pos_list, dtype=np.float64).reshape(-1, 3)
    return pos


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


class CachingMeshLoader:
    """带缓存功能的网格加载器，包装其他加载器。
    
    缓存文件格式：.npz（numpy压缩格式）
    缓存内容：vertices, faces, edges_pos
    缓存策略：如果缓存文件存在且比源文件新，直接读取缓存
    """
    
    def __init__(self, base_loader: MeshLoader, edge_angle_threshold: float = 1.0) -> None:
        self.base_loader = base_loader
        self.edge_angle_threshold = edge_angle_threshold
    
    def _get_cache_path(self, file_path: str) -> str:
        """获取缓存文件路径。"""
        return file_path + ".cache.npz"
    
    def _is_cache_valid(self, file_path: str, cache_path: str) -> bool:
        """检查缓存是否有效（存在且比源文件新）。"""
        if not os.path.exists(cache_path):
            return False
        try:
            source_mtime = os.path.getmtime(file_path)
            cache_mtime = os.path.getmtime(cache_path)
            return cache_mtime > source_mtime
        except OSError:
            return False
    
    def _load_from_cache(self, cache_path: str) -> MeshData:
        """从缓存加载网格数据。"""
        data = np.load(cache_path)
        return MeshData(
            vertices=data['vertices'],
            faces=data['faces'],
            edges_pos=data['edges_pos']
        )
    
    def _save_to_cache(self, cache_path: str, mesh: MeshData) -> None:
        """保存网格数据到缓存。"""
        try:
            np.savez_compressed(
                cache_path,
                vertices=mesh.vertices,
                faces=mesh.faces,
                edges_pos=mesh.edges_pos
            )
        except Exception:
            # 缓存保存失败不影响正常使用
            pass
    
    def load(self, file_path: str) -> MeshData:
        """加载网格数据，优先使用缓存。"""
        cache_path = self._get_cache_path(file_path)
        
        # 尝试从缓存加载
        if self._is_cache_valid(file_path, cache_path):
            try:
                return self._load_from_cache(cache_path)
            except Exception:
                # 缓存读取失败，继续使用原始加载
                pass
        
        # 使用原始加载器加载
        mesh = self.base_loader.load(file_path)
        
        # 计算特征边
        edges_pos = compute_feature_edges(
            mesh.vertices, 
            mesh.faces, 
            self.edge_angle_threshold
        )
        mesh = MeshData(
            vertices=mesh.vertices,
            faces=mesh.faces,
            edges_pos=edges_pos
        )
        
        # 保存到缓存
        self._save_to_cache(cache_path, mesh)
        
        return mesh


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
        self._bg_color = (40, 44, 45)
        self.setBackgroundColor(self._bg_color)

        # 内容项
        self.mesh_item: Optional[gl.GLMeshItem] = None
        self.edge_item: Optional[gl.GLLinePlotItem] = None

        # 记录拖拽状态
        self._dragging: bool = False
        self._drag_btn: Optional[QtCore.Qt.MouseButton] = None
        self._last_pos: Optional[QtCore.QPoint] = None

        # 绑定的模型对象，用于获取/更新视角状态
        self.model: Optional[MeshModel] = None
        
        # 自动旋转定时器：10秒一圈 = 360度/10秒 = 36度/秒
        self._auto_rotate_enabled: bool = True
        self._rotation_speed: float = 36.0  # 度/秒
        self._timer_interval: int = 16  # ms (~60fps)
        self._auto_rotate_timer = QtCore.QTimer(self)
        self._auto_rotate_timer.timeout.connect(self._on_auto_rotate)
        self._auto_rotate_timer.start(self._timer_interval)

    def _on_auto_rotate(self) -> None:
        """定时器回调：自动旋转模型。"""
        if self._dragging or not self._auto_rotate_enabled:
            return
        # 每次旋转的角度 = 速度 * 时间间隔
        angle = self._rotation_speed * (self._timer_interval / 1000.0)
        self.rotate_model_around_y(angle)

    # ---- 显示与更新 ----
    def set_model(self, model: MeshModel) -> None:
        self.model = model
        if not model.mesh:
            return

        vertices = model.mesh.vertices
        faces = model.mesh.faces

        # 创建背景色的不透明面，用于深度遮挡（隐藏被遮挡的边线）
        md = gl.MeshData(vertexes=vertices, faces=faces)
        bg_color = tuple(c / 255.0 for c in self._bg_color) + (1.0,)
        mesh_item = gl.GLMeshItem(
            meshdata=md,
            smooth=False,
            shader=None,  # 纯色，无光照
            color=bg_color,
        )
        mesh_item.setGLOptions('opaque')

        # 使用缓存的边线数据，如果没有则实时计算
        if model.mesh.edges_pos is not None:
            edges_pos = model.mesh.edges_pos
        else:
            edges_pos = compute_feature_edges(vertices, faces)
        
        # 只显示边线，使用明亮的青白色
        edge_item = gl.GLLinePlotItem(
            pos=edges_pos, 
            color=(0.85, 0.95, 1.0, 1.0),  # 明亮的青白色
            width=1.5, 
            mode='lines',
            antialias=True
        )
        edge_item.setGLOptions('opaque')  # 启用深度测试

        # 清理旧项并添加
        if self.mesh_item:
            self.removeItem(self.mesh_item)
        if self.edge_item:
            self.removeItem(self.edge_item)

        self.mesh_item = mesh_item
        self.edge_item = edge_item
        # 先添加面，再添加边线，确保边线绘制在面之上
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
        # MVC 组装 - 使用带缓存的加载器
        base_loader = GmshStepLoader()
        caching_loader = CachingMeshLoader(base_loader, edge_angle_threshold=1.0)
        self.model = MeshModel(mesh_loader=caching_loader)
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


