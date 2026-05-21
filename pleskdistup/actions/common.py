# Copyright 2023-2026. WebPros International GmbH. All rights reserved.
import os
import shutil
import subprocess
import sys
import time
import typing

from pleskdistup.common import action, dns, files, log, motd, plesk, rpm, util
from pleskdistup.phase import Phase


class FixNamedConfig(action.ActiveAction):
    def __init__(self):
        self.name = "fix named configuration"
        self.named_conf = "/etc/named.conf"
        self.chrooted_configuration_path = "/var/named/chroot"

    def _is_required(self) -> bool:
        return os.path.exists(self.named_conf) and os.path.exists(os.path.join(self.chrooted_configuration_path, self.named_conf))

    def _handle_included_file(self, chrooted_file: str):
        target_file = chrooted_file.replace(self.chrooted_configuration_path, "")

        target_file_directory = os.path.dirname(target_file)
        if not os.path.exists(target_file_directory):
            os.makedirs(target_file_directory)

        if not os.path.exists(target_file):
            if os.path.exists(chrooted_file):
                os.symlink(chrooted_file, target_file)
            else:
                with open(target_file, "w") as _:
                    pass

        if os.path.getsize(target_file) == 0:
            with open(target_file, "w") as f:
                f.write("# almalinux8to9 workaround commentary")

    def _prepare_action(self) -> action.ActionResult:
        for bind_configs in dns.get_all_includes_from_bind_config(self.named_conf, chroot_dir=self.chrooted_configuration_path):
            self._handle_included_file(bind_configs)

        return action.ActionResult()

    def _remove_included_files(self, chrooted_file: str):
        target_file = chrooted_file.replace(self.chrooted_configuration_path, "")
        if os.path.islink(target_file):
            os.unlink(target_file)

    def _post_action(self) -> action.ActionResult:
        for bind_configs in dns.get_all_includes_from_bind_config(self.named_conf, chroot_dir=self.chrooted_configuration_path):
            self._remove_included_files(bind_configs)

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for bind_configs in dns.get_all_includes_from_bind_config(self.named_conf, chroot_dir=self.chrooted_configuration_path):
            self._remove_included_files(bind_configs)

        return action.ActionResult()


class DisableSuspiciousKernelModules(action.ActiveAction):
    suspicious_modules: typing.Set[str]
    modules_config_path: str

    def __init__(self) -> None:
        self.name = "disable suspicious kernel modules"
        self.suspicious_modules = {"pata_acpi", "btrfs", "floppy"}
        self.modules_config_path = "/etc/modprobe.d/pataacpibl.conf"

    def _get_enabled_modules(self, lookup_modules: typing.Set[str]) -> typing.Set[str]:
        modules = set()
        modules_list = subprocess.check_output(["/usr/sbin/lsmod"], universal_newlines=True).splitlines()
        for line in modules_list:
            module_name = line[:line.find(' ')]
            if module_name in lookup_modules:
                modules.add(module_name)
        return modules

    def _prepare_action(self) -> action.ActionResult:
        with open(self.modules_config_path, "a") as kern_mods_config:
            for suspicious_module in self.suspicious_modules:
                kern_mods_config.write(f"blacklist {suspicious_module}\n")

        for enabled_modules in self._get_enabled_modules(self.suspicious_modules):
            util.logged_check_call(["/usr/sbin/rmmod", enabled_modules])

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for module in self.suspicious_modules:
            files.replace_string(self.modules_config_path, "blacklist " + module, "")

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        if not os.path.exists(self.modules_config_path):
            return action.ActionResult()

        for module in self.suspicious_modules:
            files.replace_string(self.modules_config_path, "blacklist " + module, "")

        return action.ActionResult()


class RecreateAwstatsConfigurationFiles(action.ActiveAction):
    def __init__(self) -> None:
        self.name = "recreate AWStats configuration files for domains"

    def get_awstats_domains(self) -> typing.Set[str]:
        domains_awstats_directory = "/usr/local/psa/etc/awstats/"
        domains: typing.Set[str] = set()
        if not os.path.exists(domains_awstats_directory):
            return domains
        for awstats_config_file in os.listdir(domains_awstats_directory):
            if awstats_config_file.startswith("awstats.") and awstats_config_file.endswith("-http.conf"):
                domains.add(awstats_config_file.split("awstats.")[-1].rsplit("-http.conf")[0])
        return domains

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        rpm.handle_all_rpmnew_files("/etc/awstats")

        for domain in self.get_awstats_domains():
            log.info(f"Recreating AWStats configuration for domain: {domain}")
            util.logged_check_call(
                [
                    "/usr/sbin/plesk", "sbin", "webstatmng", "--set-configs",
                    "--stat-prog", "awstats", "--domain-name", domain
                ], stdin=subprocess.DEVNULL
            )
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self) -> int:
        # Estimate 100 ms per configuration we have to recreate
        return int(len(self.get_awstats_domains()) / 10) + 5


class MoveOldBindConfigToNamed(action.ActiveAction):
    old_bind_config_path: str
    dst_config_path: str

    def __init__(self) -> None:
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
    """Add dist-upgrade finish message to MOTD.

    Args:
        new_os: New OS name and version.
    """
    finish_message: str

    def __init__(self, new_os: str) -> None:
        self.name = "add finish SSH login message"
        self.finish_message = f"""The server has been upgraded to {new_os}.\n"""

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
    in_progress_message: str

    def __init__(self, new_os: str) -> None:
        self.name = "add in progress SSH login message"
        path_to_util = os.path.abspath(sys.argv[0])
        self.in_progress_message = motd.IN_PROGRESS_MESSAGE_FORMAT.format(new_os=new_os, path_to_util=path_to_util)

    def _should_be_repeated_if_succeeded(self):
        # We should repeat this action on restarting the script
        # because the message might be substituted with failure message
        return True

    def _prepare_action(self) -> action.ActionResult:
        log.debug("Adding 'in progress' login message...")
        motd.restore_ssh_login_message()
        motd.add_inprogress_ssh_login_message(self.in_progress_message)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        motd.restore_ssh_login_message()
        return action.ActionResult()


class RestoreInProgressSshLoginMessage(action.ActiveAction):
    in_progress_message: str

    def __init__(self, new_os: str) -> None:
        self.name = "restore in progress SSH login message"
        path_to_util = os.path.abspath(sys.argv[0])
        self.in_progress_message = motd.IN_PROGRESS_MESSAGE_FORMAT.format(new_os=new_os, path_to_util=path_to_util)

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        log.debug("Restore 'in progress' login message...")
        motd.restore_ssh_login_message()
        motd.add_inprogress_ssh_login_message(self.in_progress_message)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class DisablePleskSshBanner(action.ActiveAction):
    banner_command_path: str

    def __init__(self) -> None:
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
    status_flag_path: str
    completion_flag_path: str

    def __init__(
        self,
        status_flag_path: str,
        completion_flag_path: str,
    ) -> None:
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
    possible_locations: typing.List[str]

    def __init__(self) -> None:
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

    def estimate_prepare_time(self) -> int:
        return 1

    def estimate_post_time(self) -> int:
        return 1

    def estimate_revert_time(self) -> int:
        return 1


# This action requests reboot to be performed at the end of the current stage
class Reboot(action.ActiveAction):
    prepare_reboot: typing.Optional[action.RebootType]
    prepare_next_phase: typing.Optional[Phase]
    post_reboot: typing.Optional[action.RebootType]
    post_next_phase: typing.Optional[Phase]
    do_before_post_reboot: typing.Callable[[], None]

    def __init__(
        self,
        prepare_reboot: typing.Optional[action.RebootType] = action.RebootType.AFTER_CURRENT_STAGE,
        prepare_next_phase: typing.Optional[Phase] = None,
        post_reboot: typing.Optional[action.RebootType] = None,
        post_next_phase: typing.Optional[Phase] = None,
        name: str = "reboot the system",
        do_before_post_reboot: typing.Callable[[], None] = lambda: None,
    ) -> None:
        self.prepare_reboot = prepare_reboot
        self.prepare_next_phase = prepare_next_phase
        self.post_reboot = post_reboot
        self.post_next_phase = post_next_phase
        self.name = name
        self.do_before_post_reboot = do_before_post_reboot

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
            do_before_reboot=self.do_before_post_reboot,
        )

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 60 if self.prepare_reboot else 0

    def estimate_post_time(self) -> int:
        return 60 if self.post_reboot else 0

    def estimate_revert_time(self) -> int:
        return 0


class DisableSelinuxDuringUpgrade(action.ActiveAction):
    selinux_config: str
    getenforce_cmd: str

    def __init__(self) -> None:
        self.name = "rule selinux status"
        self.selinux_config = "/etc/selinux/config"
        self.getenforce_cmd = "/usr/sbin/getenforce"

    def _is_required(self) -> bool:
        if not os.path.exists(self.selinux_config) or not os.path.exists(self.getenforce_cmd):
            return False

        return subprocess.check_output([self.getenforce_cmd], universal_newlines=True).strip() == "Enforcing"

    def _prepare_action(self) -> action.ActionResult:
        files.replace_string(self.selinux_config, "SELINUX=enforcing", "SELINUX=permissive")
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        files.replace_string(self.selinux_config, "SELINUX=permissive", "SELINUX=enforcing")
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        files.replace_string(self.selinux_config, "SELINUX=permissive", "SELINUX=enforcing")
        return action.ActionResult()


class PreRebootPause(action.ActiveAction):
    pause_time: int
    message: str

    def __init__(self, reboot_message: str, pause_time: int = 45) -> None:
        self.name = "pause before reboot"
        self.pause_time = pause_time
        self.message = reboot_message

    def _prepare_action(self) -> action.ActionResult:
        print(self.message)
        time.sleep(self.pause_time)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class RevertChangesInGrub(action.ActiveAction):
    grub_configs_paths: typing.List[str]

    def __init__(self) -> None:
        self.name = "revert changes in GRUB made by ELevate"
        self.grub_configs_paths = [
            "/boot/grub2/grub.cfg",
            "/boot/grub2/grubenv",
            "/boot/grub/grub.cfg",
            "/boot/grub/grubenv",
        ]

    def _prepare_action(self) -> action.ActionResult:
        for config in self.grub_configs_paths:
            if os.path.exists(config):
                files.backup_file(config)

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for config in self.grub_configs_paths:
            if os.path.exists(config):
                files.remove_backup(config)

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for config in self.grub_configs_paths:
            if os.path.exists(config):
                files.restore_file_from_backup(config)

        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 1

    def estimate_post_time(self) -> int:
        return 1

    def estimate_revert_time(self) -> int:
        return 1


class SubstituteSshPermitRootLoginConfigured(action.ActiveAction):
    sshd_config_path: str

    def __init__(self) -> None:
        self.name = "substitute known PermitRootLogin values in sshd_config"
        self.sshd_config_path = "/etc/ssh/sshd_config"

    def _prepare_action(self) -> action.ActionResult:
        if not os.path.exists(self.sshd_config_path):
            return action.ActionResult()

        files.backup_file(self.sshd_config_path)
        # We know that without-password is an outdated equivalent of prohibit-password
        # so we could just replace it with the new value
        files.replace_string(
            self.sshd_config_path,
            "PermitRootLogin without-password",
            "PermitRootLogin prohibit-password"
        )
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        if not os.path.exists(self.sshd_config_path):
            return action.ActionResult()

        files.restore_file_from_backup(self.sshd_config_path)
        return action.ActionResult()
