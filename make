#!usr/bin/env python3

import argparse
import ast
import datetime
import logging
from pathlib import Path

import tomlkit as tk

from goastty import SyncExecution, SyncTask
from goastty.liblinux.models import ObjectScript, ObjectShell

ROOT = Path(__file__).parent
SRC = ROOT / "src"


PYPROJECT_TOML = ROOT / "pyproject.toml"

if PYPROJECT_TOML.exists():
    try:
        CONFIG = tk.parse(PYPROJECT_TOML.read_text(encoding="utf-8"))
    except Exception:
        CONFIG = tk.document()
else:
    CONFIG = tk.document()

PROJECT = SRC
for a, b, c in SRC.walk():
    if "__project__.py" in c:
        PROJECT = a / "__project__.py"
        break

changelog_logger = logging.getLogger("changelog")
changelog_logger.setLevel(logging.INFO)
ch_handler = logging.FileHandler(ROOT / "change.log", encoding="utf-8")
ch_handler.setFormatter(logging.Formatter("%(message)s"))
changelog_logger.addHandler(ch_handler)

globals_dict = {}
if PROJECT.is_file():
    root_node = ast.parse(PROJECT.read_text(encoding="utf-8"))

    for node in root_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        globals_dict[target.id] = ast.literal_eval(node.value)
                    except ValueError:
                        pass


PROJECT_VERSION = globals_dict.get("__version__")
PROJECT_NAME = globals_dict.get("__project__")
PROJECT_AUTHOR = globals_dict.get("__author__")
PROJECT_EMAIL = globals_dict.get("__email__")
PROJECT_DESCRIPTION = globals_dict.get("__description__")
PROJECT_RELEASE_NOTE = globals_dict.get("__release__", {}).get(PROJECT_VERSION, "")


def update_pyproject():

    if "project" not in CONFIG:
        CONFIG.add("project", tk.table())

    CONFIG["project"]["name"] = PROJECT_NAME
    CONFIG["project"]["version"] = PROJECT_VERSION
    CONFIG["project"]["description"] = PROJECT_DESCRIPTION

    author_table = tk.inline_table()
    author_table["name"] = PROJECT_AUTHOR
    author_table["email"] = PROJECT_EMAIL

    authors_array = tk.array()
    authors_array.append(author_table)
    CONFIG["project"]["authors"] = authors_array

    PYPROJECT_TOML.write_text(tk.dumps(CONFIG), encoding="utf-8")


git = SyncTask("git")
git.config["pCwdDir"] = ROOT

script = ObjectScript(f"""
if [ ! -d ".git" ]; then
    git init
fi
if ! git config user.name >/dev/null 2>&1; then
    git config user.name "{PROJECT_AUTHOR}"
fi
if ! git config user.email >/dev/null 2>&1; then
    git config user.email "{PROJECT_EMAIL}"
fi
""")

sh = ObjectShell(shell="bash", cmd=script)
sh.run(get_err=True)

git_add_all = git.new("add", "--all")
git_commit = git.new("commit", "-m")
git_push = git.new("push")
git_tag = git.new("tag", "-a", f"v{PROJECT_VERSION}", "-m")


def git_run(task: SyncTask):
    execution = SyncExecution(task).run()
    stderr_bytes = task.stderr()

    if stderr_bytes:
        error_msg = stderr_bytes.decode("utf-8", errors="replace").strip()
        if error_msg:
            logging.error(f"Git Error [{task.cmd()}]: {error_msg}")

    return execution


def get_args():
    parser = argparse.ArgumentParser(
        description="Automation Gateway for goastty projects"
    )
    parser.add_argument("message", nargs="?", default=None, help="Commit/Tag message")
    parser.add_argument(
        "--commit", action="store_true", help="Stage all changes and commit"
    )
    parser.add_argument(
        "--freeze",
        action="store_true",
        help="Create an annotated tag for current version",
    )
    parser.add_argument(
        "--push", action="store_true", help="Push changes to remote repository"
    )
    return parser.parse_known_args()


def run(args: argparse.Namespace, unk: list[str]):
    update_pyproject()
    change_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = args.message if args.message else f"update: {change_time}"

    if args.commit:
        git_run(git_add_all)
        git_run(git_commit.new(*git_commit.args()).add(message))
        changelog_logger.info(f"NEW COMMIT: {message}")

    if args.freeze:
        tag_msg = PROJECT_RELEASE_NOTE if PROJECT_RELEASE_NOTE else message
        git_run(git_tag.new(*git_tag.args()).add(tag_msg))
        changelog_logger.info(f"NEW VERSION: {PROJECT_VERSION} -> {tag_msg}")

    if args.push:
        git_run(git_push.new(*git_push.args()).add(*unk))
        extra_args = " ".join(unk)
        changelog_logger.info(f"NEW PUSH: {extra_args}")


if __name__ == "__main__":
    parsed_args, unknown = get_args()
    run(parsed_args, unknown)
