import asyncio
import ctypes
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, SupportsIndex

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
            # Vincula dwFlags explicitamente se handles customizados forem passados
            self["dwFlags"] = dwFlags | (_winapi.STARTF_USESTDHANDLES if (hStdInput or hStdOutput or hStdError) else 0)
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
            try:
                _winapi.CloseHandle(handle_or_fd)
            except OSError:
                pass
        else:
            try:
                os.close(handle_or_fd)
            except OSError:
                pass

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
            return pid_or_handle, _winapi.GetExitCodeProcess(pid_or_handle)
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
        # Gararante desempacotamento de tuplas de argumentos para as funções os.exec
        if func.__name__.startswith('exec') and isinstance(args[1], list):
            if len(args) == 3:
                func(args[0], args[1], args[2])
            else:
                func(args[0], args[1])
        else:
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

class Pipe:
    def __init__(self, pipe_attr: Any = None, size: int = 0) -> None:
        _r, _w = pipe(pipe_attr, size)
        self._reader = Descriptor(_r)
        self._writer = Descriptor(_w)

    # ================= reader =================

    @property
    def reader(self) -> Descriptor:
        if self._reader is None:
            raise RuntimeError("Pipe reader has been destroyed.")
        return self._reader

    @reader.deleter
    def reader(self) -> None:
        if self._reader is not None:
            self._reader.close()
            self._reader = None

    # ================= writer =================

    @property
    def writer(self) -> Descriptor:
        if self._writer is None:
            raise RuntimeError("Pipe writer has been destroyed.")
        return self._writer

    @writer.deleter
    def writer(self) -> None:
        if self._writer is not None:
            self._writer.close()
            self._writer = None


class PackedByte:
    def __init__(self, init_byte: bytes | None, handle: int | None) -> None:
        if handle:
            self.handle = handle
        if init_byte:
            self.byte = init_byte

    def has_byte(self):
        return hasattr(self, 'byte')

    def has_handle(self):
        return hasattr(self, 'handle')

    def __bool__(self):
        return self.has_byte()

class Descriptor(int):
    _closed = False
    def close(self):
        if self:
            self._closed = True
            close(self)

    def duplicate(self, target: int = 1, inheritable: bool = True):
        return type(self)(duplicate(self, target, inheritable))

    def read(self, buffer_size: int = 4096):
        return PackedByte(*read(self, buffer_size))

    def sync_waitpid(self, options: int = 0):
        pid, status = waitpid(self, options)
        self._completed = pid != 0
        return type(self)(pid), status

    async def async_waitpid(self, options: int = 0, time_sleep: float = 0.01):
        while True:
            pid, status  = self.sync_waitpid(options)
            if self._completed:
                return type(self)(pid), status
            await asyncio.sleep(time_sleep)

    def __bool__(self) -> bool:
        return not self._closed or self._completed


class ByteBuffer(bytearray):
    def __init__(self, package: bytes | PackedByte | None = None) -> None:
        super().__init__()
        if package is not None:
            self.stream(package)

    def stream(self, value: PackedByte | bytes) -> None:
        if not value:
            pass
        elif isinstance(value, PackedByte):
            self.extend(value.byte)
        elif isinstance(value, bytes):
            self.extend(value)
        else:
            raise AssignmentError('invalid', value, bytes, PackedByte)

    def sync_read(self, handle_or_fd: int | Descriptor, buffer_size: int = 4096, autoclose: bool = False):
        """Universal synchronous stream reader loop"""
        if not isinstance(handle_or_fd, (int, Descriptor)):
            raise AssignmentError('invalid', handle_or_fd, int, Descriptor)

        while True:
            if isinstance(handle_or_fd, Descriptor):
                chunk = handle_or_fd.read(buffer_size)
            elif isinstance(handle_or_fd, int):
                chunk, _ = read(handle_or_fd, buffer_size)
            if not chunk:
                break
            self.stream(chunk)

        if autoclose:
            if isinstance(handle_or_fd, Descriptor)
                handle_or_fd.close()
            else:
                close(handle_or_fd)

    async def async_read(self, handle_or_fd: int | Descriptor, buffer_size: int = 4096, autoclose: bool = False):
        """Universal asynchronous stream reader loop"""

        if not isinstance(handle_or_fd, (int, Descriptor)):
            raise AssignmentError('invalid', handle_or_fd, int, Descriptor)

        loop = asyncio.get_running_loop()
        while True:
            if isinstance(handle_or_fd, Descriptor):
                chunk = loop.run_in_executor(None, handle_or_fd.read, buffer_size)
            elif isinstance(handle_or_fd, int):
                chunk, _ = loop.run_in_executor(None, read, handle_or_fd, buffer_size)
            if not chunk:
                break
            self.stream(chunk)

        if autoclose:
            if isinstance(handle_or_fd, Descriptor)
                handle_or_fd.close()
            else:
                close(handle_or_fd)


class Task(list):
    """Task IO structure controller"""
    def __init__(self, *args: str) -> None:
        """Initialize core argument list payload"""
        self.__buffer__ = {
            'stdout': ByteBuffer(),
            'stderr': ByteBuffer(),
            'stdin': ByteBuffer()
        }
        if len(args) == 0:
            raise ValueError('Empty task is not allowed')
        super().__init__(self._build_(*args))

    # ============== getters ==================

    @property
    def unpack(self) -> tuple[str | None, list | None]:
        if is_posix:
            return self[0], list(self)
        if is_nt:
            return " ".join(f'"{arg}"' if " " in arg else arg for arg in self), None
        else:
            return None, None

    @property
    def cmd(self) -> str:
        """Root binary target path"""
        cmd, _ = self.unpack
        return cmd if cmd else ''

    if is_posix:
        @property
        def args(self) -> list[str]:
            """Complete parameter argument sequence"""
            _, args = self.unpack
            return args if args else ['']

    @property
    def environ(self) -> dict | None:
        return getattr(self, '_env', None)

    @property
    def use_path(self) -> bool:
        return getattr(self, '_use_path', True)

    @property
    def stdout(self) -> ByteBuffer:
        """Cumulative stream output buffer"""
        return self.__buffer__['stdout']

    @property
    def stdin(self) -> ByteBuffer:
        """Cumulative stream input buffer"""
        return self.__buffer__['stdout']

    @property
    def stderr(self) -> ByteBuffer:
        """Cumulative stream error buffer"""
        return self.__buffer__['stderr']

    # =============== setters ==========================

    @environ.setter
    def environ(self, value: dict) -> None:
        simple_type_check(value, dict)
        setattr(self, '_env', value)

    @use_path.setter
    def use_path(self, value: bool) -> None:
        simple_type_check(value, bool)
        setattr(self, '_use_path', value)

    # ============ internal methods ==========
    def _build_(self, *args) -> list[str]:
        _args = []
        self.use_path = not isinstance(args[0], Path)
        if not self.use_path:
            _args.append(str(args[0]))
            _args.extend(list(args[1:]))
        else:
            _args.extend(list(args))
        return [simple_type_check(a, str) for a in _args]


class _BaseExecution(ABC):
    """Execution state IO controller"""
    def __init__(self, task: Task) -> None:
        """Bind objective target execution context"""
        self.__exec__ = {}
        self.task = task

    # ================ getters =====================
    @property
    def pid(self) -> int:
        """Active tracking process identifier"""
        return getattr(self, '_pid', -1)

    @property
    def pipe(self):
        if not '_pipe' in self.__exec__:
            self.__exec__['_pipe'] = Pipe()
        return self.__exec__['_pipe']

    # ================= setters =====================

    @pid.setter
    def pid(self, pid: int):
        """Set operational process identifier"""
        setattr(self, '_pid', simple_type_check(pid, int))

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
        def handle(self, value: int | None):
            """Set win32 process tracking handle"""
            if value is not None
                setattr(self, '_handle', simple_type_check(value, int))

        # ================ nt methods ================================

        def _setup_nt_pipeline(self) -> None:
            """Execute atomic win32 process spawning architecture"""

            # torna o handle de escrita herdável pelo filho
            duplicate(self.pipe._writer, inheritable=True)
            _, packet = predirect(self.pipe._writer)

            # o handle de leitura NÃO deve ser herdado pelo processo filho
            self.pipe._reader.duplicate(inheritable=False)
            _hp, _ht, _pid, _ = fork(param=ProcessParam(command_line=self.task.cmd, startup_info=packet))

            close(_ht)
            self.pipe._writer.close()  # fecha o do pai para permitir o EOF nativo na leitura
            self.handle = _hp
            self.pid = _pid
else:
    # ==========================================================================
    # Posix Execution Core
    # ==========================================================================
    class Execution(_BaseExecution, ABC):
        """POSIX abstraction base layer"""

        # ==================== posix methods =========================
        # preciso melhorar
        def _try_exec(self, is_vec: bool = True):
            """Internal selector for os exec flavor execution"""
            func_name = 'exec' + ('v' if is_vec else 'l')
            func_name += ('p' if self.task.use_path else '')
            func_name += ('e' if isinstance(self.task.environ, dict) else '')
            func_call = getattr(os, func_name)

            if is_vec:
                if self.task.use_path:
                    if self.task.environ:
                        return try_to_execute(func_call, self.task.cmd, self.task.args, self.task.environ)
                    return try_to_execute(func_call, self.task.cmd, self.task.args)
                return try_to_execute(func_call, self.task.cmd, self.task.args)
            else:
                if self.task.use_path:
                    if self.task.environ:
                        return try_to_execute(func_call, self.task.cmd, *self.task.args, self.task.environ)
                    return try_to_execute(func_call, self.task.cmd, *self.task.args)
                return try_to_execute(func_call, self.task.cmd, *self.task.args)

        def _child_side(self, is_vec: bool) -> None:
            """Execute post-fork targeted child processing routine"""
            self.pipe._reader.close()
            predirect(self.pipe._writer)
            self.pipe._writer.close()
            exec_is_ok, exec_error = self._try_exec(is_vec)
            if not exec_is_ok:
                sys.exit(127 if isinstance(exec_error, FileNotFoundError) else 1)
