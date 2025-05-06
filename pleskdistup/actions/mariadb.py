# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import os
import subprocess
import typing
from abc import ABC, abstractmethod

from pleskdistup.common import action, dpkg, files, log, mariadb, motd, packages, systemd


MARIADB_VERSION_ON_UBUNTU_20 = mariadb.MariaDBVersion("10.3.38")


class AddMysqlConnector(action.ActiveAction):
    def __init__(self):
        self.name = "install MySQL connector"

    def _is_required(self) -> bool:
        return mariadb.is_mysql_installed()

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        subprocess.check_call(["/usr/bin/dnf", "install", "-y", "mariadb-connector-c"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


def get_db_server_config_file():
    return mariadb.get_mysql_config_file_path() if mariadb.is_mysql_installed() else mariadb.get_mariadb_config_file_path()


class DisableMariadbInnodbFastShutdown(action.ActiveAction):
    def __init__(self):
        self.name = "disable MariaDB InnoDB fast shutdown"

    def _is_required(self) -> bool:
        return mariadb.is_mariadb_installed() or mariadb.is_mysql_installed()

    def _prepare_action(self) -> action.ActionResult:
        target_file = get_db_server_config_file()
        files.cnf_set_section_variable(target_file, "mysqld", "innodb_fast_shutdown", "0")
        systemd.restart_services(["mariadb", "mysql"])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        target_file = get_db_server_config_file()
        files.cnf_unset_section_variable(target_file, "mysqld", "innodb_fast_shutdown")
        systemd.restart_services(["mariadb", "mysql"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        target_file = get_db_server_config_file()
        files.cnf_unset_section_variable(target_file, "mysqld", "innodb_fast_shutdown")
        systemd.restart_services(["mariadb", "mysql"])
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 15

    def estimate_post_time(self) -> int:
        return 15

    def estimate_revert_time(self) -> int:
        return 15


class InstallUbuntu20Mariadb(action.ActiveAction):
    def __init__(self):
        self.name = "install MariaDB from Ubuntu 20 official repository"

    def _is_required(self) -> bool:
        return mariadb.is_mariadb_installed() and MARIADB_VERSION_ON_UBUNTU_20 > mariadb.get_installed_mariadb_version()

    def _prepare_action(self) -> action.ActionResult:
        dpkg.depconfig_parameter_set("libraries/restart-without-asking", "true")
        packages.install_packages(["mariadb-server-10.3"], force_package_config=True)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        dpkg.depconfig_parameter_set("libraries/restart-without-asking", "false")
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        dpkg.depconfig_parameter_set("libraries/restart-without-asking", "false")
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 60


class DisableUnsupportedMysqlModes(action.ActiveAction):
    def __init__(self):
        self.name = "disable MySQL modes not supported by MySQL 8.0"
        self.deprecated_modes = [
            "ONLY_FULL_GROUP_BY",
            "STRICT_TRANS_TABLES",
            "NO_ZERO_IN_DATE",
            "NO_ZERO_DATE",
            "ERROR_FOR_DIVISION_BY_ZERO",
            "NO_AUTO_CREATE_USER",
            "NO_ENGINE_SUBSTITUTION",
        ]

    def _is_required(self) -> bool:
        return mariadb.is_mysql_installed()

    def _prepare_action(self) -> action.ActionResult:
        for config_file in files.find_files_case_insensitive("/etc/mysql", "*.cnf", True):
            files.backup_file(config_file)
            for mode in self.deprecated_modes:
                files.replace_string(config_file, mode + ",", " ")
                files.replace_string(config_file, mode, " ")
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for config_file in files.find_files_case_insensitive("/etc/mysql", "*.cnf", True):
            files.remove_backup(config_file)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for config_file in files.find_files_case_insensitive("/etc/mysql", "*.cnf", True):
            files.restore_file_from_backup(config_file)
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 10

    def estimate_post_time(self) -> int:
        return 10

    def estimate_revert_time(self) -> int:
        return 10


class ConfigValueOperator(ABC):
    # value = None means "not existing"
    # Return value of None means "remove setting"
    @abstractmethod
    def apply(self, value) -> typing.Optional[str]:
        pass


class ConfigValueReplacer(ConfigValueOperator):
    new_value: typing.Optional[str]
    old_value: typing.Optional[str]

    # new_value = None means "remove setting"
    # old_value = None means "any value"
    def __init__(
        self,
        new_value: typing.Optional[str],
        old_value: typing.Optional[str] = None,
    ):
        if new_value is None and old_value is None:
            raise ValueError("new_value and old_value can't be both None")
        self.new_value = new_value
        self.old_value = old_value

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

    def apply(self, value: str) -> typing.Optional[str]:
        if self.new_value is None and self.old_value is None:
            raise ValueError("new_value and old_value can't be both None")
        if self.old_value is not None:
            if value == self.old_value:
                log.debug(f"{self.__class__.__name__}: replacing {value!r} with {self.new_value!r}")
                return self.new_value
        else:
            log.debug(f"{self.__class__.__name__}: replacing {value!r} with {self.new_value!r}")
            return self.new_value
        log.debug(f"{self.__class__.__name__}: keeping {value!r}")
        return value


class ConfigureMariadb(action.ActiveAction):
    settings: typing.Dict[str, typing.Dict[str, ConfigValueOperator]]
    name: str
    conf_file: str

    # Settings is a dictionary where keys are setting names in the
    # format "<section>.<name>" and values are dictionaries with three
    # possible keys "prepare", "post", "revert" mapping to desired
    # ConfigValueOperator to apply to the setting at that stage
    def __init__(
        self,
        settings: typing.Dict[str, typing.Dict[str, ConfigValueOperator]],
        name: str = "configure MariaDB/MySQL",
        conf_file: str = "/etc/mysql/my.cnf",
    ):
        self.name = name
        self.settings = settings
        self.conf_file = conf_file

    def _is_required(self) -> bool:
        return (mariadb.is_mariadb_installed() or mariadb.is_mysql_installed()) and os.path.exists(self.conf_file)

    def _stage_action(self, stage: str) -> action.ActionResult:
        for key, setting in self.settings.items():
            if stage in setting:
                section, name = key.split('.')
                old_val = files.cnf_get_section_variable(self.conf_file, section, name)
                new_val = setting[stage].apply(old_val)
                log.debug(f"{setting[stage]} maps the value of {key!r} from {old_val!r} to {new_val!r} in {self.conf_file}")
                if new_val is not None:
                    log.debug(f"Setting {section}.{name} to {new_val} in {self.conf_file}")
                    files.cnf_set_section_variable(self.conf_file, section, name, new_val)
                else:
                    log.debug(f"Unsetting {section}.{name} in {self.conf_file}")
                    files.cnf_unset_section_variable(self.conf_file, section, name)
        systemd.restart_services(["mariadb", "mysql"])
        return action.ActionResult()

    def _has_stage(self, stage: str) -> bool:
        return any(stage in setting for setting in self.settings.values())

    def _prepare_action(self) -> action.ActionResult:
        return self._stage_action("prepare")

    def _post_action(self) -> action.ActionResult:
        return self._stage_action("post")

    def _revert_action(self) -> action.ActionResult:
        return self._stage_action("revert")

    def estimate_prepare_time(self) -> int:
        return 15 if self._has_stage("prepare") else 0

    def estimate_post_time(self) -> int:
        return 15 if self._has_stage("post") else 0

    def estimate_revert_time(self) -> int:
        return 15 if self._has_stage("revert") else 0


class HoldMariadbAmbientCapabilities(action.ActiveAction):
    # Action required in some specific cases, when AmbientCapabilities can cause problems with package re-installation.
    # For example when CAP_IPC_LOCK enabled during deb-based dist-upgrade, we have troubles
    # with mariadb service starting which causes problems with psa-phpmyadmin package.
    path_to_override: str

    def __init__(self, override_path: str = "/etc/systemd/system/mariadb.service.d/override.conf"):
        self.name = "hold MariaDB systemd service AmbientCapabilities disabled"
        self.path_to_override = override_path

    def _is_required(self):
        return systemd.is_service_exists("mariadb")

    def _prepare_action(self):
        if not os.path.exists(os.path.dirname(self.path_to_override)):
            os.makedirs(os.path.dirname(self.path_to_override), exist_ok=True)

        if os.path.exists(self.path_to_override) and not files.backup_exists(self.path_to_override):
            files.backup_file(self.path_to_override)

        systemd.inject_systemd_config(
            self.path_to_override,
            "Service",
            "AmbientCapabilities",
            "",
        )
        systemd.reload_systemd_daemon()

        return action.ActionResult()

    def _post_action(self):
        files.restore_file_from_backup(self.path_to_override, remove_if_no_backup=True)
        systemd.reload_systemd_daemon()
        systemd.restart_services(["mariadb"])
        return action.ActionResult()

    def _revert_action(self):
        files.restore_file_from_backup(self.path_to_override, remove_if_no_backup=True)
        systemd.reload_systemd_daemon()
        systemd.restart_services(["mariadb"])
        return action.ActionResult()


class PreserveMariadbConfig(action.ActiveAction):
    def __init__(self):
        self.name: str = "preserve mariadb config files"
        # Potentially could be turned into array, but seems like my.cnf is enough for now
        self.mariadb_config_path: str = "/etc/my.cnf"
        self.motd_preserved_message_fmt: str = "The old MariaDB configuration file has been preserved as {preserved_path}.\n"

    def _is_required(self) -> bool:
        return os.path.exists(self.mariadb_config_path)

    def _prepare_action(self) -> action.ActionResult:
        files.backup_file(self.mariadb_config_path)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        path_to_preserved: typing.Optional[str] = packages.handle_configuration_files_conflict(self.mariadb_config_path)
        if path_to_preserved is None:
            path_to_preserved = files.get_backup_filename(self.mariadb_config_path)
        else:
            files.remove_backup(self.mariadb_config_path, raise_exception=False)

        motd.add_finish_ssh_login_message(self.motd_preserved_message_fmt.format(preserved_path=path_to_preserved))

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        files.remove_backup(self.mariadb_config_path, raise_exception=False)
        return action.ActionResult()
