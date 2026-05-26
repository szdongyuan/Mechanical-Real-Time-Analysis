# TCP 音频 Server 端对接说明

## 连接配置

Client 按配置的 `audio_interval_sec` 主动连接一次 Server，发送最近一段录音数据后关闭连接。

默认配置位于 `ui/ui_config/tcp_config.json`：

```json
{
  "enable_audio_tcp": false,
  "server_ip": "192.168.2.141",
  "client_ip": "192.168.2.168",
  "port": 50000,
  "audio_interval_sec": 60,
  "tcp_audio_sample_rate": 16000,
  "tcp_audio_bit_depth": 16
}
```

- `server_ip`: Server 监听 IP。
- `client_ip`: Client 发送前绑定的本机 IP。
- `port`: Server 监听端口，默认 `50000`。
- `enable_audio_tcp`: 是否启用音频 TCP 传输。
- `audio_interval_sec`: 音频发送间隔和单包音频时长，单位秒，默认 `60`，调试时可改小。
- `tcp_audio_sample_rate`: TCP 音频发送前的目标采样率，默认 `16000` Hz；若高于当前录音采样率，则保持当前采样率。
- `tcp_audio_bit_depth`: TCP 音频 payload 位深度，默认 `16`，支持 `8`、`16`、`32`；`32` 表示兼容旧版 `float32`。

## 数据包格式

每个 TCP 连接只发送一个完整音频包：

```text
4 bytes metadata_length (big-endian unsigned int)
metadata_length bytes metadata_json (UTF-8)
payload_bytes raw_audio_data
```

`metadata_json` 示例：

```json
{
  "type": "audio_data",
  "timestamp": 1779690000.123,
  "sample_rate": 16000,
  "channels": 2,
  "selected_channels": [0, 1],
  "dtype": "int16",
  "shape": [2, 960000],
  "byte_order": "little",
  "duration_sec": 60.0,
  "payload_bytes": 3840000,
  "original_sample_rate": 44100,
  "tcp_audio_sample_rate": 16000,
  "tcp_audio_bit_depth": 16,
  "record_start_time": "20260525143000",
  "device_name": "Input Device"
}
```

字段说明：

- `sample_rate`: 当前 TCP 包 payload 的采样率，Server 必须按该值解析音频时间轴。
- `channels`: 本次发送的通道数量。
- `selected_channels`: Client 端选择的原始输入通道索引，0 基。
- `dtype`: payload 数据类型，跟随 `tcp_audio_bit_depth`，可能为 `int8`、`int16` 或 `float32`。
- `shape`: 音频数组形状，固定为 `[channels, samples]`。
- `byte_order`: 多字节类型为 `little`，`int8` 为 `not_applicable`。
- `duration_sec`: 本次音频时长，对应配置中的 `audio_interval_sec`。
- `payload_bytes`: 原始音频字节长度，应等于 `channels * samples * 每个采样点字节数`。
- `original_sample_rate`: Client 录音原始采样率。
- `tcp_audio_sample_rate`: Client 本次发送采用的目标采样率。
- `tcp_audio_bit_depth`: Client 本次发送采用的目标位深度。

## Server 端解析二进制音频包

Server 端需要按顺序读取 3 段数据：

1. 先读 4 字节，按 big-endian unsigned int 解析出 `metadata_json` 的字节长度。
2. 再读 `metadata_length` 字节，按 UTF-8 解码并 `json.loads()` 得到 `metadata`。
3. 最后按 `metadata["payload_bytes"]` 读取剩余音频 payload，这段就是原始 `raw_audio_data`。

`raw_audio_data` 本身是连续二进制，不是 JSON。Server 端应按 `metadata["dtype"]` 选择解析类型：

```python
import json
import numpy as np


def recv_exact(conn, size: int) -> bytes:
    """从 TCP 连接中精确读取 size 字节。"""
    chunks = []
    remaining = int(size)
    while remaining > 0:
        chunk = conn.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed before packet completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def parse_audio_packet(conn):
    # 1. 读取 metadata 长度：4 bytes, big-endian unsigned int
    metadata_len_bytes = recv_exact(conn, 4)
    metadata_len = int.from_bytes(metadata_len_bytes, byteorder="big", signed=False)

    # 2. 读取 metadata JSON
    metadata_bytes = recv_exact(conn, metadata_len)
    metadata = json.loads(metadata_bytes.decode("utf-8"))

    # 3. 读取原始音频 payload。这段 bytes 就是 raw_audio_data。
    payload_len = int(metadata["payload_bytes"])
    raw_audio_data = recv_exact(conn, payload_len)

    # 4. 将 raw_audio_data 转成 numpy 数组。
    dtype_map = {
        "int8": np.dtype("i1"),
        "int16": np.dtype("<i2"),
        "float32": np.dtype("<f4"),
    }
    audio = np.frombuffer(raw_audio_data, dtype=dtype_map[metadata["dtype"]])
    audio = audio.reshape(tuple(metadata["shape"]))

    return metadata, raw_audio_data, audio
```

解析完成后：

- `metadata`: 包头信息，包含采样率、通道数、shape、payload 字节数等。
- `raw_audio_data`: 原始二进制音频数据，类型是 `bytes`。
- `audio`: 可直接处理的二维 `numpy.ndarray`，形状为 `[channels, samples]`。

如果只想落盘保存原始 payload，可直接写入 `.raw` 文件：

```python
metadata, raw_audio_data, audio = parse_audio_packet(conn)

with open("audio_payload.raw", "wb") as f:
    f.write(raw_audio_data)
```

之后读取该 `.raw` 文件时，需要使用同样的 dtype 和 shape：

```python
shape = tuple(metadata["shape"])
dtype_map = {"int8": np.dtype("i1"), "int16": np.dtype("<i2"), "float32": np.dtype("<f4")}
audio = np.fromfile("audio_payload.raw", dtype=dtype_map[metadata["dtype"]]).reshape(shape)
```

## Python Server 示例

```python
import json
import socket

import numpy as np


def recv_exact(conn, size):
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = conn.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed before packet completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def handle_client(conn):
    header = recv_exact(conn, 4)
    metadata_len = int.from_bytes(header, byteorder="big", signed=False)
    metadata = json.loads(recv_exact(conn, metadata_len).decode("utf-8"))

    payload_len = int(metadata["payload_bytes"])
    payload = recv_exact(conn, payload_len)

    dtype_map = {
        "int8": np.dtype("i1"),
        "int16": np.dtype("<i2"),
        "float32": np.dtype("<f4"),
    }
    dtype = dtype_map[metadata["dtype"]]
    audio = np.frombuffer(payload, dtype=dtype).reshape(metadata["shape"])

    sample_rate = int(metadata["sample_rate"])
    selected_channels = metadata["selected_channels"]
    print("sample_rate:", sample_rate)
    print("selected_channels:", selected_channels)
    print("audio shape:", audio.shape)
    return metadata, audio


def serve(host="192.168.2.141", port=50000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(5)
        print(f"listening on {host}:{port}")
        while True:
            conn, addr = server.accept()
            with conn:
                try:
                    metadata, audio = handle_client(conn)
                    print(f"received from {addr}: {metadata}")
                except Exception as exc:
                    print(f"failed to handle {addr}: {exc}")


if __name__ == "__main__":
    serve()
```

## 多通道说明

Server 端收到的 `audio` 始终是二维数组：

```text
audio[channel_index, sample_index]
```

例如 `shape = [2, 960000]` 表示 2 个通道，每个通道 960000 个采样点；在 `sample_rate = 16000` 时，对应 60 秒音频。调试时如果 `audio_interval_sec = 5`，则同采样率下单通道采样点数应为 `16000 * 5 = 80000`。

四通道时同样保持二维数组结构：

```text
audio.shape = [4, samples]

audio[0, :]  # 第 1 通道的所有采样点
audio[1, :]  # 第 2 通道的所有采样点
audio[2, :]  # 第 3 通道的所有采样点
audio[3, :]  # 第 4 通道的所有采样点
```

其中 `audio` 是二维数组，`audio[0, :]` 是取出单个通道后的所有采样点，因此是一维数组：

```text
audio.shape = [4, 960000]
audio[0, :].shape = [960000]
audio[0, 0]  # 单个采样值，不是数组
```

## 分段发送后拼接再做 STFT

Client 可以每隔 10 秒或 20 秒发送一次音频包，Server 端收到后按时间顺序拼接原始波形，再统一做 STFT。推荐先拼接时域音频，再做 STFT，不建议先对每个小包单独做 STFT 后再拼频谱，因为小包边界处可能受到窗函数和重叠长度影响。

拼接时要沿着采样点维度拼接，也就是第二维 `axis=1`：

```python
audio_all = np.concatenate([audio_1, audio_2], axis=1)
```

例如四通道、每包 60 秒、每通道 960000 个采样点：

```text
audio_1.shape = [4, 960000]
audio_2.shape = [4, 960000]

audio_all.shape = [4, 1920000]
```

Server 端拼接再做 STFT 时需要保证：

- 每个包的数据按时间连续，不能丢包、重复或乱序。
- 每个包的 `sample_rate` 一致，否则拼接后的时间轴和频率轴会不准确。
- 每个包的通道数量和通道顺序一致，例如始终保持 `0` 为第 1 通道、`1` 为第 2 通道。
- 每个包的 `dtype` 和位深度一致，避免拼接后数值含义不一致。

如果只是 10 秒或 20 秒分段传输，Server 端按 `axis=1` 拼接成连续二维数组后再做 STFT 是可以的。
