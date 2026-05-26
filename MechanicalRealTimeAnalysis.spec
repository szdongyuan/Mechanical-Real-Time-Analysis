# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Mechanical Real-Time Analysis."""

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
project_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(project_dir, "ui", "ui_pic"), "ui/ui_pic"),
    (os.path.join(project_dir, "ui", "ui_config"), "ui/ui_config"),
    (os.path.join(project_dir, "configs"), "configs"),
    (os.path.join(project_dir, "ui", "R87-Y160M.stp"), "ui"),
]

binaries = []
hiddenimports = [
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.QtOpenGL",
    "pyqtgraph",
    "pyqtgraph.opengl",
    "OpenGL",
    "OpenGL.GL",
    "librosa",
    "librosa.core",
    "librosa.feature",
    "librosa.util",
    "sounddevice",
    "_sounddevice_data",
    "scipy",
    "scipy.signal",
    "scipy.fft",
    "scipy.special.cython_special",
    "numpy",
    "yaml",
    "concurrent_log_handler",
    "numba",
    "audioread",
    "pooch",
    "soxr",
    "gmsh",
    "consts.ui_style_const",
    "consts.running_consts",
    "consts.db_consts",
    "base.log_manager",
    "base.database.db_manager",
    "ui.calibration_window",
    "ui.show_solid_widget",
    "ui.error_manage_widget",
    "ui.historical_data",
    "ui.main_window",
    "ui.splash_screen_window",
    "ui.analysis_config",
    "ui.tcp_config",
    "ui.device_list",
    "ui.login_window",
    "ui.machine_record_view.center_widget",
    "ui.machine_record_view.navigation_bar",
    "ui.machine_record_view.start_record_widget",
    "ui.machine_record_view.wav_or_spect_graph",
    "base.tcp.tcp_client",
    "base.sound_device_manager",
    "base.soundcard_audio_processor",
    "base.peak_detection_runner",
    "base.knock_detection",
    "base.health_score_generator",
    "my_controls.audio_player_widget",
    "my_controls.health_evaluate_widget",
    "my_controls.peak_scatter_widget",
]

hiddenimports += collect_submodules("ui")
hiddenimports += collect_submodules("base")
hiddenimports += collect_submodules("my_controls")
hiddenimports += collect_submodules("consts")

for pkg in ("librosa", "pyqtgraph", "sounddevice", "scipy", "PyQt5"):
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception:
        pass

try:
    gmsh_ret = collect_all("gmsh")
    datas += gmsh_ret[0]
    binaries += gmsh_ret[1]
    hiddenimports += gmsh_ret[2]
except Exception:
    pass

a = Analysis(
    [os.path.join(project_dir, "main_window_Launcher.py")],
    pathex=[project_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "tensorflow", "torch"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MechanicalRealTimeAnalysis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, "ui", "ui_pic", "sys_ico", "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MechanicalRealTimeAnalysis",
)
