# Copyright 1999-2023. Plesk International GmbH. All rights reserved.
from enum import Enum
import sys
if sys.version_info < (3, 8):
    import platform


class Distro(Enum):
    UNKNOWN = "Unknown"
    UNSUPPORTED = "Unsupported"
    CENTOS7 = "CentOS Linux 7"
    ALMALINUX8 = "AlmaLinux 8"
    DEBIAN10 = "Debian 10"
    DEBIAN11 = "Debian 11"
    DEBIAN12 = "Debian 12"
    UBUNTU18 = "Ubuntu 18"
    UBUNTU20 = "Ubuntu 20"
    UBUNTU22 = "Ubuntu 22"


DISTRO_MAPPING = {
    "CentOS Linux 7": Distro.CENTOS7,
    "AlmaLinux 8": Distro.ALMALINUX8,
    "Debian GNU/Linux 10": Distro.DEBIAN10,
    "Debian GNU/Linux 11": Distro.DEBIAN11,
    "Debian GNU/Linux 12": Distro.DEBIAN12,
    "Ubuntu 18": Distro.UBUNTU18,
    "Ubuntu 20": Distro.UBUNTU20,
    "Ubuntu 22": Distro.UBUNTU22,
}


def _is_deb_based(distro: Distro) -> bool:
    return distro in [
        Distro.UBUNTU18, Distro.UBUNTU20, Distro.UBUNTU22,
        Distro.DEBIAN10, Distro.DEBIAN11, Distro.DEBIAN12,
    ]


def _is_rhel_based(distro: Distro) -> bool:
    return distro in [
        Distro.CENTOS7, Distro.ALMALINUX8,
    ]


def _parse_os_relase():
    name = ""
    version = ""
    with open("/etc/os-release") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("NAME="):
                name = line.split("=")[1].strip().strip('"')
            elif line.startswith("VERSION_ID="):
                version = line.split("=")[1].strip().strip('"')

    return name, version


def get_distro() -> Distro:
    if hasattr(get_distro, "cache"):
        return get_distro.cache

    if sys.version_info < (3, 8):
        distro = platform.linux_distribution()
    else:
        distro = _parse_os_relase()

    name = distro[0]
    major_version = distro[1].split(".")[0]

    get_distro.cache = DISTRO_MAPPING.get(f"{name} {major_version}", Distro.UNKNOWN)  # type: ignore[attr-defined]

    return get_distro.cache  # type: ignore[attr-defined]


def get_distro_description(distro: Distro) -> str:
    for key, value in DISTRO_MAPPING.items():
        if value == distro:
            return key

    return "Unknown"
