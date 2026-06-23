import os

from . import execution, types
from .types import _platform as platform

__version__ = "0.3.7"

__all__ = [
    "execution",
    "types",
]


# ==========================================================================
# Pure Functional Pipeline
# ==========================================================================


def exec_sync(
    cmd: str | execution.Path,
    args: list[str],
    config: platform.StartUpInfo = platform.StartUpInfo(),
    get_err: bool = False,
) -> tuple[int, types.Buffer]:
    """Execute and consume system stream processing to termination sequentially"""
    cfg = execution.init_startup(get_err, config)
    _pid, _handle = execution.post_startup(cmd, args, cfg)

    data_output = types.Buffer()

    data_output.sync_read(cfg["hReaderOutput"], autoclose=True)
    if get_err:
        data_output.sync_read(cfg["hReaderError"], autoclose=True)

    target = types.Handle(_handle if os.name == "nt" else _pid)

    _, status = target.sync_waitpid()
    target.close()

    # get status and output
    return status, data_output


async def exec_async(
    cmd: str | execution.Path,
    args: list[str],
    config: platform.StartUpInfo = platform.StartUpInfo(),
    get_err: bool = False,
) -> tuple[int, types.Buffer]:
    """Execute and consume system stream processing via non-blocking pool loop"""
    cfg = execution.init_startup(get_err, config)
    _pid, _handle = execution.post_startup(cmd, args, cfg)

    data_output = types.Buffer()
    target = types.Handle(_handle if os.name == "nt" else _pid)

    # concurrently consume stream pipes and wait for termination to prevent block deadlocks
    if get_err:
        _, _, (_, status) = await types.asyncio.gather(
            data_output.async_read(cfg["hReaderOutput"], autoclose=True),
            data_output.async_read(cfg["hReaderError"], autoclose=True),
            target.async_waitpid(),
        )
    else:
        _, (_, status) = await types.asyncio.gather(
            data_output.async_read(cfg["hReaderOutput"], autoclose=True),
            target.async_waitpid(),
        )

    target.close()

    # get status and output
    return status, data_output


class SyncTask(types.Task):
    """Synchronous targeted pipeline context payload wrapper"""

    def __init__(self, cmd: str | execution.Path, *args: str) -> None:
        super().__init__(cmd, *args)


class SyncExecution(execution.Execution):
    """Master synchronous execution controller"""

    def __init__(self, task: SyncTask) -> None:
        super().__init__(task)

    def run(self, get_stderr: bool = False) -> int:
        """Execute and consume stream processing to termination sequentially"""
        self.startup(get_stderr=get_stderr)

        self.task.stdout().sync_read(self.pipe.stdout_reader, autoclose=True)
        if get_stderr:
            self.task.stderr().sync_read(self.pipe.stderr_reader, autoclose=True)

        target_resource = self.pipe.handle if os.name == "nt" else self.pipe.pid

        _, status = target_resource.sync_waitpid()
        target_resource.close()
        return status


class AsyncTask(types.Task):
    """Asynchronous targeted pipeline context payload wrapper"""

    def __init__(self, cmd: str | execution.Path, *args: str) -> None:
        super().__init__(cmd, *args)


class AsyncExecution(execution.Execution):
    """Master asynchronous execution controller"""

    def __init__(self, task: AsyncTask) -> None:
        super().__init__(task)

    async def run(self, get_stderr: bool = False) -> int:
        """Execute and consume stream processing via non-blocking pool loop"""
        self.startup(get_stderr=get_stderr)

        target_resource = self.pipe.handle if os.name == "nt" else self.pipe.pid

        if get_stderr:
            _, _, (_, status) = await types.asyncio.gather(
                self.task.stdout().async_read(self.pipe.stdout_reader, autoclose=True),
                self.task.stderr().async_read(self.pipe.stderr_reader, autoclose=True),
                target_resource.async_waitpid(),
            )
        else:
            _, (_, status) = await types.asyncio.gather(
                self.task.stdout().async_read(self.pipe.stdout_reader, autoclose=True),
                target_resource.async_waitpid(),
            )

        target_resource.close()
        return status
