import asyncio
from pathlib import Path

from goastty.execution import Execution, init_startup, post_startup
from goastty.types import UnifiedHandle, UnifiedIOBuffer, UnifiedTask
from goastty.unified import IS_NT, StartUpInfo

# ==========================================================================
# Pure Functional Pipeline
# ==========================================================================


def exec_sync(
    cmd: str | Path,
    args: list[str],
    env: dict | None = None,
    config: StartUpInfo = StartUpInfo(),
    get_err: bool = False,
):
    """Execute and consume system stream processing to termination sequentially"""
    cfg = init_startup(get_err, config)
    _pid, _handle = post_startup(cmd, args, env, cfg)

    data_output = UnifiedIOBuffer()

    data_output.sync_read(cfg["hReaderOutput"], autoclose=True)
    if get_err:
        data_output.sync_read(cfg["hReaderError"], autoclose=True)

    target = UnifiedHandle(_handle if IS_NT else _pid)

    _, status = target.sync_waitpid()
    target.close()
    return status


async def exec_async(
    cmd: str | Path,
    args: list[str],
    env: dict | None = None,
    config: StartUpInfo = StartUpInfo(),
    get_err: bool = False,
):
    """Execute and consume system stream processing via non-blocking pool loop"""
    cfg = init_startup(get_err, config)
    _pid, _handle = post_startup(cmd, args, env, cfg)

    data_output = UnifiedIOBuffer()
    target = UnifiedHandle(_handle if IS_NT else _pid)

    # Concurrently consume stream pipes and wait for termination to prevent block deadlocks
    if get_err:
        _, _, (_, status) = await asyncio.gather(
            data_output.async_read(cfg["hReaderOutput"], autoclose=True),
            data_output.async_read(cfg["hReaderError"], autoclose=True),
            target.async_waitpid(),
        )
    else:
        _, (_, status) = await asyncio.gather(
            data_output.async_read(cfg["hReaderOutput"], autoclose=True),
            target.async_waitpid(),
        )

    target.close()
    return status


class SyncTask(UnifiedTask):
    """Synchronous targeted pipeline context payload wrapper"""

    def __init__(self, *args: str | Path | UnifiedIOBuffer) -> None:
        super().__init__(*args)


class SyncExecution(Execution):
    """Master synchronous execution controller"""

    def __init__(self, task: SyncTask) -> None:
        super().__init__(task)

    def run(self, get_stderr: bool = False) -> int:
        """Execute and consume stream processing to termination sequentially"""
        self.startup(get_stderr=get_stderr)

        self.task.stdout.sync_read(self.pipe.stdout_reader, autoclose=True)
        if get_stderr:
            self.task.stderr.sync_read(self.pipe.stderr_reader, autoclose=True)

        target_resource = self.pipe.handle if IS_NT else self.pipe.pid

        _, status = target_resource.sync_waitpid()
        target_resource.close()
        return status


class AsyncTask(UnifiedTask):
    """Asynchronous targeted pipeline context payload wrapper"""

    def __init__(self, *args: str | Path | UnifiedIOBuffer) -> None:
        super().__init__(*args)


class AsyncExecution(Execution):
    """Master asynchronous execution controller"""

    def __init__(self, task: AsyncTask) -> None:
        super().__init__(task)

    async def run(self, get_stderr: bool = False) -> int:
        """Execute and consume stream processing via non-blocking pool loop"""
        self.startup(get_stderr=get_stderr)

        target_resource = self.pipe.handle if IS_NT else self.pipe.pid

        if get_stderr:
            _, _, (_, status) = await asyncio.gather(
                self.task.stdout.async_read(self.pipe.stdout_reader, autoclose=True),
                self.task.stderr.async_read(self.pipe.stderr_reader, autoclose=True),
                target_resource.async_waitpid(),
            )
        else:
            _, (_, status) = await asyncio.gather(
                self.task.stdout.async_read(self.pipe.stdout_reader, autoclose=True),
                target_resource.async_waitpid(),
            )

        target_resource.close()
        return status
