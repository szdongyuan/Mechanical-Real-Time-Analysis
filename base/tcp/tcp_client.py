import argparse
import json
import socket
import sys
import time
from typing import Optional

import numpy as np

from base.log_manager import LogManager

logger = LogManager.set_log_handler("core")


def estimate_tcp_send_timeout_sec(payload_bytes: int, *, min_sec: float = 30.0) -> float:
    """按 payload 大小估算发送超时，避免大包在慢链路上误报 timed out。"""
    nbytes = max(0, int(payload_bytes))
    # 按最低 256 KB/s 估算传输时间，并预留连接建立余量
    transfer_sec = nbytes / (256 * 1024) if nbytes > 0 else 0.0
    return max(float(min_sec), 15.0 + transfer_sec)


def _convert_audio_payload(audio_array, sample_bit_depth: int):
    bit_depth = int(sample_bit_depth)
    source = np.asarray(audio_array, dtype=np.float32)
    if bit_depth == 16:
        audio_data = np.ascontiguousarray(np.clip(source, -1.0, 1.0) * np.iinfo(np.int16).max, dtype="<i2")
        return audio_data, "int16", "little"
    if bit_depth == 8:
        audio_data = np.ascontiguousarray(np.clip(source, -1.0, 1.0) * np.iinfo(np.int8).max, dtype=np.int8)
        return audio_data, "int8", "not_applicable"
    if bit_depth == 32:
        audio_data = np.ascontiguousarray(source.astype("<f4", copy=False))
        return audio_data, "float32", "little"
    raise ValueError(f"不支持的 TCP 音频位深度: {sample_bit_depth}，仅支持 8/16/32")


class TcpClient:
    """
    简单的 TCP 客户端封装：
    - 支持可选本地端口绑定
    - 支持三种封装：newline / length / raw
    - 支持发送 dict 或 JSON 文件
    - 可选等待响应（按行或直到连接关闭）
    """

    def __init__(
        self,
        server_host: str,
        server_port: int,
        *,
        bind_host: Optional[str] = None,
        bind_port: Optional[int] = None,
        timeout_sec: float = 10.0,
        framing: str = "newline",
        wait_response: bool = True,
    ):
        self.server_host = server_host
        self.server_port = int(server_port)
        self.bind_host = bind_host
        self.bind_port = int(bind_port) if bind_port is not None else None
        self.timeout_sec = float(timeout_sec)
        self.framing = str(framing or "newline").lower()
        self.wait_response = bool(wait_response)

        if self.framing not in ("newline", "length", "raw"):
            raise ValueError(f"不支持的 framing: {self.framing}")

    def send_dict(self, data_obj: dict) -> Optional[bytes]:
        if not isinstance(data_obj, dict):
            raise TypeError("data_obj 必须是 dict")
        payload_text = json.dumps(data_obj, ensure_ascii=False, separators=(",", ":"))
        payload_bytes = payload_text.encode("utf-8")
        return self._send_payload(payload_bytes)

    def send_binary_packet(self, metadata: dict, payload_bytes: bytes) -> Optional[bytes]:
        if not isinstance(metadata, dict):
            raise TypeError("metadata 必须是 dict")
        if not isinstance(payload_bytes, (bytes, bytearray, memoryview)):
            raise TypeError("payload_bytes 必须是 bytes-like")
        metadata_bytes = json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        packet = len(metadata_bytes).to_bytes(4, byteorder="big", signed=False)
        packet += metadata_bytes
        packet += bytes(payload_bytes)
        return self._send_unframed_payload(packet)

    def send_audio_array(
        self,
        audio_array,
        sample_rate: int,
        selected_channels: list,
        *,
        timestamp: Optional[float] = None,
        duration_sec: Optional[float] = None,
        extra_metadata: Optional[dict] = None,
        sample_bit_depth: int = 32,
    ) -> Optional[bytes]:
        audio_data, dtype_name, byte_order = _convert_audio_payload(audio_array, sample_bit_depth)
        metadata = dict(extra_metadata or {}) if isinstance(extra_metadata, dict) else {}
        metadata.update({
            "type": "audio_data",
            "timestamp": float(timestamp if timestamp is not None else time.time()),
            "sample_rate": int(sample_rate),
            "channels": int(audio_data.shape[0]) if audio_data.ndim > 0 else 0,
            "selected_channels": list(selected_channels or []),
            "dtype": dtype_name,
            "shape": list(audio_data.shape),
            "byte_order": byte_order,
            "duration_sec": float(duration_sec if duration_sec is not None else 0.0),
            "payload_bytes": int(audio_data.nbytes),
        })
        return self.send_binary_packet(metadata, audio_data.tobytes(order="C"))

    def _log_send_complete(self, sock: socket.socket, nbytes: int, *, packet_type: str = "payload") -> None:
        local_host, local_port = sock.getsockname()
        msg = (
            f"TCP 发送完成并已关闭连接: {local_host}:{local_port} -> "
            f"{self.server_host}:{self.server_port}, {packet_type}={nbytes} 字节"
        )
        logger.info(msg)
        print(msg)

    def _send_payload(self, payload_bytes: bytes) -> Optional[bytes]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout_sec)
            # 绑定本地地址与端口（如果指定）
            if self.bind_host or self.bind_port:
                local_host = self.bind_host or "0.0.0.0"
                local_port = self.bind_port or 0
                sock.bind((local_host, int(local_port)))

            self._connect(sock)

            # 发送数据（封装）
            if self.framing == "length":
                length_prefix = len(payload_bytes).to_bytes(4, byteorder="big", signed=False)
                on_wire = length_prefix + payload_bytes
                self._send_all(sock, on_wire)
                sent_bytes = len(on_wire)
            elif self.framing == "newline":
                on_wire = payload_bytes + b"\n"
                self._send_all(sock, on_wire)
                sent_bytes = len(on_wire)
            else:
                self._send_all(sock, payload_bytes)
                sent_bytes = len(payload_bytes)

            if not self.wait_response:
                self._log_send_complete(sock, sent_bytes, packet_type=f"json({self.framing})")
                return None
            resp = self._read_response(sock)
            self._log_send_complete(sock, sent_bytes, packet_type=f"json({self.framing})")
            return resp

    def _connect(self, sock: socket.socket) -> None:
        target = f"{self.server_host}:{self.server_port}"
        try:
            sock.connect((self.server_host, int(self.server_port)))
        except socket.timeout as exc:
            raise TimeoutError(
                f"连接 {target} 超时（{self.timeout_sec:.0f}s），"
                f"请确认 Server 已在 {target} 监听且网络/防火墙可达"
            ) from exc
        except OSError as exc:
            raise ConnectionError(f"连接 {target} 失败: {exc}") from exc

    def _send_all(self, sock: socket.socket, payload_bytes: bytes) -> None:
        try:
            sock.sendall(payload_bytes)
        except socket.timeout as exc:
            raise TimeoutError(
                f"向 {self.server_host}:{self.server_port} 发送 {len(payload_bytes)} 字节超时"
                f"（{self.timeout_sec:.0f}s），请确认 Server 端正在 recv 读取完整数据包"
            ) from exc

    def _send_unframed_payload(self, payload_bytes: bytes) -> Optional[bytes]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout_sec)
            if self.bind_host or self.bind_port:
                local_host = self.bind_host or "0.0.0.0"
                local_port = self.bind_port or 0
                sock.bind((local_host, int(local_port)))
            self._connect(sock)
            self._send_all(sock, payload_bytes)
            sent_bytes = len(payload_bytes)
            if not self.wait_response:
                self._log_send_complete(sock, sent_bytes, packet_type="binary_packet")
                return None
            resp = self._read_response(sock)
            self._log_send_complete(sock, sent_bytes, packet_type="binary_packet")
            return resp

    def _read_response(self, sock: socket.socket) -> bytes:
        # 简单读取响应：优先按行读取（遇到换行停止），否则读到连接关闭
        sock.settimeout(self.timeout_sec)
        chunks = []
        try:
            # 尝试按行读取
            while True:
                b = sock.recv(1)
                if not b:
                    break
                chunks.append(b)
                if b == b"\n":
                    break
        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"Failed to read response: {e}")
        return b"".join(chunks) if chunks else b""


def send_dict(
    server_host: str,
    server_port: int,
    data_obj: dict,
    bind_host: Optional[str] = None,
    bind_port: Optional[int] = None,
    timeout_sec: float = 10.0,
    framing: str = "newline",
    wait_response: bool = True,
) -> Optional[bytes]:
    """
    发送 Python dict 到指定 TCP 服务端。
    其他参数语义与 send_json_file 一致。
    """
    client = TcpClient(
        server_host=server_host,
        server_port=server_port,
        bind_host=bind_host,
        bind_port=bind_port,
        timeout_sec=timeout_sec,
        framing=framing,
        wait_response=wait_response,
    )
    return client.send_dict(data_obj)


def send_audio_array(
    server_host: str,
    server_port: int,
    audio_array,
    sample_rate: int,
    selected_channels: list,
    bind_host: Optional[str] = None,
    bind_port: Optional[int] = None,
    timeout_sec: float = 10.0,
    wait_response: bool = False,
    duration_sec: Optional[float] = None,
    extra_metadata: Optional[dict] = None,
    sample_bit_depth: int = 32,
) -> Optional[bytes]:
    client = TcpClient(
        server_host=server_host,
        server_port=server_port,
        bind_host=bind_host,
        bind_port=bind_port,
        timeout_sec=timeout_sec,
        framing="raw",
        wait_response=wait_response,
    )
    return client.send_audio_array(
        audio_array,
        sample_rate,
        selected_channels,
        duration_sec=duration_sec,
        extra_metadata=extra_metadata,
        sample_bit_depth=sample_bit_depth,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="TCP JSON 客户端：发送 JSON 文件到服务端")
    p.add_argument("--server-host", required=True, help="服务端主机/IP，例如 127.0.0.1")
    p.add_argument("--server-port", type=int, required=True, help="服务端端口，例如 9000")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--path", help="待发送的 JSON 文件路径")
    group.add_argument("--data", help="直接发送的 JSON 字符串，例如 '{\"a\":1}'")
    p.add_argument("--bind-host", default=None, help="本地绑定主机（可选），例如 0.0.0.0")
    p.add_argument("--bind-port", type=int, default=None, help="本地绑定端口（可选）")
    p.add_argument("--timeout", type=float, default=10.0, help="连接与读写超时（秒），默认 10")
    p.add_argument(
        "--framing",
        choices=("newline", "length", "raw"),
        default="newline",
        help="发送协议封装：newline(默认)/length/raw",
    )
    p.add_argument(
        "--no-wait",
        action="store_true",
        help="发送后不等待服务端响应（默认等待）",
    )
    return p


def main(argv=None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.data is not None:
            try:
                data_obj = json.loads(args.data)
                if not isinstance(data_obj, dict):
                    raise ValueError("通过 --data 提供的 JSON 必须是对象类型（dict）")
            except Exception as e:
                raise ValueError(f"--data 解析失败: {e}") from e
            resp = send_dict(
                server_host=args.server_host,
                server_port=args.server_port,
                data_obj=data_obj,
                bind_host=args.bind_host,
                bind_port=args.bind_port,
                timeout_sec=args.timeout,
                framing=args.framing,
                wait_response=not args.no_wait,
            )
        if resp is not None:
            # 尝试按 UTF-8 输出响应
            try:
                print(resp.decode("utf-8", errors="replace").rstrip("\n"))
            except Exception:
                # 回退为原始字节的 repr
                print(repr(resp))
        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        logger.error(f"Failed to send dict: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())


