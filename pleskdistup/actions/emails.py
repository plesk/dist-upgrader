# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import json
import subprocess

from pleskdistup.common import action, log, util


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
