import os
from pathlib import Path
from typing import Any


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

        if os.name == "nt":
            import _winapi

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
