# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import sys
from abc import ABC, abstractmethod
from functools import lru_cache

if sys.version_info < (3, 8):
    import platform


class Distro(ABC):
    def __str__(self) -> str:
        return f"{self.name} {self.version}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, version={self.version!r})"

    def __eq__(self, other) -> bool:
        return self.name == other.name and self.version == other.version

    @property
    @abstractmethod
    def deb_based(self) -> bool:
        pass

    @property
    @abstractmethod
    def rhel_based(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass


class UnknownDistro(Distro):
    _name: str
    _version: str

    def __init__(
        self,
        name: str = "",
        version: str = "",
    ):
        super().__init__()
        self._name = name
        self._version = version

    @property
    def deb_based(self) -> bool:
        return False

    @property
    def rhel_based(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return self._name or "Unknown"

    @property
    def version(self) -> str:
        return self._version or "Unknown"


class DebBasedDistro(Distro):
    @property
    def deb_based(self) -> bool:
        return True

    @property
    def rhel_based(self) -> bool:
        return False


class RhelBasedDistro(Distro):
    @property
    def deb_based(self) -> bool:
        return False

    @property
    def rhel_based(self) -> bool:
        return True


class StoredVersionMixin:
    _version: str

    def __init__(self, version: str):
        super().__init__()
        self._version = version

    @property
    def version(self) -> str:
        return self._version


class Debian(StoredVersionMixin, DebBasedDistro):
    @property
    def name(self) -> str:
        return "Debian"


class Ubuntu(StoredVersionMixin, DebBasedDistro):
    @property
    def name(self) -> str:
        return "Ubuntu"


class AlmaLinux(StoredVersionMixin, RhelBasedDistro):
    @property
    def name(self) -> str:
        return "AlmaLinux"


class CentOs(StoredVersionMixin, RhelBasedDistro):
    @property
    def name(self) -> str:
        return "CentOS"


class CloudLinux(StoredVersionMixin, RhelBasedDistro):
    @property
    def name(self) -> str:
        return "CloudLinux"


_distro_mapping = {
    ("CentOS Linux", "7"): CentOs("7"),
    ("AlmaLinux", "8"): AlmaLinux("8"),
    ("CloudLinux", "7"): CloudLinux("7"),
    ("CloudLinux", "8"): CloudLinux("8"),
    ("Debian GNU/Linux", "10"): Debian("10"),
    ("Debian GNU/Linux", "11"): Debian("11"),
    ("Debian GNU/Linux", "12"): Debian("12"),
    ("Ubuntu", "18"): Ubuntu("18"),
    ("Ubuntu", "20"): Ubuntu("20"),
    ("Ubuntu", "22"): Ubuntu("22"),
}


def register_distro(name: str, version: str, distro: Distro) -> None:
    _distro_mapping[(name, version)] = distro


def unregister_distro(name: str, version: str) -> None:
    del _distro_mapping[(name, version)]


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


@lru_cache(maxsize=1)
def get_distro() -> Distro:
    if sys.version_info < (3, 8):
        distro = platform.linux_distribution()
    else:
        distro = _parse_os_relase()

    name = distro[0]
    major_version = distro[1].split(".")[0]

    return _distro_mapping.get((name, major_version), UnknownDistro(name, major_version))
