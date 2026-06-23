import os
from pathlib import Path
from typing import Any

VERIFY_OS_IS_NT = os.name == "nt"

if VERIFY_OS_IS_NT:
    import _winapi as win
    from ctypes import wintypes

    NT_BOOL = wintypes.BOOL
    NT_BOOLEAN = wintypes.BOOLEAN
    NT_CHAR = wintypes.CHAR
    NT_ATOM = wintypes.ATOM
    NT_BYTE = wintypes.BYTE
    NT_DOUBLE = wintypes.DOUBLE
    NT_DWORD = wintypes.DWORD
    NT_INFINITE = win.INFINITE
    NT_WAIT_OBJECT_0 = win.WAIT_OBJECT_0

    def _close(handle: int) -> None:
        """NT handle close"""
        try:
            win.CloseHandle(handle)
        except OSError:
            pass

    def _pipe(attr: Any, size: int | None) -> tuple[int, int]:
        """NT pipeline creator"""
        size = size if size is not None else 0
        return win.CreatePipe(attr, size)

    def _waitpid(handle: int, opt: int = 0) -> tuple[int, int]:
        """NT wait for process handle to terminate"""
        timeout = 0 if opt == 1 else NT_INFINITE
        if win.WaitForSingleObject(handle, timeout) == NT_WAIT_OBJECT_0:
            return handle, win.GetExitCodeProcess(handle)
        return 0, 0

    def _read(handle: int, buffer_size: int = 4096) -> tuple[bytes, int | None]:
        """NT chunk read from stream source"""
        try:
            res, _ = win.ReadFile(handle, buffer_size)
            return res, handle
        except BrokenPipeError, OSError:
            return b"", None

    def _spawn_process(
        cmd: str | Path, args: list[str], si: StartUpInfo
    ) -> tuple[int, int]:
        """NT spawn process"""
        cmd_line = f'"{cmd}" ' + " ".join(f'"{a}"' if " " in a else a for a in args)
        cwd = si.get("pCwdDir", None)
        environment = si.get("hDefEnv", None)
        hp, ht, pid, _ = win.CreateProcess(
            None, cmd_line, None, None, True, 0, environment, cwd, si
        )
        _close(ht)
        return pid, hp
