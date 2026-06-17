"""
For future implementation: the current focus is keep stable and improve the main execution
arch, git tools and others will take focus on the future.
"""

from pathlib import Path
from typing import (
    List,
    Optional,
    Self,
)

from pygit2 import (
    Commit,
    GitError,
    Index,
    Repository,
    Signature,
    clone_repository,
    init_repository,
)


class GitRepoError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def open_repo(repo: Repository | Path) -> Repository:
    """Open an existing git repository from a Path or Repository object."""
    if isinstance(repo, Repository):
        return repo
    if not isinstance(repo, Path):
        raise GitRepoError(
            f"Invalid repository type <{type(repo).__name__}>, expected <RepositoryOrPath>"
        )
    try:
        return Repository(str(repo))
    except KeyError, GitError:
        raise GitRepoError("Not a valid repository inited.")


def is_git(path: Path) -> bool:
    """Check if the given path is a valid git repository."""
    try:
        open_repo(repo=path)
        return True
    except GitRepoError:
        return False


class GitRepo:
    """
    TODO: log, status, tag
    """

    def __init__(self, repo: Repository | Path) -> None:
        self.repo = repo

    # ---------------------- class property ---------------------------
    @property
    def index(self) -> Index:
        """Get the repository index (staging area)."""
        return self.repo.index

    @property
    def repo(self) -> Repository:
        """Get the underlying native repository instance."""
        if not hasattr(self, "_repo"):
            setattr(self, "_repo", None)
        return getattr(self, "_repo")

    @property
    def workdir(self) -> Path:
        """Get the absolute path to the working directory."""
        return Path(self.repo.workdir).resolve()

    @repo.setter
    def repo(self, repo: Repository | Path) -> None:
        new_repo = open_repo(repo=repo)
        setattr(self, "_repo", new_repo)

    #  ---------------- repo methods ------------------
    @classmethod
    def init(cls, path: Path, bare: bool = False, **kwargs) -> "GitRepo":
        """Initialize a new git repository or open it if already initialized."""
        if is_git(path):
            return cls(open_repo(repo=path))
        if not path.exists():
            raise GitRepoError(
                f"Path does not exist: invalid try to init a repo at '{path}'."
            )
        native_repo = init_repository(str(path), bare=bare, **kwargs)
        return cls(native_repo)

    @classmethod
    def clone(cls, url: str, path: Path, **kwargs) -> "GitRepo":
        """Clone a remote git repository into a local directory."""
        if is_git(path):
            raise GitRepoError(
                f"Cannot clone: a valid git repository already exists at '{path}'."
            )
        native_repo = clone_repository(url, str(path), **kwargs)
        return cls(native_repo)

    # ------------- main methods -----------------------------
    def add(self, *files: Path) -> Self:
        """Stage files or all modifications to the repository index."""
        if len(files) == 0:
            self.index.add_all()
        else:
            for file_path in files:
                abs_path = file_path.resolve()
                try:
                    rel_path = abs_path.relative_to(self.workdir)
                    self.index.add(str(rel_path))
                except ValueError:
                    raise ValueError(
                        f"File {abs_path} out of repository {self.workdir}"
                    )
        self.index.write()
        return self

    def remove(self, *files: Path, staged_only: bool = False) -> Self:
        """Remove files from the repository index and optionally from the working directory."""
        for file_path in files:
            rel_path = file_path.resolve().relative_to(self.workdir)
            str_path = str(rel_path)

            if str_path in self.index:
                self.index.remove(str_path)

            if not staged_only:
                abs_path = self.workdir / rel_path
                if abs_path.exists():
                    abs_path.unlink()

        self.index.write()
        return self

    def move(self, source: Path, destination: Path) -> Self:
        """Move or rename a file within the working directory and update the index."""
        abs_src = source.resolve()
        abs_dst = destination.resolve()

        rel_src = abs_src.relative_to(self.workdir)
        rel_dst = abs_dst.relative_to(self.workdir)

        if abs_src.exists():
            abs_dst.parent.mkdir(parents=True, exist_ok=True)
            abs_src.rename(abs_dst)

        str_src = str(rel_src)
        if str_src in self.index:
            self.index.remove(str_src)

        self.index.add(str(rel_dst))
        self.index.write()
        return self

    def restore(self, *files: Path, ref: str = "HEAD") -> Self:
        """Discard local modifications by restoring files from a specific commit reference."""
        try:
            commit = self.repo.revparse_single(ref)
            commit_tree = commit.tree
        except KeyError:
            return self

        if len(files) == 0:
            self.repo.checkout_tree(
                commit_tree, strategy=1, directory=str(self.workdir)
            )
            self.index.read()
        else:
            for file_path in files:
                rel_path = file_path.resolve().relative_to(self.workdir)
                str_path = str(rel_path)

                self.repo.checkout_tree(
                    commit_tree,
                    strategy=1,
                    paths=[str_path],
                    directory=str(self.workdir),
                )

            self.index.read()
        return self

    def commit(
        self,
        author: Signature,
        committer: Signature,
        message: str,
        parents: Optional[List[Commit]] = None,
        ref: str = "HEAD",
    ) -> Self:
        """Commit staged changes to the repository history."""
        tree_oid = self.index.write_tree()
        if parents is None:
            parents = []
        if len(parents) == 0:
            try:
                current_tip = self.repo.revparse_single(ref)
                if isinstance(current_tip, Commit):
                    parents = [current_tip]
            except KeyError:
                pass
        self.repo.create_commit(ref, author, committer, message, tree_oid, parents)
        return self
