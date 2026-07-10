import os
import shutil
from pathlib import Path
from typing import Any

from ._struct import StartUpInfo

if os.name == "posix":

    def close(descriptor: int) -> None:
        """Posix descriptor close"""
        try:
            os.close(descriptor)
        except OSError:
            pass

    def pipe(attr: Any = None, size: int | None = None) -> tuple[int, int]:
        """Posix pipeline creator"""
        return os.pipe()

    def waitpid(pid: int, opt: int = 0) -> tuple[int, int]:
        """Posix wait for process id terminate"""
        try:
            return os.waitpid(pid, opt)
        except ChildProcessError:
            return pid, 0

    def read(descriptor: int, buffer_size: int = 4096) -> tuple[bytes, int | None]:
        """Read posix chunk from stream source"""
        try:
            return os.read(descriptor, buffer_size), None
        except BrokenPipeError, OSError:
            return b"", None

    def spawn(cmd: str | Path, args: list[str], si: StartUpInfo) -> tuple[int, int]:
        """Posix process spawning via native posix_spawn syscall."""
        program = (
            str(cmd)
            if isinstance(cmd, Path)
            else (shutil.which(cmd) if os.sep not in cmd else cmd)
        )
        if not program:
            return 0, 127

        # os.posix_spawn accepts a set_ids parameter but natively execution
        # lacks a direct cwd argument, solved via thread-safe file_actions if available,
        # or traditional chdir fallback.
        file_actions = [
            (os.POSIX_SPAWN_DUP2, fd, target)
            for target, fd in (
                (0, si.get("hStdInput")),
                (1, si.get("hStdOutput")),
                (2, si.get("hStdError")),
            )
            if fd is not None
        ]

        cwd = si.get("pCwdDir")
        old_cwd = None

        if cwd is not None:
            try:
                old_cwd = os.getcwd()
                os.chdir(cwd)
            except OSError:
                return 0, 127

        try:
            pid = os.posix_spawn(
                program,
                [program] + args,
                si.get("hDefEnv", os.environ),
                file_actions=file_actions,
            )
            return pid, 0
        except OSError:
            return 0, 127
        finally:
            if old_cwd is not None:
                os.chdir(old_cwd)
