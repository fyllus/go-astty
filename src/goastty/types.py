import asyncio
import os
from pathlib import Path
from typing import Self

from ._errors import ExecutionError

if os.name == "nt":
    from ._platform import ntapi as _platform
else:
    from ._platform import posixapi as _platform

# ==========================================================================
# Structures
# ==========================================================================


class Handle:
    """Lifecycle controller for asynchronous process tracking and channel descriptors"""

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
        if isinstance(other, Handle):
            return self.fd == other.fd
        if isinstance(other, int):
            return self.fd == other
        return False

    def close(self) -> None:
        """Destroy resource context on native system operational layer"""
        if not self._closed and self.fd != -1:
            self._closed = True
            _platform.close(self.fd)

    def read(self, buffer_size: int = 4096) -> tuple[bytes, int | None]:
        """Consume data block from active channel descriptor"""
        return _platform.read(self.fd, buffer_size)

    def sync_waitpid(self, options: int = 0) -> tuple["Handle", int]:
        """Verify tracking target process execution state once"""
        pid, status = _platform.waitpid(self.fd, options)
        if pid != 0:
            self._completed = True
        return Handle(pid), status

    async def async_waitpid(
        self, options: int = 0, time_sleep: float = 0.01
    ) -> tuple["Handle", int]:
        """Await standard process termination via non-blocking pool loop"""
        while not self._completed:
            pid, status = self.sync_waitpid(options)
            if self._completed:
                return pid, status
            await asyncio.sleep(time_sleep)
        return Handle(self.fd), 0

    def __bool__(self) -> bool:
        return not self._closed or self._completed


class Buffer(bytearray):
    """_platform internal extensible I/O data cache container"""

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
        handle_or_descriptor: int | Handle,
        buffer_size: int = 4096,
        autoclose: bool = False,
    ) -> None:
        """Universal synchronous stream reader loop"""
        is_handle = isinstance(handle_or_descriptor, Handle)

        if is_handle:
            while True:
                chunk, _ = handle_or_descriptor.read(buffer_size)
                if not chunk:
                    break
                self.extend(chunk)
        else:
            fd = int(handle_or_descriptor)
            while True:
                raw, _ = _platform.read(fd, buffer_size)
                if not raw:
                    break
                self.extend(raw)

        if autoclose:
            if is_handle:
                handle_or_descriptor.close()
            else:
                _platform.close(int(handle_or_descriptor))

    async def async_read(
        self,
        handle_or_descriptor: int | Handle,
        buffer_size: int = 4096,
        autoclose: bool = False,
    ) -> None:
        """Universal asynchronous stream reader loop"""
        is_handle = isinstance(handle_or_descriptor, Handle)
        loop = asyncio.get_running_loop()

        if is_handle:
            while True:
                chunk, _ = await loop.run_in_executor(
                    None, handle_or_descriptor.read, buffer_size
                )
                if not chunk:
                    break
                self.extend(chunk)
        else:
            fd = int(handle_or_descriptor)
            while True:
                raw, _ = await loop.run_in_executor(
                    None, _platform.read, fd, buffer_size
                )
                if not raw:
                    break
                self.extend(raw)

        if autoclose:
            if is_handle:
                handle_or_descriptor.close()
            else:
                _platform.close(int(handle_or_descriptor))


class Collector(dict):
    """Storage map routing for standard I/O bytearray pipelines"""

    def __new__(cls) -> Self:
        obj = super().__new__(cls)
        super(dict, obj).__init__()
        dict.__setitem__(obj, "stdout", Buffer())
        dict.__setitem__(obj, "stderr", Buffer())
        dict.__setitem__(obj, "stdin", Buffer())
        return obj

    @property
    def stdout(self) -> Buffer:
        return self["stdout"]

    @property
    def stderr(self) -> Buffer:
        return self["stderr"]

    @property
    def stdin(self) -> Buffer:
        return self["stdin"]

    def __setitem__(self, key: str, value: Buffer) -> None:
        if not isinstance(value, Buffer):
            raise ExecutionError("invalid_assignment", value, Buffer)
        if key not in self:
            raise ExecutionError("index_not_found", key, str)
        super().__setitem__(key, value)


class Task(list):
    """Task IO structure controller"""

    def __init__(self, cmd: str | Path, *args: str) -> None:
        """Initialize core argument list payload"""
        self.data = Collector()
        self.config = _platform.StartUpInfo()

        # eliminate _build_ to keep init clean and direct
        if all(isinstance(arg, str) for arg in args):
            _args = list(args)
        else:
            raise ExecutionError("all_must_be", args, str)

        if isinstance(cmd, (str, Path)):
            _cmd = [cmd]
        else:
            raise ExecutionError("invalid_type", cmd, Path)

        super().__init__(_cmd + _args)

    # ==================== getters =========================
    # turn  all into simple getter methods
    def cmd(self) -> str | Path:
        """Root binary target path: Path or String"""
        return self[0] if self else ""

    def args(self) -> list[str]:
        """Complete parameter argument sequence"""
        return self[1:] if len(self) > 1 else [""]

    def stdout(self) -> Buffer:
        """Cumulative stream output buffer"""
        return self.data["stdout"]

    def stdin(self) -> Buffer:
        """Cumulative stream input buffer"""
        return self.data["stdin"]

    def stderr(self) -> Buffer:
        """Cumulative stream error buffer"""
        return self.data["stderr"]

    def env(self, env: dict) -> None:
        """Set envirionment into config"""
        if not env or not isinstance(env, dict):
            raise ExecutionError("unable_assignment", env, dict)
        self.config["hDefEnv"] = env

    # ================ methods =======================

    def __str__(self) -> str:
        return " ".join(f'"{a}"' if " " in a else a for a in self)


class Gateway:
    """Process state boundary and low-level IO descriptor keeper"""

    def __init__(self, get_stderr: bool = False) -> None:
        _out_r, _out_w = _platform.pipe()
        self.stdout_reader = Handle(_out_r)
        self.stdout_writer = Handle(_out_w)

        if get_stderr:
            _err_r, _err_w = _platform.pipe()
            self.stderr_reader = Handle(_err_r)
            self.stderr_writer = Handle(_err_w)

    @property
    def pid(self) -> Handle:
        return getattr(self, "_pid", Handle(-1000))

    if os.name == "nt":

        @property
        def handle(self) -> Handle:
            return getattr(self, "_handle", Handle(-1000))
