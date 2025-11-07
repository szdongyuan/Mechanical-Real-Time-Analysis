"""
保存AI分析判定为NG的音频片段并写入数据库的工具模块

使用说明（接口概览）：

1) save_and_log_warning_segment(segment, sampling_rate, channel_index, segment_duration_sec, base_dir=None,
                                warning_level="一般", charge_person="", deal_status="未确认", description=None) -> str
   - 作用：将单通道音频片段保存为 .wav 文件（文件名：YYYYMMDDHHMMSS-通道.wav），并写入 warning_audio_data_table。
   - 参数：
       segment               单通道波形，numpy.ndarray，1D，建议float16/float32
       sampling_rate         采样率（Hz）
       channel_index         通道索引（与分析结果的channel一致）
       segment_duration_sec  该片段时长（秒），用于推算记录开始/结束时间
       base_dir              自定义保存目录；不传则默认写入 consts.db_consts.STORED_RECORDED_NG_PATH
       warning_level         警告级别（文本），默认“一般”
       charge_person         负责人（文本），默认空
       deal_status           处理状态（文本），默认“未确认”
       description           备注（文本），默认自动填充“AI分析NG，通道X”
   - 返回：保存后的绝对文件路径（str）

2) save_warning_wav(segment, sampling_rate, channel_index, base_dir=None, timestamp=None) -> str
   - 作用：仅落盘 .wav 文件（不写库）。
   - 返回：保存后的绝对文件路径（str）

3) insert_warning_record(file_name, record_time, stop_time, channel_index,
                         warning_level="一般", warning_status="NG", charge_person="",
                         deal_status="未确认", description=None) -> None
   - 作用：仅写库到 warning_audio_data_table（不落盘）。

注意：
- 数据库表结构以既有数据库为准（warning_audio_data_table），本模块使用 consts.db_consts.WARNING_COLUMNS 的列顺序写入。
- 文件名采用“YYYYMMDDHHMMSS-通道.wav”格式，通道为传入的 channel_index（从0开始）。
"""

import os
import time
from typing import Optional

import numpy as np

from base.database.db_manager import DataManage
from consts import db_consts

from base.audio_data_manager import save_audio_data


def _ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _now_str() -> str:
    return time.strftime("%Y%m%d%H%M%S", time.localtime())


def save_warning_wav(
    segment: np.ndarray,
    sampling_rate: int,
    channel_index: int,
    base_dir: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> str:
    """
    将单通道音频片段保存为“YYYYMMDDHHMMSS-通道.wav”。
    返回保存后的绝对路径。
    """
    if base_dir is None:
        base_dir = db_consts.STORED_RECORDED_NG_PATH
    _ensure_dir(base_dir)

    ts = timestamp or _now_str()
    file_name = f"{ts}-{channel_index}.wav"
    abs_path = os.path.normpath(os.path.join(base_dir, file_name))

    save_audio_data(segment, sampling_rate, abs_path)

    return abs_path


def insert_warning_record(
    file_name: str,
    record_time: str,
    stop_time: str,
    channel_index: int,
    warning_level: str = "一般",
    warning_status: str = "NG",
    charge_person: str = "",
    deal_status: str = "未确认",
    description: Optional[str] = None,
) -> None:
    """
    向 warning_audio_data_table 插入一条记录。
    采用 consts.db_consts.WARNING_COLUMNS 列顺序：
    [warning_time, warning_level, warning_status, charge_person, file_name, record_time, stop_time, deal_status, description]
    """
    warning_time = _now_str()
    warning_time = time.strftime("%Y年%m月%d日 %H时%M分%S秒", time.strptime(warning_time, "%Y%m%d%H%M%S"))
    if description is None:
        description = f"AI分析NG，通道{channel_index}"

    data_row = [
        warning_time,
        warning_level,
        warning_status,
        charge_person,
        file_name,
        record_time,
        stop_time,
        deal_status,
        description,
    ]

    with DataManage(db_consts.DATABASE_PATH) as db:
        db.insert_data_into_db("warning_audio_data_table", db_consts.WARNING_COLUMNS, [data_row])


def save_and_log_warning_segment(
    segment: np.ndarray,
    sampling_rate: int,
    channel_index: int,
    segment_duration_sec: float,
    base_dir: Optional[str] = None,
    warning_level: str = "一般",
    charge_person: str = "",
    deal_status: str = "未确认",
    description: Optional[str] = None,
) -> str:
    """
    组合操作：保存音频片段到 .wav，并写入 warning_audio_data_table。
    返回最终保存的绝对文件路径。
    """
    stop_time = _now_str()
    try:
        # 推算片段开始时间（向下取整到秒）
        dur = max(0.0, float(segment_duration_sec))
        start_epoch = int(time.time() - dur)
        record_time = time.strftime("%Y年%m月%d日 %H时%M分%S秒", time.localtime(start_epoch))
    except Exception:
        record_time = stop_time

    # 按要求文件名格式：YYYYMMDDHHMMSS-通道.wav（使用stop_time做时间戳）
    file_path = save_warning_wav(segment, sampling_rate, channel_index, base_dir=base_dir, timestamp=stop_time)
    stop_time_cn = time.strftime("%Y年%m月%d日 %H时%M分%S秒", time.strptime(stop_time, "%Y%m%d%H%M%S"))

    # 数据库仅存“文件名称”列，此处存储文件名（包含扩展名）
    file_name = os.path.basename(file_path)

    insert_warning_record(
        file_name=file_name,
        record_time=record_time,
        stop_time=stop_time_cn,
        channel_index=channel_index,
        warning_level=warning_level,
        warning_status="NG",
        charge_person=charge_person,
        deal_status=deal_status,
        description=description or f"AI分析NG，通道{channel_index}",
    )

    return file_path


