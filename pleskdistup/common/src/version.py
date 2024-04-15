# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import typing

class KernelVersion():
    """Linux kernel version representation class."""

    major: str
    minor: str
    patch: str
    build: str
    distro: str
    arch: str

    def _extract_with_build(self, version: str) -> None:
        main_part, secondary_part = version.split("-")

        self.major, self.minor, self.patch = main_part.split(".")

        # Sometimes packages split patch and build with "_", which looks
        # really weird.
        if "_" in self.patch:
            self.patch, self.build = self.patch.split("_")
            self.distro, self.arch = secondary_part.split(".")
            return

        # Short format of kernel version without distro and arch mentioned
        if secondary_part.isnumeric():
            self.build = secondary_part
            self.distro = ""
            self.arch = ""
            return

        # Long format of kernel version
        for iter in range(len(secondary_part)):
            if secondary_part[iter].isalpha():
                self.build = secondary_part[:iter - 1]
                suffix = secondary_part[iter:]
                # There is no information about arch when we have vzX suffix
                if suffix.startswith("vz"):
                    self.distro = suffix.split(".")[0]
                else:
                    self.distro, self.arch = suffix.rsplit(".", 1)
                break

    def _extract_no_build(self, version: str) -> None:
        self.build = ""
        self.major, self.minor, self.patch, self.distro, self.arch = version.split(".")

    def _remove_prefix(self, version: str) -> str:
        while not version[0].isdigit():
            version = version.split("-", 1)[-1]
        return version

    def __init__(self, version: str):
        """Initialize a KernelVersion object."""
        self.major = "0"
        self.minor = "0"
        self.patch = "0"
        self.build = "0"
        self.distro = ""
        self.arch = ""

        version = self._remove_prefix(version)
        if "-" in version:
            self._extract_with_build(version)
        else:
            self._extract_no_build(version)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.build != "":
            result += f"-{self.build}"
        if self.distro != "":
            result += f".{self.distro}"
        if self.arch != "":
            result += f".{self.arch}"

        return result

    def __lt__(self, other) -> bool:
        if int(self.major) < int(other.major) or int(self.minor) < int(other.minor) or int(self.patch < other.patch):
            return True

        for build_part_left, build_part_right in zip(self.build.split("."), other.build.split(".")):
            if int(build_part_left) < int(build_part_right):
                return True
            elif int(build_part_left) > int(build_part_right):
                return False

        return len(self.build) < len(other.build)

    def __eq__(self, other) -> bool:
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch and self.build == other.build

    def __ge__(self, other) -> bool:
        return not self.__lt__(other)


class PHPVersion():
    """Php version representation class."""

    major: int
    minor: int

    def _extract_from_version(self, version: str) -> None:
        # Version string example is "7.2" or "7.2.24"
        major_part, minor_part = version.split(".")[:2]
        self.major = int(major_part)
        self.minor = int(minor_part)

    def _extract_from_desc(self, description: str) -> None:
        # Description string example is "PHP 5.2"
        major_part, minor_part = description.split(" ")[1].split(".")
        self.major = int(major_part)
        self.minor = int(minor_part)

    def _extract_from_plesk_package(self, packagename: str) -> None:
        # Related package name example is plesk-php52
        version_part = packagename.split("php")[1]
        self.major = int(version_part[0])
        self.minor = int(version_part[1])

    def __init__(self, to_extract: str):
        """Initialize a KernelVersion object."""
        self.major = 0
        self.minor = 0

        if to_extract.startswith("plesk-php"):
            self._extract_from_plesk_package(to_extract)
        elif to_extract.startswith("PHP "):
            self._extract_from_desc(to_extract)
        elif to_extract[0].isdigit():
            self._extract_from_version(to_extract)
        else:
            raise ValueError(f"Cannot extract php version from '{to_extract}'")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(major={self.major!r}, minor={self.minor!r})"

    def __str__(self) -> str:
        return f"PHP {self.major}.{self.minor}"

    def __lt__(self, other) -> bool:
        return self.major < other.major or (self.major == other.major and self.minor < other.minor)

    def __eq__(self, other) -> bool:
        return self.major == other.major and self.minor == other.minor

    def __ge__(self, other) -> bool:
        return not self.__lt__(other)


class PleskVersion:
    """
    Plesk version representation class.

    Plesk version is represented as a string in format "major.minor.patch.hotfix".
    Examples:
    - "18.0.50"
    - "18.0.51.2"

    Versions could be compared with each other, represented as a string.
    Available fields are: major, minor, patch and hotfix.
    """

    major: int
    minor: int
    patch: int
    hotfix: int

    def _extract_from_version(self, version: str) -> None:
        split_version = version.split(".")
        if len(split_version) not in (3, 4):
            raise ValueError("Incorrect version length")

        # Version string example is "18.0.50" or "18.0.50.2"
        self.major, self.minor, self.patch = map(int, split_version[:3])
        if len(split_version) > 3:
            self.hotfix = int(split_version[3])
        else:
            self.hotfix = 0

        if self.major < 0 or self.minor < 0 or self.patch < 0 or self.hotfix < 0:
            raise ValueError("Negative number in version")

    def __init__(self, version: str):
        """Initialize a PleskVersion object."""
        self.major = 0
        self.minor = 0
        self.patch = 0
        self.hotfix = 0

        self._extract_from_version(version)

    def _to_tuple(self) -> typing.Tuple[int, int, int, int]:
        return (self.major, self.minor, self.patch, self.hotfix)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(major={self.major!r}, minor={self.minor!r}, patch={self.patch!r}, hotfix={self.hotfix!r})"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}.{self.hotfix}"

    def __lt__(self, other) -> bool:
        return self._to_tuple() < other._to_tuple()

    def __eq__(self, other) -> bool:
        return self._to_tuple() == other._to_tuple()

    def __ge__(self, other) -> bool:
        return not self.__lt__(other)
