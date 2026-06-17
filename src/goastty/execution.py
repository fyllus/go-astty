from pathlib import Path

from goastty.types import IS_NT, UnifiedGateway, UnifiedHandle, UnifiedTask
from goastty.unified import (
    StartUpInfo,
    close,
    pipe,
    spawn,
)

# ==========================================================================
# Execution Core
# ==========================================================================


def init_startup(
    get_err: bool = False, config: StartUpInfo | None = None
) -> StartUpInfo:
    """Aloca canais e acopla descritores de escrita e leitura no StartUpInfo"""
    cfg = config if config is not None else StartUpInfo()

    stdout_r, stdout_w = pipe()
    cfg["hStdOutput"] = stdout_w
    cfg["hReaderOutput"] = stdout_r

    if get_err:
        stderr_r, stderr_w = pipe()
        cfg["hStdError"] = stderr_w
        cfg["hReaderError"] = stderr_r
    else:
        cfg["hStdError"] = stdout_w
        cfg["hReaderError"] = stdout_r

    return cfg


def post_startup(cmd: str | Path, args: list[str], config: StartUpInfo):
    _pid, _handle = spawn(cmd, args, config)
    close(config["hStdOutput"])
    if config["hStdOutput"] != config["hStdError"]:
        close(config["hStdError"])
    return _pid, _handle


class Execution:
    """Execution state IO controller"""

    def __init__(self, task: UnifiedTask) -> None:
        """Bind objective target execution context"""
        self.task = task

    @property
    def pipe(self) -> UnifiedGateway:
        """Expose current gateway; raises AttributeError if startup wasn't called"""
        return getattr(self, "_pipe")

    def startup(self, get_stderr: bool = False) -> None:
        """Unified Execution PipeLine with dynamic lazy gate initialization"""

        _gateway = UnifiedGateway(get_stderr=get_stderr)
        setattr(self, "_pipe", _gateway)

        self.task.config["hStdOutput"] = _gateway.stdout_writer
        if get_stderr:
            self.task.config["hStdError"] = _gateway.stderr_writer

        _pid, _hp = spawn(self.task.cmd(), self.task.args(), self.task.config)

        _gateway.stdout_writer.close()
        if get_stderr:
            _gateway.stderr_writer.close()

        if IS_NT:
            setattr(_gateway, "_handle", UnifiedHandle(_hp))
        setattr(_gateway, "_pid", UnifiedHandle(_pid))
