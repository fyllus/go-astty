import asyncio

from goastty.api import (
    Execution,
    close,
    fork,
    is_nt,
    is_posix,
    pipe,
    waitpid,
)

if is_posix:
    from goastty.api import WNOHANG

class AsyncTask(Execution):
    """Asynchronous subprocess execution runtime engine."""

    async def run(self, use_path: bool = False, env: dict | None = None, is_vec: bool = False) -> None:
        """Execute the task payload through a non-blocking, cooperative workflow.

        Orchestrates pipeline generation, asynchronous stream processing loops,
        and polling-based exit status harvesting wrapped around asyncio context switches.
        """
        if is_posix:
            self.reader, self.writer = pipe()
            _, _, self.pid, _ = fork()
            if self.pid == 0:
                self._child_side(use_path, env, is_vec)
            else:
                close(self.writer)
                await self._chunk_read_async()
                while True:
                    pid, _ = waitpid(self.pid, WNOHANG)
                    if pid != 0:
                        break
                    await asyncio.sleep(0.01)

        elif is_nt:
            self._setup_nt_pipeline()
            await self._chunk_read_async()
            while True:
                pid, _ = waitpid(self.handle, 1)
                if pid != 0:
                    break
                await asyncio.sleep(0.01)
            close(self.handle)
