# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os.path

from pleskdistup.common import action, debconf, dpkg, log

GRUB_PC_PACKAGE = "grub-pc"
GRUB_INSTALL_DEVICES_QUESTION = "grub-pc/install_devices"


class AssertGrubInstallDeviceExists(action.CheckAction):
    _FIX_HINT = """This could fail conversion - please fix GRUB configuration:
    dpkg --configure grub-pc
"""

    def __init__(self) -> None:
        self.name = "check GRUB installation device exists"
        self.description = ""

    def _do_check(self) -> bool:
        if not os.path.exists(debconf.DEBCONF_SHOW_CMD):
            return True

        # Only grub-pc's maintainer scripts read its debconf answers. They outlive the package
        # (or are preseeded without it), e.g. on hosts booting via UEFI with grub-efi-amd64
        if not dpkg.is_package_present(GRUB_PC_PACKAGE):
            log.debug("Package {} is not present, skipping the GRUB install device check".format(GRUB_PC_PACKAGE))
            return True

        devices = debconf.get_package_values(GRUB_PC_PACKAGE).get(GRUB_INSTALL_DEVICES_QUESTION)
        if devices is None:
            return True

        if not devices:
            self.description = "Grub's install-device list is empty\n" + self._FIX_HINT
            return False

        missing = [device for device in devices if not os.path.exists(device)]
        if missing:
            self.description = "Grub's install-device is not found: {}\n".format(", ".join(missing)) + self._FIX_HINT
            return False
        return True
