from subprocess import run as shell
from typing import Any

from . import base


class SyncPiper(base._BasePiper):
    """Synchronous stream reader and state manager for running sub-processes."""
    def __init__(self) -> None:
        super().__init__()


class SyncTask(base._BaseTask):
    """Synchronous executable command vector managing a SyncPiper context."""
    def __init__(self, *args: str) -> None:
        super().__init__(*args)

    @property
    def piper(self) -> SyncPiper:
        """Get or initialize the synchronous stream pipeline manager instance."""
        if not hasattr(self, '_piper'):
            setattr(self, '_piper', SyncPiper())
        return getattr(self, '_piper')

    def run(self, stdin: Any = None, **kwargs: Any) -> None:
        """Execute a SyncTask synchronously using either shell or executive sub-processes."""
        self.validation()

        if stdin is not None:
            self.piper.stdin_pipe = stdin

        kwargs.setdefault('stdin', self.piper.stdin_pipe)
        kwargs.setdefault('stdout', self.piper.stdout_pipe)
        kwargs.setdefault('stderr', self.piper.stderr_pipe)
        kwargs.setdefault('cwd', self.piper.path)
        kwargs.setdefault('shell', self.piper.shell)

        if not self.piper.shell:
            cmd = list(self)
            process = shell(cmd, **kwargs)
        else:
            cmd_str = ' '.join(self)
            process = shell(cmd_str, **kwargs)

        if process.stdout is not None:
            self.piper.stdout = process.stdout
        if process.stderr is not None:
            self.piper.stderr = process.stderr

        self.piper.returncode = process.returncode
