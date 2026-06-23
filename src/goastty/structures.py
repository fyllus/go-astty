import os
import sys
from typing import Any

from goastty.unified import IS_NT


class UnifiedSI:
    """Agnostic process startup information layer normalizing NT and POSIX primitives"""

    # Win32 Subsystem Hardcoded Constants
    USE_STDH = 0x100
    STDIN_H = 0xFFFFFFF6
    STDOUT_H = 0xFFFFFFF5
    STDERR_H = 0xFFFFFFF4
    STARTF_USESHOWWINDOW = 0x00000001

    def __init__(self) -> None:
        self.mask_flag = 0
        self.curr_working_dir = None
        self.environ_variables = None
        self.redirect_stdout = None
        self.redirect_stderr = None
        self.redirect_stdin = None
        self.hide_win_console = False

    def __enter__(self):
        if self.curr_working_dir is not None:
            self._old_dir = os.getcwd()
            try:
                os.chdir(self.curr_working_dir)
            except Exception:
                sys.exit(127)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "_old_dir"):
            try:
                os.chdir(self._old_dir)
            except Exception:
                sys.exit(127)

    def file_actions(self) -> Any:
        return self.compile().get("file_actions")

    def compile(self) -> dict:
        """Compiles clean configuration into a flat, system-specific deployment dictionary"""
        _unpacked = {}

        if IS_NT:
            import _winapi as win

            # Calculate active descriptor masking
            flags = self.mask_flag
            if self.redirect_stdin or self.redirect_stdout or self.redirect_stderr:
                flags |= self.USE_STDH
            if self.hide_win_console:
                flags |= self.STARTF_USESHOWWINDOW
                _unpacked["wShowWindow"] = 0  # SW_HIDE

            _unpacked["dwFlags"] = flags
            _unpacked["hStdInput"] = (
                self.redirect_stdin
                if self.redirect_stdin is not None
                else win.GetStdHandle(self.STDIN_H)
            )
            _unpacked["hStdOutput"] = (
                self.redirect_stdout
                if self.redirect_stdout is not None
                else win.GetStdHandle(self.STDOUT_H)
            )
            _unpacked["hStdError"] = (
                self.redirect_stderr
                if self.redirect_stderr is not None
                else win.GetStdHandle(self.STDERR_H)
            )
        else:
            _unpacked["file_actions"] = [
                (os.POSIX_SPAWN_DUP2, fd, target)
                for target, fd in (
                    (0, self.redirect_stdin),
                    (1, self.redirect_stdout),
                    (2, self.redirect_stderr),
                )
                if fd is not None
            ]

        if self.curr_working_dir is not None:
            _unpacked["pCwdDir"] = self.curr_working_dir
        if self.environ_variables is not None:
            _unpacked["hDefEnv"] = self.environ_variables

        return _unpacked
