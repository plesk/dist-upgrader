# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import os
import subprocess
import typing
import zipfile

from . import dist, log, plesk


class Feedback():
    VERSIONS_FILE_PATH = "versions.txt"
    util_name: typing.Optional[str]
    util_version: typing.Optional[str]
    upgrader_name: typing.Optional[str]
    upgrader_version: typing.Optional[str]
    attached_files: typing.List[str]
    collect_actions: typing.List[typing.Callable[[], typing.Iterable[str]]]
    _created_files: typing.List[str]
    _prepared: bool

    def __init__(
        self,
        util_name: typing.Optional[str] = None,
        util_version: typing.Optional[str] = None,
        upgrader_name: typing.Optional[str] = None,
        upgrader_version: typing.Optional[str] = None,
        attached_files: typing.Optional[typing.Iterable[str]] = None,
        collect_actions: typing.Optional[typing.Iterable[typing.Callable[[], typing.Iterable[str]]]] = None,
    ) -> None:
        self.util_name = util_name
        self.util_version = util_version
        self.upgrader_name = upgrader_name
        self.upgrader_version = upgrader_version
        self.attached_files = list(attached_files) if attached_files is not None else []
        self.collect_actions = list(collect_actions) if collect_actions is not None else []
        self._created_files = []
        self._prepared = False

    def __del__(self) -> None:
        for f in self._created_files:
            if os.path.exists(f):
                os.unlink(f)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

    @property
    def prepared(self) -> bool:
        return self._prepared

    def _prepare_versions_file(self, versions_file_path: str) -> None:
        for att in ("util_name", "util_version", "upgrader_name", "upgrader_version"):
            if getattr(self, att) is None:
                raise ValueError(f"Feedback attribute {att!r} is not set")
        with open(versions_file_path, "w") as versions:
            try:
                versions.write(f"The {self.util_name!r} utility version: {self.util_version}\n")
                versions.write(f"Upgrader {self.upgrader_name!r} version: {self.upgrader_version}\n")
                versions.write(f"Distribution information: {dist.get_distro()}\n")

                try:
                    uname_path = "/usr/bin/uname"
                    if not os.path.exists(uname_path):
                        uname_path = "/bin/uname"

                    kernel_info = subprocess.check_output([uname_path, "-a"], universal_newlines=True).splitlines()[0]
                except FileNotFoundError:
                    kernel_info = "not available. likely we are in a container"

                versions.write(f"Kernel information: {kernel_info}\n")
            except subprocess.CalledProcessError:
                versions.write("Plesk version is not available\n")

    def prepare(self) -> None:
        self._prepare_versions_file(self.VERSIONS_FILE_PATH)
        self._created_files = [self.VERSIONS_FILE_PATH]
        for action in self.collect_actions:
            self._created_files += action()
        self._prepared = True

    def save_archive(self, archive_path: str) -> None:
        if not self.prepared:
            raise RuntimeError("Feedback hasn't been prepared yet, call prepare() first")
        with zipfile.ZipFile(archive_path, "w") as zip_file:
            files_to_store = self.attached_files + self._created_files
            for f in files_to_store:
                if os.path.exists(f):
                    zip_file.write(f)


def _collect_command_output(
    args: typing.Sequence[str],
    file_path: str,
    error_message_fmt: typing.Optional[str] = None,
) -> None:
    with open(file_path, "w") as outf:
        try:
            out = subprocess.check_output(args, stderr=subprocess.STDOUT, universal_newlines=True).splitlines()
            for line in out:
                outf.write(line + "\n")
        except Exception as ex:
            if error_message_fmt:
                msg = error_message_fmt.format(args=args, file_path=file_path, ex=ex)
            else:
                msg = f"Unable to get output from the command {args}: {ex}"
            outf.write(msg)


def collect_installed_packages_apt(out_file_path: str = "installed_packages_apt.txt") -> typing.List[str]:
    _collect_command_output(
        ["/usr/bin/apt", "list", "--installed"],
        out_file_path,
        "Getting installed packages from APT (called as {args}) failed: {ex}\n",
    )
    return [out_file_path]


def collect_apt_policy(out_file_path: str = "apt_policy.txt") -> typing.List[str]:
    _collect_command_output(
        ["/usr/bin/apt", "policy"],
        out_file_path,
        "Getting policy from APT (called as {args}) failed: {ex}\n",
    )
    return [out_file_path]


def collect_installed_packages_dpkg(out_file_path: str = "installed_packages_dpkg.txt") -> typing.List[str]:
    _collect_command_output(
        ["/usr/bin/dpkg", "--list"],
        out_file_path,
        "Getting installed packages from dpkg (called as {args}) failed: {ex}\n",
    )
    return [out_file_path]


def collect_installed_packages_yum(out_file_path: str = "installed_packages_yum.txt") -> typing.List[str]:
    _collect_command_output(
        ["/usr/bin/yum", "list", "installed"],
        out_file_path,
        "Getting installed packages from yum (called as {args}) failed: {ex}\n",
    )
    return [out_file_path]


def collect_plesk_version(out_file_path: str = "plesk_version.txt") -> typing.List[str]:
    with open(out_file_path, "w") as version_file:
        for lines in plesk.get_plesk_full_version():
            version_file.write(lines + "\n")

    return [out_file_path]


def collect_kernel_modules(out_file_path: str = "kernel_modules.txt") -> typing.List[str]:
    possible_lsmod_paths: typing.List[str] = ["/usr/sbin/lsmod", "/sbin/lsmod"]
    lsmod_utility: typing.Optional[str] = None
    for lsmod_path in possible_lsmod_paths:
        if os.path.exists(lsmod_path):
            lsmod_utility = lsmod_path
            break

    if lsmod_utility is None:
        log.warn("lsmod utility not found, skipping kernel modules collection")
        return []

    _collect_command_output(
        [lsmod_utility],
        out_file_path,
        "Getting kernel modules (called as {args}) failed: {ex}\n",
    )
    return [out_file_path]
