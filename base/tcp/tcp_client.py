import argparse
import json
import socket
import sys
from typing import Optional


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

    def _send_payload(self, payload_bytes: bytes) -> Optional[bytes]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout_sec)
            # 绑定本地地址与端口（如果指定）
            if self.bind_host or self.bind_port:
                local_host = self.bind_host or "0.0.0.0"
                local_port = self.bind_port or 0
                sock.bind((local_host, int(local_port)))

            # 连接服务端
            sock.connect((self.server_host, int(self.server_port)))

            # 发送数据（封装）
            if self.framing == "length":
                length_prefix = len(payload_bytes).to_bytes(4, byteorder="big", signed=False)
                sock.sendall(length_prefix + payload_bytes)
            elif self.framing == "newline":
                sock.sendall(payload_bytes + b"\n")
            else:
                sock.sendall(payload_bytes)

            if not self.wait_response:
                return None
            return self._read_response(sock)

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
        except Exception:
            pass
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
        return 2


if __name__ == "__main__":
    sys.exit(main())


