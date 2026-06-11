import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, List, TypeVar

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
DEVNULL = subprocess.DEVNULL


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


class TaskError(Exception):
    """Exception raised for validation failures before task runtime execution."""
    def __init__(self, flag: str, task: "_BaseTask") -> None:
        self._cases = {
            'empty': f'Unable to run empty task: {task}',
            'invalid_command': f'Not found or unknown command {task.prog}'
        }
        super().__init__(self._cases.get(flag, f'Unknown error case with task {task}'))


BaseTask = TypeVar('BaseTask', bound='_BaseTask')
BasePiper = TypeVar('BasePiper', bound='_BasePiper')


class _BasePiper:
    """Manage stream pipes, exit status, and execution context for a process."""
    def __init__(self) -> None:
        pass

    def __getitem__(self, name: str) -> Any:
        return getattr(self, name)

    def __setitem__(self, name: str, value: Any) -> None:
        if not hasattr(self, name):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        setattr(self, name, value)

    # ---------- class property -------------------
    @property
    def stdout(self) -> bytearray:
        """Get the accumulated standard output bytes."""
        if not hasattr(self, '_stdout'):
            setattr(self, '_stdout', bytearray())
        return getattr(self, '_stdout')

    @stdout.setter
    def stdout(self, value: bytes | bytearray) -> None:
        if not isinstance(value, (bytes, bytearray)):
            raise AssignmentError('invalid', value, bytes, bytearray)
        self.stdout.extend(value)

    @property
    def stderr(self) -> bytearray:
        """Get the accumulated standard error bytes."""
        if not hasattr(self, '_stderr'):
            setattr(self, '_stderr', bytearray())
        return getattr(self, '_stderr')

    @stderr.setter
    def stderr(self, value: bytes | bytearray) -> None:
        if not isinstance(value, (bytes, bytearray)):
            raise AssignmentError('invalid', value, bytes, bytearray)
        self.stderr.extend(value)

    @property
    def returncode(self) -> int | None:
        """Get the process exit code integer after termination."""
        if not hasattr(self, '_returncode'):
            setattr(self, '_returncode', None)
        return getattr(self, '_returncode')

    @returncode.setter
    def returncode(self, value: int) -> None:
        if not isinstance(value, int):
            raise AssignmentError('unable', value, int)
        self._returncode = value

    @property
    def stdout_pipe(self) -> int:
        """Get the internal target destination descriptor for stdout."""
        if not hasattr(self, '_stdout_pipe'):
            setattr(self, '_stdout_pipe', PIPE)
        return getattr(self, '_stdout_pipe')

    @property
    def stderr_pipe(self) -> int:
        """Get the internal target destination descriptor for stderr."""
        if not hasattr(self, '_stderr_pipe'):
            setattr(self, '_stderr_pipe', PIPE)
        return getattr(self, '_stderr_pipe')

    @property
    def stdin_pipe(self) -> Any:
        """Get the source input stream pipeline anchor for stdin."""
        if not hasattr(self, '_stdin'):
            setattr(self, '_stdin', None)
        return getattr(self, '_stdin')

    @stdin_pipe.setter
    def stdin_pipe(self, value: Any) -> None:
        setattr(self, '_stdin', value)

    @property
    def path(self) -> Path:
        """Get the filesystem directory context where execution occurs."""
        if not hasattr(self, '_path'):
            setattr(self, '_path', Path.cwd())
        return getattr(self, '_path')

    @path.setter
    def path(self, value: Path) -> None:
        if value is None:
            raise AssignmentError('none', value, Path)
        if not isinstance(value, Path):
            raise AssignmentError('unable', value, Path)
        setattr(self, '_path', value)

    @property
    def shell(self) -> bool:
        """Check whether direct system shell execution is enabled."""
        if not hasattr(self, '_shell'):
            setattr(self, '_shell', False)
        return getattr(self, '_shell')

    @shell.setter
    def shell(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise AssignmentError('unable', value, bool)
        setattr(self, '_shell', value)


class _BaseTask(list):
    """Represent an executable command payload structure as an array of arguments."""
    def __init__(self, *args: str) -> None:
        super().__init__()
        if args:
            self.extend(args)

    def __bool__(self) -> bool:
        return len(self) > 0

    # ---------- class property -------------------
    @property
    def prog(self) -> str:
        """Get the root binary filename executable anchor of the command."""
        if not self:
            return ''
        return self[0]

    @property
    def args(self) -> list:
        """Get the trailing arguments list passed to the executable payload."""
        if not len(self) > 1:
            return []
        return self[1:]

    @property
    def piper(self) -> Any:
        """Get the stream pipeline manager tied to this specific task execution context."""
        if not hasattr(self, '_piper'):
            setattr(self, '_piper', _BasePiper())
        return getattr(self, '_piper')

    @piper.setter
    def piper(self, value: Any) -> None:
        if not isinstance(value, _BasePiper):
            raise AssignmentError('unable', value, _BasePiper)
        setattr(self, '_piper', value)

    @property
    def callback(self) -> Any:
        """Get the execution hook function triggered upon process completion."""
        return getattr(self, '_callback', None)

    @callback.setter
    def callback(self, value: Any) -> None:
        if not callable(value):
            raise AssignmentError('invalid', value, Callable)
        setattr(self, '_callback', value)

    # --------------- main methods -------------------------------
    def append(self, value: str) -> None:
        """Append a safe string argument entry to the command vector."""
        if not isinstance(value, str):
            raise ValueError('Value must be <str>')
        super().append(value)

    def extend(self, value: List[str]) -> None:
        """Extend the command argument payload using an array of string slices."""
        if not all(isinstance(arg_item, str) for arg_item in value):
            raise ValueError('Value must be <List[str]>')
        super().extend(value)

    def validation(self) -> None:
        """Pre-Runtime validation gate to check structural faults before process boot."""
        if not self:
            raise TaskError('empty', self)
        if not self.piper.shell and not shutil.which(self.prog):
            raise TaskError('invalid_command', self)
