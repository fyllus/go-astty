import asyncio

from . import base


class AsyncPiper(base._BasePiper):
    """Asynchronous stream reader and state manager for running sub-processes."""
    def __init__(self) -> None:
        super().__init__()

    async def stream_stdout(self, stream: asyncio.StreamReader | None) -> None:
        """Consume and append chunks from the asynchronous stdout stream buffer."""
        if not isinstance(stream, asyncio.StreamReader):
            raise TypeError('<stream> must be StreamReader ')
        while True:
            data = await stream.read(4096)
            if not data:
                break
            self.stdout = data

    async def stream_stderr(self, stream: asyncio.StreamReader | None) -> None:
        """Consume and append chunks from the asynchronous stderr stream buffer."""
        if not isinstance(stream, asyncio.StreamReader):
            raise TypeError('<stream> must be StreamReader ')
        while True:
            data = await stream.read(4096)
            if not data:
                break
            self.stderr = data


class AsyncTask(base._BaseTask):
    """Asynchronous executable command vector managing an AsyncPiper context."""
    def __init__(self, *args: str) -> None:
        super().__init__(*args)

    @property
    def piper(self) -> AsyncPiper:
        """Get or initialize the asynchronous stream pipeline manager instance."""
        if not hasattr(self, '_piper'):
            setattr(self, '_piper', AsyncPiper())
        return getattr(self, '_piper')

async def shell(task: AsyncTask, **kwargs) -> None:
    """Execute an AsyncTask asynchronously using either shell or executive sub-processes."""
    if not task:
        return

    if task.piper.shell:
        cmd_str = " ".join([task.prog] + task.args)
        process = await asyncio.create_subprocess_shell(
            cmd_str,
            stdin=task.piper.stdin_pipe,
            stdout=task.piper.stdout_pipe,
            stderr=task.piper.stderr_pipe,
            cwd=task.piper.path,
            **kwargs
        )
    else:
        process = await asyncio.create_subprocess_exec(
            task.prog, *task.args,
            stdin=task.piper.stdin_pipe,
            stdout=task.piper.stdout_pipe,
            stderr=task.piper.stderr_pipe,
            cwd=task.piper.path,
            **kwargs
        )

    await asyncio.gather(
        task.piper.stream_stdout(process.stdout),
        task.piper.stream_stderr(process.stderr)
    )

    await process.wait()
    if isinstance(process.returncode, int):
        task.piper.returncode = process.returncode
