# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import subprocess
import typing

from . import dist, log


def is_version_larger(left: str, right: str) -> bool:
    return MariaDBVersion(left) > MariaDBVersion(right)


def _get_mariadb_utilname() -> typing.Optional[str]:
    for utility in ("mariadb", "mysql"):
        if subprocess.run(["which", utility], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return utility

    return None


def is_mariadb_installed() -> bool:
    utility = _get_mariadb_utilname()
    if utility is None:
        return False
    elif utility == "mariadb":
        return True

    return "MariaDB" in subprocess.check_output([utility, "--version"], universal_newlines=True)


def is_mysql_installed() -> bool:
    utility = _get_mariadb_utilname()
    if utility is None or utility == "mariadb":
        return False

    return "MariaDB" not in subprocess.check_output([utility, "--version"], universal_newlines=True)


class MariaDBVersion():
    """Mariadb or mysql version representation class."""

    major: int
    minor: int
    patch: int

    def _extract_from_version_str(self, version: str):
        # Version string example is "8.2.24"
        major_part, minor_part, patch_part = version.split(".")[:3]
        self.major = int(major_part)
        self.minor = int(minor_part)
        self.patch = int(patch_part)

    def _extract_from_mysql_util(self, util_output: str):
        # String example: "mysql  Ver 15.1 Distrib 10.6.12-MariaDB, for debian-linux-gnu (x86_64) using  EditLine wrapper"
        major_part, minor_part, patch_part = util_output.split("Distrib ")[1].split(",")[0].split("-")[0].split(".")[:3]
        self.major = int(major_part)
        self.minor = int(minor_part)
        self.patch = int(patch_part)

    def __init__(self, to_extract: str):
        """Initialize a version object."""
        self.major = 0
        self.minor = 0
        self.patch = 0

        if to_extract[0].isdigit():
            self._extract_from_version_str(to_extract)
        elif "Distrib" in to_extract:
            self._extract_from_mysql_util(to_extract)
        else:
            raise ValueError(f"Cannot extract php version from '{to_extract}'")

    def __str__(self):
        """Return a string representation of a PHPVersion object."""
        return f"PHP {self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other):
        return self.major < other.major or (self.major == other.major and self.minor < other.minor) or (self.major == other.major and self.minor == other.minor and self.patch < other.patch)

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __ge__(self, other):
        return not self.__lt__(other)


def get_installed_mariadb_version() -> MariaDBVersion:
    utility = _get_mariadb_utilname()
    if not utility:
        raise RuntimeError("Unable to find mariadb or mysql utility")
    out = subprocess.check_output([utility, "--version"], universal_newlines=True)
    log.debug("Detected mariadb version is: {version}".format(version=out.split("Distrib ")[1].split(",")[0].split("-")[0]))
    return MariaDBVersion(out)


def get_mariadb_config_file_path() -> str:
    if dist._is_rhel_based(dist.get_distro()):
        return "/etc/my.cnf.d/server.cnf"
    return "/etc/mysql/mariadb.conf.d/50-server.cnf"


def get_mysql_config_file_path() -> str:
    if dist._is_rhel_based(dist.get_distro()):
        return "/etc/my.cnf.d/server.cnf"
    return "/etc/mysql/my.cnf"
