from goastty.api import (
    Execution,
    close,
    fork,
    is_nt,
    is_posix,
    pipe,
    waitpid,
)

if is_nt:
    from goastty.api import W_INFINITE

class SyncTask(Execution):
    """Synchronous subprocess execution runtime engine."""

    def run(self, is_vec: bool = False) -> None:
        """Execute the task payload through a blocking, native OS workflow.

        Orchestrates pipeline generation, process spawning via fork/CreateProcess,
        and synchronous stream reading loops before harvesting the exit status.
        """
        if is_posix:
            self.reader, self.writer = pipe()
            _, _, self.pid, _ = fork()
            if self.pid == 0:
                self._child_side(is_vec)
            else:
                close(self.writer)
                self.task.stdout.sync_read(self.pipe._reader, autoclose=True)
                self.pid.sync_wait()

        elif is_nt:
            self._setup_nt_pipeline()
            self.task.stdout.async_read(self.pipe._reader)
            self.handle.sync_wait(W_INFINITE)
            self.handle.close()
