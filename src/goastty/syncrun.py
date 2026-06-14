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

    def run(self, use_path: bool = False, env: dict | None = None, is_vec: bool = False) -> None:
        """Execute the task payload through a blocking, native OS workflow.

        Orchestrates pipeline generation, process spawning via fork/CreateProcess,
        and synchronous stream reading loops before harvesting the exit status.
        """
        if is_posix:
            self.reader, self.writer = pipe()
            _, _, self.pid, _ = fork()
            if self.pid == 0:
                self._child_side(use_path, env, is_vec)
            else:
                close(self.writer)
                self._chunk_read()
                waitpid(self.pid, 0)

        elif is_nt:
            self._setup_nt_pipeline()
            self._chunk_read()
            waitpid(self.handle, W_INFINITE)
            close(self.handle)
