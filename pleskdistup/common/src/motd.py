# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
import shutil

from . import files, log

MOTD_PATH = "/etc/motd"

IN_PROGRESS_MESSAGE_FORMAT = """
===============================================================================
Message from the Plesk dist-upgrader tool:
The server is being converted to {new_os}. Please wait. During the conversion the
server may reboot itself a few times.
To see the current conversion status, run the '{path_to_util} --status' command.
To monitor the conversion progress in real time, run the '{path_to_util} --monitor' command.
===============================================================================
"""


def restore_ssh_login_message(motd_path: str = MOTD_PATH) -> None:
    files.restore_file_from_backup(motd_path, remove_if_no_backup=True)


def add_inprogress_ssh_login_message(message: str, motd_path: str = MOTD_PATH) -> None:
    try:
        if not files.backup_exists(motd_path):
            files.backup_file(motd_path)

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
