# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import shutil

from . import files, log

MOTD_PATH = "/etc/motd"


def restore_ssh_login_message(motd_path: str = MOTD_PATH) -> None:
    files.restore_file_from_backup(motd_path, remove_if_no_backup=True)


def add_inprogress_ssh_login_message(message: str, motd_path: str = MOTD_PATH) -> None:
    try:
        if not files.backup_exists(motd_path):
            if os.path.exists(motd_path):
                files.backup_file(motd_path)
            else:
                with open(motd_path + files.DEFAULT_BACKUP_EXTENSION, "a") as motd:
                    pass

        with open(motd_path, "a") as motd:
            motd.write(message)
    except FileNotFoundError:
        log.warn("The /etc/motd file cannot be changed or created. The utility may be lacking the permissions to do so.")


FINISH_INTRODUCE_MESSAGE = """
===============================================================================
Message from the Plesk dist-upgrader tool:
"""

FINISH_END_MESSAGE = """You can remove this message from the {} file.
===============================================================================
""".format(MOTD_PATH)


def add_finish_ssh_login_message(message: str, motd_path: str = MOTD_PATH) -> None:
    try:
        if not os.path.exists(motd_path + ".next"):
            if os.path.exists(motd_path + files.DEFAULT_BACKUP_EXTENSION):
                shutil.copy(motd_path + files.DEFAULT_BACKUP_EXTENSION, motd_path + ".next")

            with open(motd_path + ".next", "a") as motd:
                motd.write(FINISH_INTRODUCE_MESSAGE)

        with open(motd_path + ".next", "a") as motd:
            motd.write(message)
    except FileNotFoundError:
        log.warn("The /etc/motd file cannot be changed or created. The utility may be lacking the permissions to do so.")


def publish_finish_ssh_login_message(motd_path: str = MOTD_PATH) -> None:
    try:
        if os.path.exists(motd_path + ".next"):
            with open(motd_path + ".next", "a") as motd:
                motd.write(FINISH_END_MESSAGE)

            shutil.move(motd_path + ".next", motd_path)
        else:
            files.restore_file_from_backup(motd_path, remove_if_no_backup=True)
    except FileNotFoundError:
        log.warn("The /etc/motd file cannot be changed or created. The utility may be lacking the permissions to do so.")
