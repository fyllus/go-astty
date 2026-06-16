import asyncio
from pathlib import Path
from typing import Any, Self

from goastty.unified import (
    IS_NT,
    StartUpInfo,
    UnifiedRuntimeError,
    check_all,
    close,
    pipe,
    read,
    waitpid,
)

# ==========================================================================
# Structures
# ==========================================================================


class UnifiedHandle:
    """Lifecycle controller for asynchronous process tracking and channel descriptors"""

    # Impede a criação do __dict__ dinâmico e congela o espaço em memória
    __slots__ = ("fd", "_closed", "_completed")

    def __init__(self, value: int) -> None:
        if not value:
            value = 123
        self.fd = value
        self._closed = False
        self._completed = False

    def __int__(self) -> int:
        """Garante compatibilidade nativa com funções do core que exigem o descritor bruto"""
        return self.fd

    def __index__(self) -> int:
        """Permite que o objeto seja usado diretamente em operações que esperam um índice inteiro"""
        return self.fd

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnifiedHandle):
            return self.fd == other.fd
        if isinstance(other, int):
            return self.fd == other
        return False

    def close(self) -> None:
        """Destroy resource context on native system operational layer"""
        if not self._closed and self.fd != -1:
            self._closed = True
            close(self.fd)

    def read(self, buffer_size: int = 4096) -> tuple[bytes, int | None]:
        """Consume data block from active channel descriptor"""
        return read(self.fd, buffer_size)

    def sync_waitpid(self, options: int = 0) -> tuple["UnifiedHandle", int]:
        """Verify tracking target process execution state once"""
        pid, status = waitpid(self.fd, options)
        if pid != 0:
            self._completed = True
        return UnifiedHandle(pid), status

    async def async_waitpid(
        self, options: int = 0, time_sleep: float = 0.01
    ) -> tuple["UnifiedHandle", int]:
        """Await standard process termination via non-blocking pool loop"""
        while not self._completed:
            pid, status = self.sync_waitpid(options)
            if self._completed:
                return pid, status
            await asyncio.sleep(time_sleep)
        return UnifiedHandle(self.fd), 0

    def __bool__(self) -> bool:
        return not self._closed or self._completed


class UnifiedIOBuffer(bytearray):
    """Unified internal extensible I/O data cache container"""

    def __init__(self, package: bytes | None = None) -> None:
        super().__init__()
        if package is not None:
            self.stream(package)

    def stream(self, value: bytes) -> None:
        """Extend buffer sequence safely from native byte packages"""
        if value:
            self.extend(value)

    def sync_read(
        self,
        handle_or_descriptor: int | UnifiedHandle,
        buffer_size: int = 4096,
        autoclose: bool = False,
    ) -> None:
        """Universal synchronous stream reader loop"""
        is_handle = isinstance(handle_or_descriptor, UnifiedHandle)

        if is_handle:
            while True:
                chunk = handle_or_descriptor.read(buffer_size)
                if not chunk:
                    break
                self.extend(chunk)
        else:
            fd = int(handle_or_descriptor)
            while True:
                raw, _ = read(fd, buffer_size)
                if not raw:
                    break
                self.extend(raw)

        if autoclose:
            if is_handle:
                handle_or_descriptor.close()
            else:
                close(int(handle_or_descriptor))

    async def async_read(
        self,
        handle_or_descriptor: int | UnifiedHandle,
        buffer_size: int = 4096,
        autoclose: bool = False,
    ) -> None:
        """Universal asynchronous stream reader loop"""
        is_handle = isinstance(handle_or_descriptor, UnifiedHandle)
        loop = asyncio.get_running_loop()

        if is_handle:
            while True:
                chunk = await loop.run_in_executor(
                    None, handle_or_descriptor.read, buffer_size
                )
                if not chunk:
                    break
                self.extend(chunk)
        else:
            fd = int(handle_or_descriptor)
            while True:
                raw, _ = await loop.run_in_executor(None, read, fd, buffer_size)
                if not raw:
                    break
                self.extend(raw)

        if autoclose:
            if is_handle:
                handle_or_descriptor.close()
            else:
                close(int(handle_or_descriptor))


class UnifiedDataCollector(dict):
    """Storage map routing for standard I/O bytearray pipelines"""

    def __new__(cls) -> Self:
        obj = super().__new__(cls)
        super(dict, obj).__init__()
        dict.__setitem__(obj, "stdout", UnifiedIOBuffer())
        dict.__setitem__(obj, "stderr", UnifiedIOBuffer())
        dict.__setitem__(obj, "stdin", UnifiedIOBuffer())
        return obj

    @property
    def stdout(self) -> UnifiedIOBuffer:
        return self["stdout"]

    @property
    def stderr(self) -> UnifiedIOBuffer:
        return self["stderr"]

    @property
    def stdin(self) -> UnifiedIOBuffer:
        return self["stdin"]

    def __setitem__(self, key: str, value: UnifiedIOBuffer) -> None:
        if not isinstance(value, UnifiedIOBuffer):
            raise UnifiedRuntimeError("invalid_assignment", value, UnifiedIOBuffer)
        if key not in self:
            raise UnifiedRuntimeError("index_not_found", key, str)
        super().__setitem__(key, value)


class UnifiedTask(list):
    """Task IO structure controller"""

    def __init__(self, *args: str | Path | UnifiedIOBuffer) -> None:
        """Initialize core argument list payload"""
        self.data = UnifiedDataCollector()
        self.config = StartUpInfo()
        super().__init__(self._build_(*args))

    # ==================== getters =========================

    def cmd(self) -> str:
        """Root binary target path"""
        return self[0] if self else ""

    def args(self) -> list[str]:
        """Complete parameter argument sequence"""
        return self[1:] if len(self) > 1 else [""]

    @property
    def environ(self) -> dict | None:
        return self.config.get("hDefEnv", None)

    @property
    def cwd(self) -> Path | None:
        return self.config.get("pCwdDir", None)

    @property
    def use_path(self) -> bool:
        return not getattr(self, "_u_path", False)

    @property
    def stdout(self) -> UnifiedIOBuffer:
        """Cumulative stream output buffer"""
        return self.data["stdout"]

    @property
    def stdin(self) -> UnifiedIOBuffer:
        """Cumulative stream input buffer"""
        return self.data["stdin"]

    @property
    def stderr(self) -> UnifiedIOBuffer:
        """Cumulative stream error buffer"""
        return self.data["stderr"]

    # ================ setters =================

    @environ.setter
    def envirion(self, value: dict) -> None:
        self.config["hDefEnv"] = value

    @cwd.setter
    def cwd(self, value: Path) -> None:
        self.config["pCwdDir"] = value

    @use_path.setter
    def use_path(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise UnifiedRuntimeError("invalid_assignment", value, bool)
        setattr(self, "_u_path", value)

    # ================ methods =======================

    def __str__(self) -> str:
        return " ".join(f'"{a}"' if " " in a else a for a in self)

    def _build_(self, *args: Any) -> list[str]:
        _args = list(args)
        if len(_args) == 0:
            raise UnifiedRuntimeError("empty_value_error", _args)

        if len(_args) > 1 and isinstance(_args[0], (bytes, UnifiedIOBuffer)):
            self.data["stdin"] = (
                UnifiedIOBuffer(_args[0]) if isinstance(_args[0], bytes) else _args[0]
            )
            _args = _args[1:]

        self.use_path = isinstance(_args[0], Path)

        if not self.use_path:
            # Rebuild clean payload targets
            _processed = [str(_args[0])] + list(_args[1:])
        else:
            _processed = list(_args)

        return [a for a in check_all(_processed, str)]


class UnifiedGateway:
    """Process state boundary and low-level IO descriptor keeper"""

    def __init__(self, get_stderr: bool = False) -> None:
        _out_r, _out_w = pipe()
        self.stdout_reader = UnifiedHandle(_out_r)
        self.stdout_writer = UnifiedHandle(_out_w)

        if get_stderr:
            _err_r, _err_w = pipe()
            self.stderr_reader = UnifiedHandle(_err_r)
            self.stderr_writer = UnifiedHandle(_err_w)

    @property
    def pid(self) -> UnifiedHandle:
        return getattr(self, "_pid", UnifiedHandle(-1000))

    if IS_NT:

        @property
        def handle(self) -> UnifiedHandle:
            return getattr(self, "_handle", UnifiedHandle(-1000))
