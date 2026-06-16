import os
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

IS_POSIX = os.name == "posix"
IS_NT = os.name == "nt"

if IS_NT:
    import _winapi
    from ctypes import wintypes

# ==========================================================================
# Unified Objects
# ==========================================================================


class UnifiedRuntimeError(Exception):
    """Exception raised for execution errors with dynamic case dictionary."""

    _cases = {
        "none_assignment": "Property/Attribute cannot be None: expected {expected}, got <{got}>",
        "unable_assignment": "Unable to assign type <{got}>: expected {expected}",
        "invalid_assignment": "Invalid Assignment: expected {expected}, cannot use <{got}>",
        "index_not_found": "Index not found in <type {got}>",
        "invalid_type": "Trying to set invalid type of <{got}>, but is expected <{expected}>",
        "empty_value_error": "Arguments collection cannot be empty",
    }

    def __init__(self, case: str, obj: object, *expected: type) -> None:
        expected_types = ", ".join(f"<{t.__name__}>" for t in expected)
        got_type = type(obj).__name__
        template = self._cases.get(case, "Unknown error case with <{got}>")
        self.message = template.format(expected=expected_types, got=got_type)
        super().__init__(self.message)


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
        hDefEnv: dict | None = None,
        lpAttributeList: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()

        if IS_NT:
            self["dwFlags"] = dwFlags | (
                _winapi.STARTF_USESTDHANDLES
                if (hStdInput or hStdOutput or hStdError)
                else 0
            )
            self["hStdInput"] = (
                hStdInput
                if hStdInput is not None
                else _winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)
            )
            self["hStdOutput"] = (
                hStdOutput
                if hStdOutput is not None
                else _winapi.GetStdHandle(_winapi.STD_OUTPUT_HANDLE)
            )
            self["hStdError"] = (
                hStdError
                if hStdError is not None
                else _winapi.GetStdHandle(_winapi.STD_ERROR_HANDLE)
            )
            self["wShowWindow"] = wShowWindow
            if lpAttributeList is not None:
                self["lpAttributeList"] = lpAttributeList
        else:
            self["hStdInput"] = hStdInput if hStdInput is not None else 0
            self["hStdOutput"] = hStdOutput if hStdOutput is not None else 1
            self["hStdError"] = hStdError if hStdError is not None else 2
            self["hDefEnv"] = hDefEnv

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

    def _nt_read(handle: int, buffer_size: int = 4096) -> tuple[bytes, int | None]:
        """NT chunk read from stream source"""
        try:
            res, _ = _winapi.ReadFile(handle, buffer_size)
            return res, handle
        except (BrokenPipeError, OSError):
            return b"", None

    def _nt_spawn_process(
        cmd: str | Path, args: list[str], env: dict[str, str] | None, si: StartUpInfo
    ) -> tuple[int, int]:
        """NT spawn process"""
        cmd_line = f'"{cmd}" ' + " ".join(f'"{a}"' if " " in a else a for a in args)
        cwd = si.get("pCwdDir", None)
        hp, ht, pid, _ = _winapi.CreateProcess(
            None, cmd_line, None, None, True, 0, env, cwd, si
        )
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

    def _posix_read(
        descriptor: int, buffer_size: int = 4096
    ) -> tuple[bytes, int | None]:
        """Read posix chunk from stream source"""
        try:
            return os.read(descriptor, buffer_size), None
        except (BrokenPipeError, OSError):
            return b"", None

    def _posix_spawn_process(
        cmd: str | Path, args: list[str], env: dict[str, str] | None, si: StartUpInfo
    ) -> tuple[int, int]:
        """Posix high-performance process spawning via native posix_spawn syscall"""
        _prog = str(cmd)
        _args = [_prog] + args

        executable = shutil.which(_prog) if not isinstance(cmd, Path) else _prog
        if not executable:
            sys.exit(127)

        stdout = si.get("hStdOutput")
        stdin = si.get("hStdInput")
        stderr = si.get("hStdError")
        cwd = si.get("pCwdDir")
        old_cwd = None

        if cwd is not None:
            try:
                old_cwd = os.getcwd()
                os.chdir(cwd)
            except Exception:
                sys.exit(127)

        file_actions = []
        if stdin is not None:
            file_actions.append((os.POSIX_SPAWN_DUP2, stdin, 0))
        if stdout is not None:
            file_actions.append((os.POSIX_SPAWN_DUP2, stdout, 1))
        if stderr is not None:
            file_actions.append((os.POSIX_SPAWN_DUP2, stderr, 2))

        _env = env if env is not None else os.environ

        try:
            pid = os.posix_spawn(executable, _args, _env, file_actions=file_actions)
        finally:
            if old_cwd is not None:
                os.chdir(old_cwd)

        return pid, 0

# ==========================================================================
# Unified Interface
# ==========================================================================


def close(handle_or_descriptor: int | None) -> None:
    """Close native subsystem resource descriptor"""
    if handle_or_descriptor is not None and handle_or_descriptor != -1:
        _close = _nt_close if IS_NT else _posix_close
        _close(handle_or_descriptor)


def read(
    handle_or_descriptor: int, buffer_size: int = 4096
) -> tuple[bytes, int | None]:
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


def spawn(
    cmd: str | Path, args: list[str], env: dict[str, str] | None, si: StartUpInfo
) -> tuple[int, int]:
    """Spawn a low level system process with unified lifecycle signature"""
    _spawn = _nt_spawn_process if IS_NT else _posix_spawn_process
    return _spawn(cmd, args, env, si)


def check_all(iterable: Iterable[Any], *args: type) -> Iterable[Any]:
    """Validate all types within a collection pipeline"""
    for v in iterable:
        if not isinstance(v, args):
            raise UnifiedRuntimeError("unable_assignment", v, *args)
        yield v
