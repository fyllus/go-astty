import os
from pathlib import Path

from goastty.types import Gateway, Handle, Task, _platform

# ==========================================================================
# Execution Core
# ==========================================================================


def init_startup(
    get_err: bool = False, config: _platform.StartUpInfo | None = None
) -> _platform.StartUpInfo:
    """Aloca canais e acopla descritores de escrita e leitura no StartUpInfo"""
    cfg = config if config is not None else _platform.StartUpInfo()

    stdout_r, stdout_w = _platform.pipe()
    cfg["hStdOutput"] = stdout_w
    cfg["hReaderOutput"] = stdout_r

    if get_err:
        stderr_r, stderr_w = _platform.pipe()
        cfg["hStdError"] = stderr_w
        cfg["hReaderError"] = stderr_r
    else:
        cfg["hStdError"] = stdout_w
        cfg["hReaderError"] = stdout_r

    return cfg


def post_startup(cmd: str | Path, args: list[str], config: _platform.StartUpInfo):
    _pid, _handle = _platform.spawn(cmd, args, config)
    _platform.close(config["hStdOutput"])
    if config["hStdOutput"] != config["hStdError"]:
        _platform.close(config["hStdError"])
    return _pid, _handle


class Execution:
    """Execution state IO controller"""

    def __init__(self, task: Task) -> None:
        """Bind objective target execution context"""
        self.task = task

    @property
    def pipe(self) -> Gateway:
        """Expose current gateway; raises AttributeError if startup wasn't called"""
        return getattr(self, "_pipe")

    def startup(self, get_stderr: bool = False) -> None:
        """Execution PipeLine with dynamic lazy gate initialization"""

        _gateway = Gateway(get_stderr=get_stderr)
        setattr(self, "_pipe", _gateway)

        self.task.config["hStdOutput"] = _gateway.stdout_writer
        if get_stderr:
            self.task.config["hStdError"] = _gateway.stderr_writer

        _pid, _hp = _platform.spawn(self.task.cmd(), self.task.args(), self.task.config)

        _gateway.stdout_writer.close()
        if get_stderr:
            _gateway.stderr_writer.close()

        if os.name == "nt":
            setattr(_gateway, "_handle", Handle(_hp))
        setattr(_gateway, "_pid", Handle(_pid))
