# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import os

from pleskdistup.common import action, mounts


FSTAB_PATH: str = "/etc/fstab"


class AssertFstabOrderingIsFine(action.CheckAction):
    def __init__(self):
        self.name = "checking if /etc/fstab is ordered properly"
        self.description = """The /etc/fstab file entries is not ordered properly.
\t- {}"""

    def _do_check(self) -> bool:
        if not os.path.exists(FSTAB_PATH):
            # Might be a problem, but it is not something we checking in scope of this check
            return True

        misorderings = mounts.get_fstab_configuration_misorderings(FSTAB_PATH)

        if len(misorderings) == 0:
            return True

        self.description = self.description.format("\n\t- ".join([f"Mount point {mount_point} should be placed after {parent_dir}" for parent_dir, mount_point in misorderings]))
        return False


class AssertFstabHasDirectRaidDevices(action.CheckAction):
    allow_raid_devices: bool

    def __init__(self, allow_raid_devices: bool = False):
        self.allow_raid_devices = allow_raid_devices
        self.name = "checking if /etc/fstab has direct RAID devices"
        self.description = """The /etc/fstab file has direct RAID devices entries.
A RAID device could be renamed after the conversion which will lead to unable to mount the device.
Potentially it could make the system unbootable.
To fix the issue, replace following direct RAID devices with the UUID:
\t- {}

Or you could skip the check by calling the tool with --allow-raid-devices option.
"""

    def _do_check(self) -> bool:
        if self.allow_raid_devices:
            return True

        if not os.path.exists(FSTAB_PATH):
            # Might be a problem, but it is not something we checking in scope of this check
            return True

        raid_devices_in_fstab = []
        with open(FSTAB_PATH, "r") as fstab_file:
            for line in fstab_file.readlines():
                if line.startswith("/dev/md"):
                    raid_devices_in_fstab.append(line.rstrip())

        if len(raid_devices_in_fstab) == 0:
            return True

        self.description = self.description.format("\n\t- ".join(raid_devices_in_fstab))
        return False


class AssertFstabHasNoDuplicates(action.CheckAction):
    def __init__(self):
        self.name = "checking if /etc/fstab has no duplicate mount points"
        self.description = """The /etc/fstab file contains duplicate mount points.
\tTo proceed with the conversion, you need to resolve following duplicates:
{}"""

    def _do_check(self) -> bool:
        if not os.path.exists(FSTAB_PATH):
            # Might be a problem, but it is not something we checking in scope of this check
            return True

        duplicates = mounts.get_fstab_duplicate_mount_points(FSTAB_PATH)

        if len(duplicates) == 0:
            return True

        duplicate_descriptions = []
        for mount_point, entries in duplicates.items():
            duplicate_descriptions.append(f"\t- Mount point '{mount_point}' appears {len(entries)} times:\n\t\t" + "\n\t\t".join(entries))

        self.description = self.description.format("\n".join(duplicate_descriptions))
        return False
