import asyncio
from asyncio import create_subprocess_exec as async_exec
from asyncio import create_subprocess_shell as async_shell
from typing import Any

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

    async def run(self, stdin: Any = None, **kwargs: Any) -> None:
        """Execute an AsyncTask asynchronously using either shell or executive sub-processes."""
        self.validation()

        if stdin is not None:
            self.piper.stdin_pipe = stdin

        kwargs.setdefault('stdin', self.piper.stdin_pipe)
        kwargs.setdefault('stdout', self.piper.stdout_pipe)
        kwargs.setdefault('stderr', self.piper.stderr_pipe)
        kwargs.setdefault('cwd', self.piper.path)

        if self.piper.shell:
            cmd_str = " ".join(self)
            process = await async_shell(cmd_str, **kwargs)
        else:
            process = await async_exec(self.prog, *self.args, **kwargs)

        await asyncio.gather(
            self.piper.stream_stdout(process.stdout),
            self.piper.stream_stderr(process.stderr)
        )

        await process.wait()
        if process.returncode is not None:
            self.piper.returncode = process.returncode
