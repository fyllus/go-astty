from pathlib import Path

from pygit2 import GitError, Repository

from goastty.git import errors


def open_repository(repo: Path | Repository):
    """Open an existing git repository from a Path or Repository object."""

    if isinstance(repo, Repository):
        return repo
    if not isinstance(repo, Path):
        raise errors.GitRepoError(
            f"Invalid repository type <{type(repo).__name__}>, expected <RepositoryOrPath>"
        )
    try:
        return Repository(str(repo))
    except KeyError, GitError:
        raise errors.GitRepoError("Not a valid repository inited.")


def is_git_repository(path: Path) -> bool:
    """Check if the given path is a valid git repository."""
    try:
        open_repository(repo=path)
        return True
    except errors.GitRepoError:
        return False
