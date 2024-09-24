# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import json
import os
import shutil
import subprocess

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
