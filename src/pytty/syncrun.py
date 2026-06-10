import subprocess as sp

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

def shell(task: SyncTask, **kwargs) -> None:
    """Execute a SyncTask synchronously using either array vectors or raw string commands."""
    if not task:
        return

    if not task.piper.shell:
        cmd = [task.prog] + task.args
        process = sp.run(
            cmd,
            stdin=task.piper.stdin_pipe,
            stderr=task.piper.stderr_pipe,
            stdout=task.piper.stdout_pipe,
            cwd=task.piper.path,
            shell=task.piper.shell,
            **kwargs
        )
    else:
        cmd_str = ' '.join(task)
        process = sp.run(
            cmd_str,
            stdin=task.piper.stdin_pipe,
            stderr=task.piper.stderr_pipe,
            stdout=task.piper.stdout_pipe,
            cwd=task.piper.path,
            shell=task.piper.shell,
            **kwargs
        )

    task.piper.stdout = process.stdout
    task.piper.stderr = process.stderr
    task.piper.returncode = process.returncode
