import os
import shutil
import sys
from pathlib import Path
from typing import Any

VERIFY_OS_IS_POSIX = os.name == "posix"

if VERIFY_OS_IS_POSIX:

    def _close(descriptor: int) -> None:
        """Posix descriptor close"""
        try:
            os.close(descriptor)
        except OSError:
            pass

    def _pipe(attr: Any, size: int | None) -> tuple[int, int]:
        """Posix pipeline creator"""
        return os.pipe()

    def _waitpid(pid: int, opt: int = 0) -> tuple[int, int]:
        """Posix wait for process id terminate"""
        try:
            return os.waitpid(pid, opt)
        except ChildProcessError:
            return pid, 0

    def _read(descriptor: int, buffer_size: int = 4096) -> tuple[bytes, int | None]:
        """Read posix chunk from stream source"""
        try:
            return os.read(descriptor, buffer_size), None
        except BrokenPipeError, OSError:
            return b"", None

    def _spawn_process(
        cmd: str | Path, args: list[str], si: StartUpInfo
    ) -> tuple[int, int]:
        """Posix high-performance process spawning via native posix_spawn syscall"""

        # simple path edge case to ensure found executable
        program = (
            str(cmd)
            if isinstance(cmd, Path)
            else shutil.which(cmd)
            if os.sep not in cmd
            else cmd
        )

        arguments = [program] + args
        stdout = si.get("hStdOutput")
        stdin = si.get("hStdInput")
        stderr = si.get("hStdError")
        cwd = si.get("pCwdDir")
        environment = si.get("hDefEnv", os.environ)
        old_cwd = None

        if cwd is not None:
            try:
                old_cwd = os.getcwd()
                os.chdir(cwd)
            except Exception:
                sys.exit(127)

        # list comprehension to avoid overhead in .append()
        file_actions = [
            (os.POSIX_SPAWN_DUP2, fd, target)
            for target, fd in ((0, stdin), (1, stdout), (2, stderr))
            if fd is not None
        ]

        try:
            pid = os.posix_spawn(
                program, arguments, environment, file_actions=file_actions
            )
        finally:
            if old_cwd is not None:
                os.chdir(old_cwd)

        return pid, 0
