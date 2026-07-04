from pathlib import Path

from pygit2 import Commit, Repository, Signature


class StageModel(list):
    def __init__(self, *files: Path) -> None:
        _resolved = []
        for file in files:
            if not isinstance(file, Path) or not file.exists():
                raise TypeError("files must be a valid <Path>")
            _resolved.append(file.resolve())
        super().__init__(_resolved)

    def relative_to(self, path: Path, as_string: bool = False):
        """Iterator of files in StageModel: yield the file path relative to given path"""
        for file in self:
            relative = file.relative_to(path)
            yield relative if not as_string else str(relative)

    def add_to(self, repo: "RepoModel"):
        """Add all paths in StageModel to index of given repo: default will add all files"""
        if not self:
            repo.idx.add_all()
            repo.idx.write()
            return repo
        for relative_path in self.relative_to(repo.wd):
            repo.idx.add(str(relative_path))
        repo.idx.write()
        return repo

    def restore_from(self, repo: "RepoModel", ref: str) -> "RepoModel":
        """Restore all files in StageModel of a especific reference from given repo"""
        try:
            commit_tree = repo.repo.revparse_single(ref).tree
        except KeyError:
            return repo

        paths = list(self.relative_to(repo.wd, as_string=True)) if self else None
        repo.repo.checkout_tree(
            commit_tree, strategy=1, paths=paths, directory=str(repo.wd)
        )
        repo.idx.read()
        return repo

    def remove_from(self, repo: "RepoModel", staged_only: bool = True):
        """Remove all files in StageModel or just staged files"""
        if self:
            for relative_path in self.relative_to(repo.wd):
                if str(relative_path) in repo.idx:
                    repo.idx.remove(str(relative_path))

                if not staged_only:
                    abstract_path = repo.wd / relative_path
                    if abstract_path.exists():
                        abstract_path.unlink()
        repo.idx.write()
        return repo

    def __bool__(self):
        return len(self) > 0


class RepoModel:
    def __init__(self, path: str | Path) -> None:
        self.repo = path

    @property
    def wd(self):
        """Give the workdir path resolved as PathLike"""
        return Path(self.repo.workdir).resolve()

    @property
    def idx(self):
        """Give the Index of RepoModel"""
        return self.repo.index

    @property
    def repo(self) -> Repository:
        """Give the Repository object of the RepoModel"""
        return getattr(self, "_repo", Repository())

    @repo.setter
    def repo(self, value: str | Path):
        if isinstance(value, str):
            new = Path(value)
        elif isinstance(value, Path):
            new = value
        else:
            raise TypeError("repo path must be a <str> or <Path> type")
        if (not new.exists()) or (not new.is_dir()):
            raise ValueError("repo path must be a valid dir path")

        self._repo = Repository(str(new))


class CommitModel:
    def __init__(self, author: Signature, committer: Signature) -> None:
        self.author = author
        self.committer = committer

    @property
    def message(self) -> str:
        """Message of the CommitModel: default will be empty string"""
        return getattr(self, "_message", "")

    @property
    def parents(self) -> list[Commit]:
        """Parents is a list of Commit: default return empty list"""
        return getattr(self, "_parents", [])

    @property
    def ref(self) -> str:
        """Repo reference: default HEAD"""
        return getattr(self, "_ref", "HEAD")

    @message.setter
    def message(self, value: str):
        if not isinstance(value, str):
            raise TypeError("message must be <str>")
        self._message = value

    @parents.setter
    def parents(self, value: list[Commit]):
        if not isinstance(value, list):
            raise TypeError("parents must be <list[Commit]>")

        if not all(isinstance(v, Commit) for v in value):
            raise TypeError("parents must be <list[Commit]>")

        self._parents = value

    @ref.setter
    def ref(self, value: str):
        if not isinstance(value, str):
            raise TypeError("ref must be <str>")
        self._ref = value

    def apply(self, repo: RepoModel, files: StageModel | None, autoadd: bool = True):
        """Apply the CommitModel to the given RepoModel"""
        if files is not None:
            repo = files.add_to(repo)
        else:
            if autoadd:
                repo.idx.add_all()
                repo.idx.write()
        tree_oid = repo.idx.write_tree()
        if len(self.parents) == 0:
            try:
                curr_tip = repo.repo.revparse_single(self.ref)
                if isinstance(curr_tip, Commit):
                    self.parents = [curr_tip]
            except KeyError:
                pass
        repo.repo.create_commit(
            self.ref, self.author, self.committer, self.message, tree_oid, self.parents
        )
        return repo
