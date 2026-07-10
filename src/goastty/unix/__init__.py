import grp
import os
import pwd
from pathlib import Path

from goastty.unix.models import ObjectScript, ObjectShell


def group_name_exists(group: str) -> bool:
    try:
        grp.getgrnam(group)
        return True
    except KeyError:
        return False


def is_curr_user_in_group(group: str) -> bool:
    if not group_name_exists(group):
        return False

    target_gid = grp.getgrnam(group).gr_gid
    user_gids = os.getgroups()
    user_gids.append(os.getgid())

    if target_gid in user_gids:
        return True
    username = pwd.getpwuid(os.getuid()).pw_name
    return username in grp.getgrnam(group).gr_mem


def is_path_in_group(group_path="", group_name="", is_dir=True):
    real_path = os.path.expandvars(group_path)
    dir_path = Path(real_path)

    if not dir_path.exists():
        return False

    if is_dir and not dir_path.is_dir():
        return False

    if not group_name_exists(group_name):
        return False

    target_gid = grp.getgrnam(group_name).gr_gid
    current_dir_gid = dir_path.stat().st_gid
    return current_dir_gid == target_gid


def create_group(
    group_name="", group_path="", write=True, user="", recursive=True
) -> bool:
    script = []
    if not group_name_exists(group_name):
        script.append(f"sudo groupadd {group_name}")

    if not is_path_in_group(group_path, group_name, recursive):
        script.append(
            f"sudo chgrp {'-R' if recursive else ''} {group_name} {group_path}"
        )
        permission = "r" + ("w" if write else "")
        script.append(
            f"sudo chmod {'-R' if recursive else ''} g+{permission} {group_path}"
        )

    user = user if user else pwd.getpwuid(os.getuid()).pw_name
    if not is_curr_user_in_group(group_name):
        script.append(f"sudo usermod -aG {group_name} {user}")

    if len(script) == 0:
        return True
    else:
        to_execute = ObjectScript("\n".join(script))
        shell = ObjectShell(shell="bash", cmd=to_execute)
        shell.run(get_err=True)

        if shell.shell.data.stderr.decode().strip():
            return False
        else:
            return True
