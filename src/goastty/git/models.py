from pathlib import Path

from pygit2 import Commit, Repository, Signature

from goastty.git.errors import GitRepoError


class StageModel(list):
    def __init__(self, *files: Path) -> None:
        if not all(isinstance(f, Path) for f in files):
            raise TypeError("files must be <Path>")
        _resolved = []
        for file in files:
            if (not isinstance(file, Path)) or (not file.exists()):
                raise TypeError("files must be <Path>")
            _resolved.append(file.resolve())
        super().__init__(*_resolved)

    def relative_to(self, path: Path, as_string: bool = False):
        for file in self:
            relative = file.relative_to(path)
            yield relative if not as_string else str(relative)

    def add_to(self, repo: RepoModel):
        if not self:
            repo.idx.add_all()
            return repo
        for relative_path in self.relative_to(repo.wd):
            repo.idx.add(str(relative_path))
        repo.idx.write()
        return repo

    def restore_from(self, repo: RepoModel, ref: str):
        try:
            commit = repo.repo.revparse_single(ref)
            commit_tree = commit.tree
        except KeyError:
            return self
        if not self:
            repo.repo.checkout_tree(commit_tree, strategy=1, directory=str(repo.wd))
            repo.idx.read()
            return repo

        for relative in self.relative_to(repo.wd, as_string=True):
            repo.repo.checkout_tree(
                commit_tree, strategy=1, paths=relative, directory=str(repo.wd)
            )
        repo.idx.read()
        return repo

    def remove_from(self, repo: RepoModel, staged_only: bool = True):
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
        return Path(self.repo.workdir).resolve()

    @property
    def idx(self):
        return self.repo.index

    @property
    def repo(self) -> Repository:
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
        return getattr(self, "_message", "")

    @property
    def parents(self) -> list[Commit]:
        return getattr(self, "_parents", [])

    @property
    def ref(self) -> str:
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

        if not all(True if isinstance(v, Commit) else False for v in value):
            raise TypeError("parents must be <list[Commit]>")

        self._parents = value

    @ref.setter
    def ref(self, value: str):
        if not isinstance(value, str):
            raise TypeError("ref must be <str>")
        self._ref = value

    def apply(self, repo: RepoModel, files: StageModel, autoadd: bool = True):
        if files is not None:
            repo = files.add_to(repo)
        else:
            if autoadd:
                repo.idx.add_all()
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
