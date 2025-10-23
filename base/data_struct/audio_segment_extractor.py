"""
音频片段提取器模块
按照开闭原则设计，通过组合方式扩展功能而不修改现有代码
"""
import numpy as np
import threading
import time
from typing import List, Optional


class AudioSegmentExtractor:
    """
    音频片段提取器类
    功能：每隔指定时间从音频数据数组中提取最后N秒的数据
    """
    
    def __init__(self, 
                 extract_interval: float = 3.5,
                 segment_duration: float = 4.0,
                 sampling_rate: int = 44100):
        """
        初始化音频片段提取器
        
        Args:
            extract_interval: 提取间隔时间（秒），默认3.5秒
            segment_duration: 每次提取的数据时长（秒），默认4秒
            sampling_rate: 采样率，默认44100Hz
        """
        self.extract_interval = extract_interval
        self.segment_duration = segment_duration
        self.sampling_rate = sampling_rate
        self.segment_samples = int(segment_duration * sampling_rate)  # 4秒对应的采样点数
        
        self._is_running = False
        self._extract_thread: Optional[threading.Thread] = None
        self._audio_data_arr: Optional[List[np.ndarray]] = None
        self._write_index_ref = None  # 环形缓冲区写入位置索引
        self._extracted_segments: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        
    def set_audio_source(self, audio_data_arr: List[np.ndarray], write_index_ref=None):
        """
        设置音频数据源
        
        Args:
            audio_data_arr: 音频数据数组列表（环形缓冲区），每个元素对应一个通道
            write_index_ref: 写入位置索引的引用（用于环形缓冲区）
        """
        with self._lock:
            self._audio_data_arr = audio_data_arr
            self._write_index_ref = write_index_ref
            num_channels = len(audio_data_arr)
            # 初始化二维数组，用于存储提取的数据
            # 形状为 (通道数, 片段采样点数)
            self._extracted_segments = np.zeros((num_channels, self.segment_samples), dtype=np.float32)
    
    def start(self):
        """启动提取器"""
        if self._is_running:
            print("AudioSegmentExtractor 已经在运行中")
            return
        
        if self._audio_data_arr is None:
            raise ValueError("请先通过set_audio_source()设置音频数据源")
        
        self._is_running = True
        self._extract_thread = threading.Thread(target=self._extraction_loop, daemon=True)
        self._extract_thread.start()
        print(f"AudioSegmentExtractor 已启动：每隔{self.extract_interval}秒提取最后{self.segment_duration}秒的数据")
    
    def stop(self):
        """停止提取器"""
        if not self._is_running:
            return
        
        self._is_running = False
        if self._extract_thread is not None:
            self._extract_thread.join(timeout=5)
        print("AudioSegmentExtractor 已停止")
    
    def _extraction_loop(self):
        """提取循环（在独立线程中运行）"""
        while self._is_running:
            try:
                self._extract_segments()
                time.sleep(self.extract_interval)
            except Exception as e:
                print(f"音频片段提取出错: {e}")
    
    def _extract_segments(self):
        """
        从每个通道提取最后N秒的数据
        考虑环形缓冲区的特性，根据write_index正确提取数据
        """
        if self._audio_data_arr is None or self._extracted_segments is None:
            return
        
        with self._lock:
            for channel_idx, ring_buffer in enumerate(self._audio_data_arr):
                # 获取环形缓冲区的写入位置
                if self._write_index_ref is not None and channel_idx < len(self._write_index_ref):
                    write_idx = self._write_index_ref[channel_idx]
                    
                    # 将环形缓冲区转换为线性数组
                    # write_idx 指向下一个要写入的位置
                    # 最旧的数据在 write_idx 位置，最新的数据在 write_idx-1 位置
                    # 拼接顺序：[write_idx:] 是较旧的数据, [:write_idx] 是较新的数据
                    linear_data = np.concatenate([ring_buffer[write_idx:], ring_buffer[:write_idx]])
                else:
                    # 如果没有提供write_index，假设是普通数组
                    linear_data = ring_buffer
                
                # 从线性数据中提取最后segment_samples个采样点
                data_length = len(linear_data)
                if data_length >= self.segment_samples:
                    # 如果数据足够，提取最后的segment_samples个点
                    segment = linear_data[-self.segment_samples:]
                else:
                    # 如果数据不足，用0填充前面部分
                    segment = np.zeros(self.segment_samples, dtype=np.float32)
                    segment[-data_length:] = linear_data
                
                # 存储到二维数组对应通道
                self._extracted_segments[channel_idx] = segment
            
            # 打印日志（可选）
            current_time = time.strftime("%H:%M:%S", time.localtime())
            print(f"[{current_time}] 已提取音频片段：{len(self._audio_data_arr)}个通道，每个{self.segment_duration}秒")
    
    def get_extracted_segments(self) -> Optional[np.ndarray]:
        """
        获取提取的音频片段数据
        
        Returns:
            二维numpy数组，形状为 (通道数, 片段采样点数)
        """
        with self._lock:
            if self._extracted_segments is not None:
                return self._extracted_segments.copy()
            return None
    
    def get_segment_info(self) -> dict:
        """
        获取片段信息
        
        Returns:
            包含片段配置信息的字典
        """
        return {
            "extract_interval": self.extract_interval,
            "segment_duration": self.segment_duration,
            "sampling_rate": self.sampling_rate,
            "segment_samples": self.segment_samples,
            "num_channels": len(self._audio_data_arr) if self._audio_data_arr else 0,
            "is_running": self._is_running
        }
    
    @property
    def is_running(self) -> bool:
        """提取器是否正在运行"""
        return self._is_running
    
    @property
    def extracted_segments(self) -> Optional[np.ndarray]:
        """获取提取的片段数据（只读属性）"""
        return self.get_extracted_segments()

