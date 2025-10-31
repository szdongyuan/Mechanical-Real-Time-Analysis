class DataDealStruct(object):
    _instance = None

    @classmethod
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DataDealStruct, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.save_flag = False
            self.record_flag = False
            self.channels_change_flag = True
            self.used_audio_data_arr = None

            self._initialized = True

            self.audio_data = None
            self.audio_data_queue = None
            self.audio_data_arr_i = None
            self.audio_data_arr_ii = None

            # 写入-读取一致性 epoch（偶数表示稳定快照可读，奇数表示写入中）
            self.epoch = 0
            
            # 音频片段提取器相关属性（遵循开闭原则，扩展而非修改）
            self.segment_extractor = None
            self.extracted_audio_segments = None  # 二维数组，存储提取的音频片段