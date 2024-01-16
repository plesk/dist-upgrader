# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
from pleskdistup.common import action

import os
import shutil


class RestoreCurrentSpamassasinConfiguration(action.ActiveAction):
    name: str
    state_dir: str
    spamassasin_config_path: str
    spamassasin_backup_path: str

    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        self.name = "restore current spamassassin configuration after conversion"
        self.spamassasin_config_path = "/etc/spamassassin/local.cf"
        self.spamassasin_backup_path = os.path.join(self.state_dir, "spamassasin_local.cf.backup")

    def _is_required(self) -> bool:
        return os.path.exists(self.spamassasin_config_path)

    def _prepare_action(self) -> action.ActionResult:
        shutil.copy(self.spamassasin_config_path, self.spamassasin_backup_path)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        shutil.copy(self.spamassasin_backup_path, self.spamassasin_config_path)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        os.unlink(self.spamassasin_backup_path)
        return action.ActionResult()
