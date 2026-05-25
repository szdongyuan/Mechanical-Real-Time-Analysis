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
  "audio_interval_sec": 60
}
```

- `server_ip`: Server 监听 IP。
- `client_ip`: Client 发送前绑定的本机 IP。
- `port`: Server 监听端口，默认 `50000`。
- `enable_audio_tcp`: 是否启用音频 TCP 传输。
- `audio_interval_sec`: 音频发送间隔和单包音频时长，单位秒，默认 `60`，调试时可改小。

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
  "sample_rate": 44100,
  "channels": 2,
  "selected_channels": [0, 1],
  "dtype": "float32",
  "shape": [2, 2646000],
  "byte_order": "little",
  "duration_sec": 60.0,
  "payload_bytes": 21168000,
  "record_start_time": "20260525143000",
  "device_name": "Input Device"
}
```

字段说明：

- `sample_rate`: 当前录音采样率，Server 必须按该值解析音频时间轴。
- `channels`: 本次发送的通道数量。
- `selected_channels`: Client 端选择的原始输入通道索引，0 基。
- `dtype`: 固定为 `float32`。
- `shape`: 音频数组形状，固定为 `[channels, samples]`。
- `byte_order`: 固定为 `little`。
- `duration_sec`: 本次音频时长，对应配置中的 `audio_interval_sec`。
- `payload_bytes`: 原始音频字节长度，应等于 `channels * samples * 4`。

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

    dtype = np.dtype("<f4")
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

例如 `shape = [2, 2646000]` 表示 2 个通道，每个通道 2646000 个采样点；在 `sample_rate = 44100` 时，对应 60 秒音频。调试时如果 `audio_interval_sec = 5`，则同采样率下单通道采样点数应为 `44100 * 5 = 220500`。
