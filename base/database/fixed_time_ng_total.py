import time
from typing import Any, Dict, List, Tuple

from base.database.db_manager import DataManage
from consts import db_consts, error_code


CN_TIME_FMT = "%Y年%m月%d日 %H时%M分%S秒"


def _parse_cn_time_to_epoch(time_str: str) -> int:
    """
    将“YYYY年MM月DD日 HH时mm分ss秒”解析为本地时间的 epoch 秒。
    """
    return int(time.mktime(time.strptime(time_str, CN_TIME_FMT)))


def query_warning_between(
    start_time_cn: str,
    end_time_cn: str,
    time_field: str = "warning_time",
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    在 warning_audio_data_table 中查询介于两个时间之间的所有数据（闭区间）。

    参数:
        start_time_cn: 开始时间（格式：YYYY年MM月DD日 HH时mm分ss秒）
        end_time_cn:   结束时间（格式：YYYY年MM月DD日 HH时mm分ss秒）
        time_field:    用于比较的时间字段（默认：warning_time，可选：record_time/stop_time）

    返回:
        (code, result)
        - code == 0 表示成功，result 为记录字典列表
        - 否则返回 (错误码, 错误信息字符串)
    """
    try:
        start_epoch = _parse_cn_time_to_epoch(start_time_cn)
        end_epoch = _parse_cn_time_to_epoch(end_time_cn)
        if start_epoch > end_epoch:
            start_epoch, end_epoch = end_epoch, start_epoch
    except Exception as e:
        return error_code.INVALID_TYPE_DATA, f"时间解析失败: {e}"
    with DataManage(db_consts.DATABASE_PATH) as db:
        code, rows = db.query("warning_audio_data_table", db_consts.WARNING_COLUMNS)
        if code != error_code.OK:
            return code, rows  # rows 为错误信息
    columns = db_consts.WARNING_COLUMNS
    col_index_map = {name: idx for idx, name in enumerate(columns)}
    if time_field not in col_index_map:
        return error_code.INVALID_TYPE_DATA, f"不支持的时间字段: {time_field}"

    tf_idx = col_index_map[time_field]

    def _row_to_dict(row_tuple) -> Dict[str, Any]:
        return {col: row_tuple[i] for i, col in enumerate(columns)}

    filtered: List[Dict[str, Any]] = []
    for row in rows:
        try:
            time_str = row[tf_idx]
            ts = _parse_cn_time_to_epoch(time_str)
            if start_epoch <= ts <= end_epoch:
                filtered.append(_row_to_dict(row))
        except Exception:
            # 跳过无法解析时间的记录
            continue

    # 按时间升序排序
    filtered.sort(key=lambda r: r.get(time_field, ""))
    return error_code.OK, filtered


if __name__ == "__main__":
    print("请输入查询时间（格式：YYYY年MM月DD日 HH时mm分ss秒）")
    # start = input("开始时间: ").strip()
    # end = input("结束时间: ").strip()
    start = "2025年11月12日 10时00分00秒"
    end = "2025年11月12日 12时00分00秒"
    code, result = query_warning_between(start, end, time_field="warning_time")
    if code == error_code.OK:
        print(f"匹配到 {len(result)} 条记录")
        for r in result:
            print(r)
    else:
        print(f"查询失败: {result}")


