# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import json
import os
import shutil
import subprocess
import typing

from pleskdistup.common import action, files, log, motd, util


class SetMinDovecotDhParamSize(action.ActiveAction):
    dhparam_size: int

    def __init__(self, dhparam_size: int):
        self.name = "increase Dovecot DH parameters size to 2048 bits"
        self.dhparam_size = dhparam_size

    def _is_required(self) -> bool:
        proc = subprocess.run(
            ["/usr/sbin/plesk", "sbin", "sslmng", "--show-config"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if proc.returncode != 0:
            log.warn(f"Failed to get ssl configuration by plesk sslmng: {proc.stdout}\n{proc.stderr}")
            return False

        try:
            sslmng_config = json.loads(proc.stdout)
            if int(sslmng_config["effective"]["dovecot"]["dhparams_size"]) >= self.dhparam_size:
                return False
        except json.JSONDecodeError:
            log.warn(f"Failed to parse plesk sslmng results: {proc.stdout}")
            return False
        except KeyError as e:
            log.warn(f"There is no parameter '{e}' in the sslmng output.")
            return False
        except Exception as e:
            log.warn(f"Failed to check sslmng configuration for dovecot: {e}. Type is {type(e)}")
            raise e

        return True

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        util.logged_check_call(
            [
                "/usr/sbin/plesk", "sbin", "sslmng",
                "--service", "dovecot",
                "--strong-dh",
                f"--dhparams-size={self.dhparam_size}",
            ]
        )
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self) -> int:
        return 5


class RestoreDovecotConfiguration(action.ActiveAction):
    dovecot_config_path: str
    temp_directory: str

    def __init__(self, temp_directory: str):
        self.name = "restore Dovecot configuration"
        self.dovecot_config_path = "/etc/dovecot/dovecot.conf"
        self.temp_directory = temp_directory

    def _is_required(self) -> bool:
        return os.path.exists(self.dovecot_config_path)

    def _prepare_action(self) -> action.ActionResult:
        files.backup_file(self.dovecot_config_path)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        path_to_backup = os.path.join(self.temp_directory, "dovecot.conf" + files.DEFAULT_BACKUP_EXTENSION)
        if os.path.exists(self.dovecot_config_path):
            shutil.copy(self.dovecot_config_path, path_to_backup)
            motd.add_finish_ssh_login_message(f"The dovecot configuration '{self.dovecot_config_path}' has been restored from original distro. Modern configuration was placed in '{path_to_backup}'.\n")

        files.restore_file_from_backup(self.dovecot_config_path)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        files.remove_backup(self.dovecot_config_path)
        return action.ActionResult()


class RestoreRoundcubeConfiguration(action.ActiveAction):
    roundcube_config_path: str
    roundcube_file_for_customizations: str
    save_path: str
    default_lines: typing.List[str]

    def __init__(self, temp_directory: str):
        self.name = "restore roundcube configuration"
        self.roundcube_config_path = "/usr/share/psa-roundcube/config/config.inc.php"
        self.roundcube_file_for_customizations = "/usr/share/psa-roundcube/config/config.local.php"
        self.save_path = os.path.join(temp_directory, os.path.basename(self.roundcube_config_path) + files.DEFAULT_BACKUP_EXTENSION)
        self.default_lines = [
            "$config = array();",
            "$config['db_dsnw'] = 'mysql://roundcube:"
        ]

    def _is_required(self) -> bool:
        return os.path.exists(self.roundcube_config_path)

    def _get_customizations(self, source_file_path: str) -> typing.List[str]:
        customizations = []
        with open(source_file_path, "r") as target:
            for line in target:
                if line.startswith("$config") and not any(line.startswith(skip) for skip in self.default_lines):
                    customizations.append(line)

        return customizations

    def _move_customizations(self, source_file_path: str, target_file_path: str) -> int:
        customizations = self._get_customizations(source_file_path)

        if len(customizations) == 0:
            return 0

        with open(target_file_path, "w") as target_file:
            for line in customizations:
                target_file.write(line)

        return len(customizations)

    def _prepare_action(self) -> action.ActionResult:
        if os.path.exists(self.roundcube_config_path):
            shutil.copy(self.roundcube_config_path, self.save_path)

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        if not os.path.exists(self.roundcube_file_for_customizations) and os.path.exists(self.save_path):
            if self._move_customizations(self.save_path, self.roundcube_file_for_customizations) > 0:
                os.unlink(self.save_path)
                motd.add_finish_ssh_login_message(f"The roundcube configuration customizations have been relocated to the file {self.roundcube_file_for_customizations!r}. This file should be included in the {self.roundcube_config_path!r}. If this inclusion is missing, please update Plesk to the latest version.\n")

            return action.ActionResult()

        if os.path.exists(self.save_path) and len(self._get_customizations(self.save_path)) > 0:
            motd.add_finish_ssh_login_message(f"Your roundcube configuration, located at {self.roundcube_config_path!r}, has been moved to {self.save_path!r}. Please transfer any necessary customizations into {self.roundcube_file_for_customizations!r}\n")

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        if os.path.exists(self.save_path):
            os.unlink(self.save_path)

        return action.ActionResult()
