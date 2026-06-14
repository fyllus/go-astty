import asyncio
import ctypes
import os
import sys
from abc import ABC, abstractmethod
from typing import Any

is_nt = os.name == 'nt'
is_posix = os.name == 'posix'

class AssignmentError(Exception):
    """Exception raised for invalid property or attribute assignments."""
    def __init__(self, case: str, obj: object, *expected: type) -> None:
        expected_types = ", ".join(f"<{t.__name__}>" for t in expected)
        self._cases = {
            'none': f'Property/Attribute cannot be None: expected {expected_types}, got <{type(obj).__name__}>',
            'unable': f'Unable to assign type <{type(obj).__name__}>: expected {expected_types}',
            'invalid': f'Invalid Assignment: expected {expected_types}, cannot use <{type(obj).__name__}>'
        }
        super().__init__(self._cases.get(case, f"Unknown error case with type <{type(obj).__name__}>"))

PIPE = -1
STDOUT = -2
DEVNULL = -3

if is_nt:
    # ============= win32 / nt const re-mapping and helpers creation ==================
    import _winapi
    from ctypes import wintypes

    W_BYTE = wintypes.BYTE
    W_BOOL = wintypes.BOOL
    W_DWORD = wintypes.DWORD
    W_HANDLE = wintypes.HANDLE
    HANDLE_FLAG_INHERIT = 0x00000001
    HANDLE_FLAG_PROTECT_FROM_CLOSE = 0x00000002
    W_INFINITE = _winapi.INFINITE

    kernel_win32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel_win32.SetHandleInformation.argtypes = [W_HANDLE, W_DWORD, W_DWORD]
    kernel_win32.SetHandleInformation.restype = W_BOOL

    class ProcessParam(dict):
        """Windows CreateProcess parameters wrapper as native dictionary"""
        def __init__(
            self,
            *,
            application_name: str | None = None,
            command_line: str | None = None,
            proc_attrs: Any = None,
            thread_attrs: Any = None,
            inherit_handles: bool = True,
            creation_flags: int = 0,
            env_mapping: dict[str, str] | None = None,
            current_directory: str | None = None,
            startup_info: Any = None
        ) -> None:
            super().__init__()
            self['application_name'] = application_name
            self['command_line'] = command_line
            self['proc_attrs'] = proc_attrs
            self['thread_attrs'] = thread_attrs
            self['inherit_handles'] = inherit_handles
            self['creation_flags'] = creation_flags
            self['env_mapping'] = env_mapping
            self['current_directory'] = current_directory
            self['startup_info'] = startup_info

    class StartUpInfo(dict):
        """Windows STARTUPINFO structure wrapper as native dictionary"""
        def __init__(
            self,
            *,
            dwFlags: int = 0,
            hStdInput: int | None = None,
            hStdOutput: int | None = None,
            hStdError: int | None = None,
            wShowWindow: int = 0,
            lpAttributeList: dict[str, Any] | None = None
        ) -> None:
            super().__init__()
            self["dwFlags"] = dwFlags
            self["hStdInput"] = hStdInput if hStdInput is not None else _winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)
            self["hStdOutput"] = hStdOutput if hStdOutput is not None else _winapi.GetStdHandle(_winapi.STD_OUTPUT_HANDLE)
            self["hStdError"] = hStdError if hStdError is not None else _winapi.GetStdHandle(_winapi.STD_ERROR_HANDLE)
            self["wShowWindow"] = wShowWindow
            if lpAttributeList is not None:
                self["lpAttributeList"] = lpAttributeList

if is_posix:
    # ============= Posix const re-mapping =====================
    WNOHANG = os.WNOHANG
    WNOWAIT = os.WNOWAIT
    WSTOPPED = os.WSTOPPED
    WCONTINUED = os.WCONTINUED


# ==========================================================================
# Global Functions
# ==========================================================================
def pipe(pipe_attr: Any = None, size: int = 0) -> tuple[int, int]:
    """Create os specific anonymous pipeline channel"""
    if is_nt:
        return _winapi.CreatePipe(pipe_attr, size)
    return os.pipe()

def close(handle_or_fd: int | None) -> None:
    """Close native subsystem resource descriptor"""
    if handle_or_fd is not None and handle_or_fd != -1:
        if is_nt:
            _winapi.CloseHandle(handle_or_fd)
        else:
            os.close(handle_or_fd)

def fork(param: ProcessParam | None = None) -> tuple[int | None, int | None, int, Any]:
    """Execute target execution lifecycle division"""
    if is_nt:
        p = param or {}
        hp, ht, pid, thid = _winapi.CreateProcess(
            p.get('application_name'), p.get('command_line'), p.get('proc_attrs'),
            p.get('thread_attrs'), p.get('inherit_handles', True), p.get('creation_flags', 0),
            p.get('env_mapping'), p.get('current_directory'), p.get('startup_info')
        )
        return hp, ht, pid, thid
    return None, None, os.fork(), None

def waitpid(pid_or_handle: int, options: int = 0) -> tuple[int, int]:
    """Wait for a specific process identifier or handle to terminate"""
    if is_nt:
        timeout = 0 if options == 1 else _winapi.INFINITE
        if _winapi.WaitForSingleObject(pid_or_handle, timeout) == _winapi.WAIT_OBJECT_0:
            return pid_or_handle, 0
        return 0, 0
    try:
        return os.waitpid(pid_or_handle, options)
    except ChildProcessError:
        return pid_or_handle, 0

def duplicate(source_fd: int, target_fd: int = 1, inheritable: bool = True) -> int:
    """Duplicate native descriptor redirection targets"""
    if is_nt:
        mask = HANDLE_FLAG_INHERIT
        flags = HANDLE_FLAG_INHERIT if inheritable else 0
        if not kernel_win32.SetHandleInformation(source_fd, mask, flags):
            raise ctypes.WinError(ctypes.get_last_error())
        return source_fd
    return os.dup2(source_fd, target_fd, inheritable=inheritable)

def predirect(handle_or_fd: int) -> Any:
    """Redirect standard output and error descriptors"""
    if is_posix:
        try:
            os.dup2(handle_or_fd, 1)
            os.dup2(handle_or_fd, 2)
            os.close(handle_or_fd)
            return True, None
        except Exception as err:
            return False, err
    return True, StartUpInfo(hStdOutput=handle_or_fd, hStdError=handle_or_fd)

def read(handle_or_fd: int, buffer_size: int = 4096) -> tuple[bytes, int | None]:
    """Read low level chunk from stream source"""
    if is_nt:
        try:
            return _winapi.ReadFile(handle_or_fd, buffer_size)
        except BrokenPipeError:
            return b'', None
    try:
        return os.read(handle_or_fd, buffer_size), None
    except (BrokenPipeError, OSError):
        return b'', None

def args_to_command(*args: str):
    """Extract command structure from args"""
    try:
        return args[0], list(args)
    except Exception as err:
        return None, err

def try_to_execute(func, *args):
    """Execute target function catching runtime failures"""
    try:
        func(*args)
        return True, None
    except Exception as err:
        return False, err

def simple_type_check(v: object, t: type) -> Any:
    """Validate objective runtime instance datatype"""
    if not isinstance(v, t):
        raise TypeError(f'Expected <{t.__name__}> but was given <{type(v).__name__}>: {v}')
    return v

# ==========================================================================
# Base Objects
# ==========================================================================
class Task(list):
    """Task IO structure controller"""
    def __init__(self, *args: str) -> None:
        """Initialize core argument list payload"""
        if len(args) == 0:
            raise ValueError('Empty task is not allowed')
        super().__init__([simple_type_check(arg, str) for arg in args])

    # ============== getters ==================

    @property
    def program(self) -> str:
        """Root binary target path"""
        p, a = args_to_command(*self)
        return '' if not p else p

    @property
    def args(self) -> list[str]:
        """Complete parameter argument sequence"""
        p, a = args_to_command(*self)
        return [''] if not p else self

    @property
    def stdout(self) -> bytearray:
        """Cumulative stream output buffer"""
        return getattr(self, '_stdout', bytearray())

    @property
    def stderr(self) -> bytearray:
        """Cumulative stream error buffer"""
        return getattr(self, '_stderr', bytearray())

    # =============== setters ==========================

    @stderr.setter
    def stderr(self, value: bytes | bytearray) -> None:
        """Append error fragments avoiding recursion"""
        if isinstance(value, bytes):
            value = bytearray(value)
        simple_type_check(value, bytearray)
        if not hasattr(self, '_stderr'):
            setattr(self, '_stderr', value)
        else:
            self._stderr.extend(value)

    @stdout.setter
    def stdout(self, value: bytes | bytearray) -> None:
        """Append output fragments avoiding recursion"""
        if isinstance(value, bytes):
            value = bytearray(value)
        simple_type_check(value, bytearray)
        if not hasattr(self, '_stdout'):
            setattr(self, '_stdout', value)
        else:
            self._stdout.extend(value)


class _BaseExecution(ABC):
    """Execution state IO controller"""
    def __init__(self, task: Task) -> None:
        """Bind objective target execution context"""
        self.task = task

    # ================ getters =====================
    @property
    def pid(self) -> int:
        """Active tracking process identifier"""
        return getattr(self, '_pid', -1)

    @property
    def writer(self) -> int:
        """Pipeline inbound writing descriptor"""
        return getattr(self, '_fdw', -1)

    @property
    def reader(self) -> int:
        """Pipeline outbound reading descriptor"""
        return getattr(self, '_fdr', -1)

    # ================= setters =====================

    @pid.setter
    def pid(self, pid: int):
        """Set operational process identifier"""
        setattr(self, '_pid', simple_type_check(pid, int))

    @writer.setter
    def writer(self, fdw: int):
        """Set inbound pipeline handle"""
        setattr(self, '_fdw', simple_type_check(fdw, int))

    @reader.setter
    def reader(self, fdr: int):
        """Set outbound pipeline handle"""
        setattr(self, '_fdr', simple_type_check(fdr, int))

    # =========== global methods ==========================

    def _chunk_read(self) -> None:
        """Universal synchronous stream reader loop"""
        while True:
            curr_chunk, _ = read(self.reader, 4096)
            if not curr_chunk:
                break
            self.task.stdout = curr_chunk
        close(self.reader)

    async def _chunk_read_async(self) -> None:
        """Universal asynchronous stream reader loop"""
        loop = asyncio.get_running_loop()
        while True:
            curr_chunk, _ = await loop.run_in_executor(None, read, self.reader, 4096)
            if not curr_chunk:
                break
            self.task.stdout = curr_chunk
        close(self.reader)

    # ================== abstracts ===============================

    @abstractmethod
    def run(self, use_path: bool, env: dict | None, is_vec: bool):
        """Run command subprocess execution core"""
        pass

if is_nt:
    # ==========================================================================
    #  Win32 / NT Execution core
    # ==========================================================================
    class Execution(_BaseExecution, ABC):
        """Windows NT abstraction base layer"""

        # =========== handle getter/setter ==================

        @property
        def handle(self) -> int:
            """Get win32 process tracking handle"""
            return getattr(self, '_handle', -1)

        @handle.setter
        def handle(self, value: int):
            """Set win32 process tracking handle"""
            setattr(self, '_handle', simple_type_check(value, int))

        # ================ nt methods ================================

        def _setup_nt_pipeline(self) -> None:
            """Execute atomic win32 process spawning architecture"""
            self.reader, self.writer = pipe()
            _, packet = predirect(self.writer)
            duplicate(self.reader, inheritable=False)

            cmd_line = " ".join(f'"{arg}"' if " " in arg else arg for arg in self.task)
            _hp, _ht, _pid, _ = fork(param=ProcessParam(command_line=cmd_line, startup_info=packet))

            close(_ht)
            close(self.writer)
            self.handle = _hp
            self.pid = _pid
else:
    # ==========================================================================
    # Posix Execution Core
    # ==========================================================================
    class Execution(_BaseExecution, ABC):
        """POSIX abstraction base layer"""

        # ==================== posix methods =========================

        def _try_exec(self, use_path: bool, env: dict | None, is_vec: bool):
            """Internal selector for os exec flavor execution"""
            func_name = 'exec' + ('v' if is_vec else 'l') + ('p' if use_path else '') + ('e' if env else '')
            func_call = getattr(os, func_name)
            if is_vec:
                if env:
                    return try_to_execute(func_call, self.task.program, self.task.args, env)
                return try_to_execute(func_call, self.task.program, self.task.args)
            else:
                if env:
                    return try_to_execute(func_call, self.task.program, *self.task.args, env)
                return try_to_execute(func_call, self.task.program, *self.task.args)

        def _child_side(self, use_path: bool, env: dict | None, is_vec: bool) -> None:
            """Execute post-fork targeted child processing routine"""
            close(self.reader)
            predirect(self.writer)
            exec_is_ok, exec_error = self._try_exec(use_path, env, is_vec)
            if not exec_is_ok:
                sys.exit(127 if isinstance(exec_error, FileNotFoundError) else 1)
