import os

from time import time

def analysis_worker(job_queue, result_queue):
    """
    独立进程中的分析工作循环：
    - 从 job_queue 获取任务（包含 npy 路径、采样率、模型与配置路径）
    - 加载切片 numpy 文件；首次或模型路径变更时常驻加载模型
    - 逐通道执行预测（复用已加载模型）
    - 将结果通过 result_queue 回传
    - 接收到 None 时退出
    """
    # 子进程内限制底层线程数，避免过度并行
    try:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    except Exception:
        pass
    try:
        import numpy as _np
        import os as _os
        import json as _json
        from base.predict_model import predict_from_audio
        from base.model_config import init_model_from_config as _init_model_from_config
    except Exception as e:
        # 若初始化即失败，尝试将错误回传并退出
        try:
            result_queue.put({"job_id": None, "results": [{"channel": -1, "data": {"ret_code": -1, "ret_msg": f"worker init error: {e}", "result": []}}]})
        finally:
            return


    while True:
        job = job_queue.get()
        if job is None:
            break
        job_id = job.get("job_id")
        npy_path = job.get("npy_path")
        sampling_rate = job.get("sampling_rate")
        model_path = job.get("model_path")
        config_path = job.get("config_path")
        gmm_path = job.get("gmm_path")
        scaler_path = job.get("scaler_path")
        results = []
        try:
            segments = _np.load(npy_path)
            try:
                # 及时删除临时文件，避免堆积
                _os.remove(npy_path)
            except Exception:
                pass
            model_path_dict = {
                "ae": model_path,
                "gmm": gmm_path,
                "scaler": scaler_path,
            }
            try:
                t1 = time()
                ret_str = predict_from_audio(
                    signals=[segments],
                    file_names=["current"],
                    fs=[sampling_rate],
                    load_model_path=model_path_dict,
                    config_path=config_path,
                )
                ret = _json.loads(ret_str)
                print(time() - t1, "time")
            except Exception as e:
                print(e)
                ret = {"ret_code": -1, "ret_msg": f"predict error: {e}", "result": [[ "ERR", "0.0"]]}
            results.append(ret)

        except Exception as e:
            results = [{"ret_code": -1, "ret_msg": f"worker error: {e}", "result": []}]
        try:
            result_queue.put({"job_id": job_id, "results": results})
        except Exception:
            # 主进程可能已退出
            pass