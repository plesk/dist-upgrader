# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import shutil
import sys
import typing

from pleskdistup.common import action, files, log, motd, plesk
from pleskdistup.phase import Phase


class MoveOldBindConfigToNamed(action.ActiveAction):
    def __init__(self):
        self.name = "move old BIND configuration to named"
        self.old_bind_config_path = "/etc/default/bind9"
        self.dst_config_path = "/etc/default/named"

    def _is_required(self) -> bool:
        return os.path.exists(self.old_bind_config_path)

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        log.debug(f"Moving {self.old_bind_config_path} to {self.dst_config_path}")
        shutil.move(self.old_bind_config_path, self.dst_config_path)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class AddFinishSshLoginMessage(action.ActiveAction):
    def __init__(self, new_os: str):
        self.name = "add finish SSH login message"
        self.finish_message = f"""
The server has been upgraded to {new_os}.
"""

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        log.debug("Adding 'finished' login message...")
        motd.add_finish_ssh_login_message(self.finish_message)
        motd.publish_finish_ssh_login_message()
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class AddInProgressSshLoginMessage(action.ActiveAction):
    def __init__(self, new_os: str):
        self.name = "add in progress SSH login message"
        util_name = os.path.basename(sys.argv[0])
        path_to_util = os.path.abspath(sys.argv[0])
        self.in_progress_message = f"""
===============================================================================
Message from the Plesk dist-upgrader tool:
The server is being converted to {new_os}. Please wait. During the conversion the
server may reboot itself a few times.
To see the current conversion status, run the '{path_to_util} --status' command.
To monitor the conversion progress in real time, run the '{path_to_util} --monitor' command.
===============================================================================
"""

    def _prepare_action(self) -> action.ActionResult:
        log.debug("Adding 'in progress' login message...")
        motd.add_inprogress_ssh_login_message(self.in_progress_message)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        motd.restore_ssh_login_message()
        return action.ActionResult()


class DisablePleskSshBanner(action.ActiveAction):
    def __init__(self):
        self.name = "disable Plesk SSH banner"
        self.banner_command_path = "/root/.plesk_banner"

    def _prepare_action(self) -> action.ActionResult:
        log.debug("Disabling Plesk login banner")
        if os.path.exists(self.banner_command_path):
            files.backup_file(self.banner_command_path)
            os.unlink(self.banner_command_path)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        files.restore_file_from_backup(self.banner_command_path)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        files.restore_file_from_backup(self.banner_command_path)
        return action.ActionResult()


class HandleConversionStatus(action.ActiveAction):
    name: str
    status_flag_path: str
    completion_flag_path: str

    def __init__(
        self,
        status_flag_path: str,
        completion_flag_path: str,
    ):
        self.name = "prepare and send conversion status"
        self.status_flag_path = status_flag_path
        self.completion_flag_path = completion_flag_path

    def _prepare_action(self) -> action.ActionResult:
        log.debug(f"Preparing conversion flag {self.status_flag_path!r}")
        plesk.prepare_conversion_flag(self.status_flag_path)
        if os.path.exists(self.completion_flag_path):
            log.debug(f"Removing existing completion flag {self.status_flag_path!r}")
            os.unlink(self.completion_flag_path)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        log.debug(f"Sending conversion status (status flag path is {self.status_flag_path!r})")
        plesk.send_conversion_status(True, self.status_flag_path)
        with open(self.completion_flag_path, "w"):
            log.debug(f"Creating completion flag {self.completion_flag_path!r}")
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        log.debug(f"Removing conversion flag {self.status_flag_path}")
        plesk.remove_conversion_flag(self.status_flag_path)
        return action.ActionResult()


class CleanApparmorCacheConfig(action.ActiveAction):
    def __init__(self):
        self.name = "clean AppArmor cache configuration"
        self.possible_locations = ["/etc/apparmor/cache", "/etc/apparmor.d/cache"]

    def _is_required(self) -> bool:
        return len([location for location in self.possible_locations if os.path.exists(location)]) > 0

    def _prepare_action(self) -> action.ActionResult:
        log.debug("Cleaning AppArmor cache configuration")
        for location in self.possible_locations:
            if os.path.exists(location):
                shutil.move(location, location + ".backup")
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        log.debug("Cleaning up backups of AppArmor cache configuration")
        for location in self.possible_locations:
            location = location + ".backup"
            if os.path.exists(location):
                shutil.rmtree(location)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        log.debug("Restoring backups of AppArmor cache configuration")
        for location in self.possible_locations:
            if os.path.exists(location):
                shutil.move(location + ".backup", location)
        return action.ActionResult()

    def estimate_prepare_time(self):
        return 1

    def estimate_post_time(self):
        return 1

    def estimate_revert_time(self):
        return 1


# This action requests reboot to be performed at the end of the current stage
class Reboot(action.ActiveAction):
    prepare_reboot: typing.Optional[action.RebootType]
    prepare_next_phase: typing.Optional[Phase]
    post_reboot: typing.Optional[action.RebootType]
    post_next_phase: typing.Optional[Phase]
    name: str

    def __init__(
        self,
        prepare_reboot: typing.Optional[action.RebootType] = action.RebootType.AFTER_CURRENT_STAGE,
        prepare_next_phase: typing.Optional[Phase] = None,
        post_reboot: typing.Optional[action.RebootType] = None,
        post_next_phase: typing.Optional[Phase] = None,
        name: str = "reboot the system",
    ):
        self.prepare_reboot = prepare_reboot
        self.prepare_next_phase = prepare_next_phase
        self.post_reboot = post_reboot
        self.post_next_phase = post_next_phase
        self.name = name

    def _prepare_action(self) -> action.ActionResult:
        log.debug(f"Returning request to reboot the system '{self.prepare_reboot}' and switch phase to '{self.prepare_next_phase}'")
        return action.ActionResult(
            reboot_requested=self.prepare_reboot,
            next_phase=self.prepare_next_phase,
        )

    def _post_action(self) -> action.ActionResult:
        log.debug(f"Returning request to reboot the system '{self.post_reboot}' and switch phase to '{self.post_next_phase}'")
        return action.ActionResult(
            reboot_requested=self.post_reboot,
            next_phase=self.post_next_phase,
        )

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self):
        return 60 if self.prepare_reboot else 0

    def estimate_post_time(self):
        return 60 if self.post_reboot else 0

    def estimate_revert_time(self):
        return 0
