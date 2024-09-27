# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os.path

from pleskdistup.common import action, util

DEBCONF_CMD = "/usr/bin/debconf-show"


class AssertGrubInstallDeviceExists(action.CheckAction):
    def __init__(self) -> None:
        self.name = "check GRUB installation device exists"
        self.description = """Grub's install-device is not found: {}
This could fail conversion - please fix GRUB configuration:
    dpkg --configure grub-pc
"""

    def _do_check(self) -> bool:
        if not os.path.exists(DEBCONF_CMD):
            return True

        param = "grub-pc"
        debconf_out = util.logged_check_call([DEBCONF_CMD, param])
        prefix = "{}/install_devices:".format(param)
        for line in debconf_out.split("\n"):
            idx = line.find(prefix)
            if idx != -1:
                devpath = line[idx+len(prefix):].strip()
                if not os.path.exists(devpath):
                    self.description = self.description.format(devpath)
                    return False
        return True
