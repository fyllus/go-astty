import socket
from typing import Optional


class Socket:
    SOCK = ""

    def __init__(self) -> None:
        if not self.SOCK:
            raise RuntimeError("Socket path not found..")
        self._data = b""
        self._client: Optional[socket.socket] = None

    @property
    def data(self) -> bytes:
        return self._data

    @data.setter
    def data(self, value: bytes) -> None:
        if not isinstance(value, bytes):
            raise TypeError("Data must be <byte> type..")
        self._data = value

    def __enter__(self) -> "Socket":
        self._client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._client.connect(self.SOCK)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def up(self, hsize: int = 14) -> bytes:
        if self._client:
            self._client.sendall(self.data)
            return self._client.recv(hsize)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(self.SOCK)
            client.sendall(self.data)
            return client.recv(hsize)
