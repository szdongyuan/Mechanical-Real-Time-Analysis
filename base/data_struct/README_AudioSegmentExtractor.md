# 音频片段提取器使用说明

## 功能概述

`AudioSegmentExtractor` 是一个遵循开闭原则设计的音频数据提取工具，用于定期从多通道音频数据流中提取指定时长的数据片段。

## 设计原则

本功能严格遵循开闭原则（Open-Closed Principle）：
- **对扩展开放**：通过创建新类 `AudioSegmentExtractor` 来扩展功能
- **对修改封闭**：不修改现有核心代码，通过组合方式集成到系统中

## 核心特性

1. **定时提取**：每隔 3.5 秒自动提取一次数据
2. **多通道支持**：支持从多个音频通道同时提取数据
3. **固定时长**：每次提取最后 4 秒的音频数据
4. **线程安全**：使用线程锁保证多线程环境下的数据安全
5. **二维数组存储**：提取的数据存储在二维 numpy 数组中，格式为 (通道数, 采样点数)

## 架构设计

```
RecordMachineAudioWidget
    ├── DataDealStruct (单例数据结构)
    │   ├── audio_data_arr (音频数据源)
    │   ├── segment_extractor (提取器实例)
    │   └── extracted_audio_segments (提取结果)
    └── AudioSegmentExtractor (提取器类)
        ├── 独立线程运行
        ├── 定时提取逻辑
        └── 线程安全的数据访问
```

## 使用方法

### 1. 初始化（已自动集成）

在 `RecordMachineAudioWidget.__init__()` 中已自动初始化：

```python
self.segment_extractor = AudioSegmentExtractor(
    extract_interval=3.5,  # 每隔3.5秒提取一次
    segment_duration=4.0,   # 提取最后4秒的数据
    sampling_rate=44100     # 采样率
)
self.segment_extractor.set_audio_source(self.data_struct.audio_data_arr)
```

### 2. 启动提取器（录音时自动启动）

开始录音时，提取器会自动启动：

```python
def record_audio(self):
    # ... 其他代码 ...
    self.segment_extractor.start()  # 自动启动
    # ... 其他代码 ...
```

### 3. 停止提取器（停止录音时自动停止）

停止录音时，提取器会自动停止：

```python
def stop_record(self):
    # ... 其他代码 ...
    self.segment_extractor.stop()  # 自动停止
    # ... 其他代码 ...
```

### 4. 获取提取的数据

可以在程序的任何地方访问提取的数据：

```python
# 方法1：通过提取器实例获取
segments = self.segment_extractor.get_extracted_segments()
if segments is not None:
    print(f"数据形状: {segments.shape}")  # 输出: (通道数, 采样点数)
    print(f"通道0的数据: {segments[0]}")

# 方法2：通过DataDealStruct获取（推荐）
from base.data_struct.data_deal_struct import DataDealStruct
data_struct = DataDealStruct()
if data_struct.segment_extractor:
    segments = data_struct.segment_extractor.get_extracted_segments()
    
# 方法3：使用属性访问
segments = self.segment_extractor.extracted_segments  # 只读属性
```

### 5. 查看提取器状态

```python
# 获取提取器配置信息
info = self.segment_extractor.get_segment_info()
print(f"提取间隔: {info['extract_interval']}秒")
print(f"片段时长: {info['segment_duration']}秒")
print(f"采样率: {info['sampling_rate']}Hz")
print(f"通道数: {info['num_channels']}")
print(f"运行状态: {info['is_running']}")

# 检查是否正在运行
if self.segment_extractor.is_running:
    print("提取器正在运行")
```

## 数据格式说明

### 输入数据
- **类型**: `List[np.ndarray]`
- **格式**: 每个元素代表一个音频通道
- **来源**: `self.data_struct.audio_data_arr`

### 输出数据
- **类型**: `np.ndarray`
- **形状**: `(通道数, 采样点数)`
- **数据类型**: `np.float32`
- **采样点数**: `segment_duration * sampling_rate` (默认: 4.0 * 44100 = 176400)

示例：
```python
segments = self.segment_extractor.get_extracted_segments()
# segments.shape = (2, 176400)  # 假设有2个通道
# segments[0] = 第一个通道的4秒音频数据
# segments[1] = 第二个通道的4秒音频数据
```

## 配置参数

可以在创建提取器时自定义参数：

```python
extractor = AudioSegmentExtractor(
    extract_interval=5.0,    # 修改为每5秒提取一次
    segment_duration=3.0,    # 修改为提取3秒的数据
    sampling_rate=48000      # 修改采样率为48kHz
)
```

## 线程安全

提取器使用线程锁保护关键数据：
- 所有数据访问操作都是线程安全的
- 可以在录音线程运行时安全地读取提取的数据
- 不会干扰主录音流程

## 性能考虑

- 提取操作在独立线程中运行，不阻塞主界面
- 内存占用: 约 `通道数 × 采样点数 × 4字节` (例如: 2通道 × 176400 × 4 = 1.41MB)
- CPU占用: 极低，仅在提取时短暂占用

## 扩展示例

### 示例1：在更新绘图时使用提取的数据

```python
def update_plot(self, selected_channels, audio_data, canvas):
    while True:
        if not self.data_struct.record_flag:
            break
        
        # 获取提取的片段数据
        segments = self.segment_extractor.get_extracted_segments()
        if segments is not None:
            # 可以对提取的数据进行分析或处理
            for i in range(len(selected_channels)):
                # 例如：计算RMS值
                rms = np.sqrt(np.mean(segments[i]**2))
                print(f"通道{i} RMS: {rms}")
        
        # ... 原有的绘图代码 ...
        time.sleep(1)
```

### 示例2：保存提取的片段到文件

```python
def save_extracted_segments(self):
    """保存提取的音频片段到文件"""
    segments = self.segment_extractor.get_extracted_segments()
    if segments is not None:
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        filename = f"extracted_segment_{timestamp}.npy"
        np.save(filename, segments)
        print(f"已保存片段数据到: {filename}")
```

### 示例3：实时监控音频电平

```python
def monitor_audio_level(self):
    """实时监控音频电平"""
    segments = self.segment_extractor.get_extracted_segments()
    if segments is not None:
        for i in range(len(self.selected_channels)):
            # 计算峰值
            peak = np.max(np.abs(segments[i]))
            # 计算平均值
            avg = np.mean(np.abs(segments[i]))
            print(f"通道{i} - 峰值: {peak:.4f}, 平均: {avg:.4f}")
```

## 注意事项

1. **数据更新频率**：数据每3.5秒更新一次，读取时获取的是最近一次提取的数据
2. **启动延迟**：首次提取需要等待3.5秒
3. **数据有效性**：只有在录音开始后才会有有效数据
4. **资源清理**：停止录音或关闭窗口时会自动清理提取器资源

## 技术细节

### 提取算法
```python
# 从环形缓冲区提取最后N秒的数据
segment = audio_data[-segment_samples:]  # 简单切片

# 如果数据不足，用0填充
if data_length < segment_samples:
    segment = np.zeros(segment_samples)
    segment[-data_length:] = audio_data
```

### 线程模型
```
主线程 (GUI)
    └─> 录音线程 (AudioDataManager)
    └─> 绘图线程 (update_plot)
    └─> 提取器线程 (AudioSegmentExtractor)  ← 新增，独立运行
```

## 版本历史

- **v1.0** (2025-10-20): 初始版本
  - 支持定时提取多通道音频数据
  - 遵循开闭原则设计
  - 线程安全实现

## 作者

东原科技 - 音频系统开发团队

