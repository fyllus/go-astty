import _winapi
import asyncio
from asyncio.events import Handle
import os
import sys
from ctypes import WinDLL, windll, wintypes
from pathlib import Path
from typing import Any

IS_POSIX = os.name == 'posix'
IS_NT = os.name == 'nt'

# ==========================================================================
# Unified Objects
# ==========================================================================
class ExecutionError(Exception):
    """Exception raised for execution errors."""
    def __init__(self, case: str, obj: object, *expected: type) -> None:
        expected_types = ", ".join(f"<{t.__name__}>" for t in expected)
        self._cases = {
            'none_assignment': f'Property/Attribute cannot be None: expected {expected_types}, got <{type(obj).__name__}>',
            'unable_assignment': f'Unable to assign type <{type(obj).__name__}>: expected {expected_types}',
            'invalid_assignment': f'Invalid Assignment: expected {expected_types}, cannot use <{type(obj).__name__}>'
        }
        super().__init__(self._cases.get(case, f"Unknown error case with <{type(obj)}>"))


class StartUpInfo(dict):
    """STARTUPINFO structure wrapper as universal metadata dictionary"""
    def __init__(
        self,
        *,
        dwFlags: int = 0,
        hStdInput: int | None = None,
        hStdOutput: int | None = None,
        hStdError: int | None = None,
        wShowWindow: int = 0,
        pCwdDir: str | Path | None = None,
        lpAttributeList: dict[str, Any] | None = None
    ) -> None:
        super().__init__()

        if IS_NT:
            self["dwFlags"] = dwFlags | (_winapi.STARTF_USESTDHANDLES if \
            (hStdInput or hStdOutput or hStdError) else 0)

            self["hStdInput"] = hStdInput if hStdInput is not None else\
            _winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)

            self["hStdOutput"] = hStdOutput if hStdOutput is not None else\
            _winapi.GetStdHandle(_winapi.STD_OUTPUT_HANDLE)

            self["hStdError"] = hStdError if hStdError is not None else\
            _winapi.GetStdHandle(_winapi.STD_ERROR_HANDLE)

            self["wShowWindow"] = wShowWindow
            if lpAttributeList is not None:
                self["lpAttributeList"] = lpAttributeList
        else:
            self["hStdInput"] = hStdInput if hStdInput is not None else 0
            self["hStdOutput"] = hStdOutput if hStdOutput is not None else 1
            self["hStdError"] = hStdError if hStdError is not None else 2

        if pCwdDir is not None:
            self["pCwdDir"] = pCwdDir

# ==========================================================================
# Design Remapping
# ==========================================================================

if IS_NT:
    NT_BOOL = wintypes.BOOL
    NT_BOOLEAN = wintypes.BOOLEAN
    NT_CHAR = wintypes.CHAR
    NT_ATOM = wintypes.ATOM
    NT_BYTE = wintypes.BYTE
    NT_DOUBLE = wintypes.DOUBLE
    NT_DWORD = wintypes.DWORD
    NT_INFINITE = _winapi.INFINITE
    NT_WAIT_OBJECT_0 = _winapi.WAIT_OBJECT_0

    def _nt_close(handle: int) -> None:
        """NT handle close"""
        try:
            _winapi.CloseHandle(handle)
        except OSError:
            pass

    def _nt_pipe(attr: Any, size: int | None) -> tuple[int, int]:
        """NT pipeline creator"""
        return _winapi.CreatePipe(attr, size if size is not None else 0)

    def _nt_waitpid(handle: int, opt: int = 0) -> tuple[int, int]:
        """NT wait for process handle to terminate"""
        timeout = 0 if opt == 1 else NT_INFINITE
        if _winapi.WaitForSingleObject(handle, timeout) == NT_WAIT_OBJECT_0:
            return handle, _winapi.GetExitCodeProcess(handle)
        return 0, 0

    def _nt_read(handle: int, buffer_size: int = 4096):
        """NT posix chunk from stream source"""
        try:
            return _winapi.ReadFile(handle, buffer_size)
        except (BrokenPipeError, OSError):
            return b'', None

    def _nt_spawn_process(
        cmd: str | Path, args: list[str], env: dict[str, str] | None, si: StartUpInfo
    ) -> tuple[int, int]:
        """NT spawn process"""
        cmd_line = f'"{cmd}" ' + " ".join(f'"{a}"' if " " in a else a for a in args)
        cwd = si.get('pCwdDir', None)
        hp, ht, pid, _ = _winapi.CreateProcess(None, cmd_line, None, None, True, 0, env , cwd, si)
        _nt_close(ht)
        return pid, hp

if IS_POSIX:
    def _posix_close(descriptor: int) -> None:
        """Posix descriptor close"""
        try:
            os.close(descriptor)
        except OSError:
            pass

    def _posix_pipe(attr: Any, size: int | None) -> tuple[int, int]:
        """Posix pipeline creator"""
        return os.pipe()

    def _posix_waitpid(pid: int, opt: int = 0) -> tuple[int, int]:
        """Posix wait for process id terminate"""
        try:
            return os.waitpid(pid, opt)
        except ChildProcessError:
            return pid, 0

    def _posix_read(descriptor: int, buffer_size: int = 4096):
        """Read posix chunk from stream source"""
        try:
            return os.read(descriptor, buffer_size), None
        except (BrokenPipeError, OSError):
            return b'', None

    def _posix_spawn_process(
        cmd: str | Path, args: list[str], env: dict[str, str] | None, si: StartUpInfo
        ) -> tuple[int, int]:
        """Posix adapted spawn process to follow NT design"""

        # extract redirections
        stdout = si.get('hStdOutput', None)
        stdin = si.get('hStdInput', None)
        stderr = si.get('hStdError', None)

        # get work dir
        cwd = si.get('pCwdDir', None)

        # fork and simulate NT process creation
        pid = os.fork()
        if pid == 0:
            # NOTE: to change cwd we use chdir
            if cwd is not None:
                try:
                    os.chdir(cwd)
                except Exception:
                    sys.exit(127)

            # NOTE: make redirections manually
            if stdin is not None:
                os.dup2(stdin, 0)
            if stdout is not None:
                os.dup2(stdout, 1)
            if stderr is not None:
                os.dup2(stderr, 2)

            # NOTE: execution of process as NT design
            try:
                _prog = str(cmd)
                _func = "execv"

                # build options for execution way
                if not isinstance(cmd, Path):
                    _func += "p"
                _args = [_prog] + args

                if env is not None:
                    _func += 'e'
                    func = getattr(os, _func)
                    # execute as: execv(p)e
                    func(_prog, _args, env)
                else:
                    # execute as: execv(p)
                    func = getattr(os, _func)
                    func(_prog, _args)
            except Exception:
                sys.exit(127)

        return pid, 0

# ==========================================================================
# Unified Interface
# ==========================================================================

def close(handle_or_descriptor: int | None) -> None:
    """Close native subsystem resource descriptor"""
    if handle_or_descriptor is not None and handle_or_descriptor != -1:
        _close = _nt_close if IS_NT else _posix_close
        _close(handle_or_descriptor)

def read(handle_or_descriptor: int, buffer_size: int = 4096):
    """Read low level chunk from stream source"""
    _read = _nt_read if IS_NT else _posix_read
    return _read(handle_or_descriptor, buffer_size)

def pipe(attr: Any = None, size: int | None = None) -> tuple[int, int]:
    """Create os specific anonymous pipeline channel"""
    _pipe = _nt_pipe if IS_NT else _posix_pipe
    return _pipe(attr, size)

def waitpid(handle_or_descriptor: int, options: int = 0) -> tuple[int, int]:
    """Wait for a specific process identifier or handle to terminate"""
    _waitpid = _nt_waitpid if IS_NT else _posix_waitpid
    return _waitpid(handle_or_descriptor, options)

def spawn(cmd: str | Path, args: list[str], env: dict[str, str] | None, si: StartUpInfo) -> tuple[int, int]:
    """Spawn a low level system process with unified lifecycle signature"""
    _spawn = _nt_spawn_process if IS_NT else _posix_spawn_process
    return _spawn(cmd, args, env, si)

# ==========================================================
# Structures
# ==========================================================

class UnifiedBytes:
    """Immutable bytes sequence carrying reference tracking origin"""
    def __init__(self, init_byte: bytes | None, handle: int | None) -> None:
        if handle:
            self.handle = handle
        if init_byte:
            self.byte = init_byte

    def has_byte(self) -> bool:
        """Evaluate if payload contains readable allocated data"""
        return hasattr(self, 'byte') and bool(getattr(self, 'byte', None))

    def has_handle(self) -> bool:
        """Evaluate if resource origin handle context is valid"""
        return hasattr(self, 'handle') and getattr(self, 'handle', None) is not None

    def __bool__(self) -> bool:
        return self.has_byte()


class UnifiedHandle(int):
    """Lifecycle controller for asynchronous process tracking and channel descriptors"""
    def __new__(cls, value):
        obj = super().__new__(cls, value)
        obj._closed = False
        obj._completed = False
        return obj

    def close(self) -> None:
        """Destroy resource context on native system operational layer"""
        if not self._closed and self != -1:
            self._closed = True
            close(self)

    def read(self, buffer_size: int = 4096) -> UnifiedBytes:
        """Consume data block from active channel descriptor"""
        return UnifiedBytes(*read(self, buffer_size))

    def sync_waitpid(self, options: int = 0) -> tuple['UnifiedHandle', int]:
        """Verify tracking target process execution state once"""
        pid, status = waitpid(self, options)
        if pid != 0:
            self._completed = True
        return type(self)(pid), status

    async def async_waitpid(self, options: int = 0, time_sleep: float = 0.01) -> tuple['UnifiedHandle', int]:
        """Await standard process termination via non-blocking pool loop"""
        while not self._completed:
            pid, status = self.sync_waitpid(options)
            if self._completed:
                return pid, status
            await asyncio.sleep(time_sleep)
        return type(self)(self), 0

    def __bool__(self) -> bool:
        return not self._closed or self._completed


class UnifiedIOBuffer(bytearray):
    def __init__(self, package: bytes | UnifiedBytes | None = None) -> None:
        super().__init__()
        if package is not None:
            self.stream(package)

    def stream(self, value: UnifiedBytes | bytes | asyncio.Future[UnifiedBytes]) -> None:
        if not value:
            pass
        elif isinstance(value, UnifiedBytes):
            self.extend(value.byte)
        elif isinstance(value, bytes):
            self.extend(value)
        else:
            raise ExecutionError('invalid_assignment', value, bytes, UnifiedBytes)

    def sync_read(self, handle_or_descriptor: int | UnifiedHandle, buffer_size: int = 4096, autoclose: bool = False):
        """Universal synchronous stream reader loop"""
        if not isinstance(handle_or_descriptor, (int, UnifiedHandle)):
            raise ExecutionError('invalid_assignment', handle_or_descriptor, int, UnifiedHandle)

        while True:
            if isinstance(handle_or_descriptor, UnifiedHandle):
                chunk = handle_or_descriptor.read(buffer_size)
            elif isinstance(handle_or_descriptor, int):
                chunk, _ = read(handle_or_descriptor, buffer_size)
            if not chunk:
                break
            self.stream(chunk)

        if autoclose:
            if isinstance(handle_or_descriptor, UnifiedHandle)
                handle_or_descriptor.close()
            else:
                close(handle_or_descriptor)

    async def async_read(self, handle_or_descriptor: int | UnifiedHandle, buffer_size: int = 4096, autoclose: bool = False):
        """Universal asynchronous stream reader loop"""
        if not isinstance(handle_or_descriptor, (int, UnifiedHandle)):
            raise ExecutionError('invalid_assignment', handle_or_descriptor, int, UnifiedHandle)

        loop = asyncio.get_running_loop()
        while True:
            if isinstance(handle_or_descriptor, UnifiedHandle):
                chunk = loop.run_in_executor(None, handle_or_descriptor.read, buffer_size)
            elif isinstance(handle_or_descriptor, int):
                chunk, _ = loop.run_in_executor(None, read, handle_or_descriptor, buffer_size)
            if not chunk:
                break
            self.stream(chunk)

        if autoclose:
            if isinstance(handle_or_descriptor, UnifiedHandle)
                handle_or_descriptor.close()
            else:
                close(handle_or_descriptor)
