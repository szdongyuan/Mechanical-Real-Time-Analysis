import json
import os
from typing import Dict, List

import numpy as np

from base.knock_detection import KnockDetector
from base.health_score_generator import HealthScoreGenerator
from consts import error_code
from consts.running_consts import PEAK_DETECTION_CONFIG_JSON


def run_peak_detection(signals: List[np.ndarray],
                       file_names: List[str],
                       fs,
                       config_path: str | None = None) -> str:
    cfg_path = config_path or os.path.normpath(PEAK_DETECTION_CONFIG_JSON)
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as exc:
        return json.dumps({
            "ret_code": error_code.INVALID_CONFIG,
            "ret_msg": f"load config failed: {exc}",
            "result": []
        }, ensure_ascii=False)

    detector = KnockDetector(cfg)
    sr_list = fs if isinstance(fs, (list, tuple)) else [fs] * len(signals)

    results = []
    peak_result_map: Dict[str, Dict[str, float]] = {}

    try:
        for idx, signal in enumerate(signals):
            signal = np.array(signal, copy=False)
            sr = int(sr_list[idx])
            detection = detector.run(signal, sr)
            for ch_result in detection.channels:
                ch_name = ch_result.get("channel", f"channel_{len(results)}")
                exceed = bool(ch_result.get("exceed_threshold"))
                detail = {
                    "file": file_names[idx],
                    "channel": ch_name,
                    "max_flux": ch_result.get("max_flux", 0.0),
                    "max_zscore": ch_result.get("max_zscore", 0.0),
                    "threshold": ch_result.get("threshold"),
                    "exceed_threshold": exceed,
                }
                results.append([
                    f"{file_names[idx]}::{ch_name}",
                    "NG" if exceed else "OK",
                    json.dumps(detail, ensure_ascii=False),
                ])
                peak_result_map[ch_name] = {
                    "exceeded": exceed,
                    "peak_value": ch_result.get("max_zscore") or ch_result.get("max_flux"),
                    "threshold": ch_result.get("threshold"),
                }

    except Exception as exc:
        return json.dumps({
            "ret_code": error_code.INVALID_PROCESS,
            "ret_msg": f"knock detection error: {exc}",
            "result": []
        }, ensure_ascii=False)

    health_scores = {}
    try:
        generator = HealthScoreGenerator()
        health_scores = generator.generate_scores(peak_results=peak_result_map)
    except Exception as exc:
        health_scores = {"error": str(exc)}

    result_json = json.dumps({
        "ret_code": error_code.OK,
        "ret_msg": "knock peak detection completed",
        "result": results,
        "health_scores": health_scores,
    }, ensure_ascii=False)
    return result_json

