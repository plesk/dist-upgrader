# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import itertools
import os
import re
import subprocess
import typing

from . import files, util

APT_CHOOSE_OLD_FILES_OPTIONS = [
    "-o", "Dpkg::Options::=--force-confdef",
    "-o", "Dpkg::Options::=--force-confold"
]


def is_package_installed(pkg: str) -> bool:
    res = subprocess.run(
        ["/usr/bin/dpkg-query", "--showformat", "${db:Status-status}", "--show", pkg],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
    )
    return res.returncode == 0 and res.stdout == "installed"


class PackageEntry(typing.NamedTuple):
    name: str
    arch: str
    epoch_version_release: str


def _parse_apt_get_simulation(data: str) -> typing.Dict[str, typing.List[PackageEntry]]:
    re_inst = re.compile(r"^(?P<op>Inst|Conf) (?P<name>[^ :]+)(:(?P<arch>[^ ]+))?( \[[^ ]+\])? \((?P<evr>[^ ]+) .+")
    re_remv = re.compile(r"^(?P<op>Remv|Purg) (?P<name>[^ :]+)(:(?P<arch>[^ ]+))? \[(?P<evr>[^ ]+)\]$")
    res: typing.Dict[str, typing.List[PackageEntry]] = {}
    for line in data.split("\n"):
        m = re.match(re_inst, line)
        if not m:
            m = re.match(re_remv, line)
        if m:
            if m["op"] not in res:
                res[m["op"]] = []
            res[m["op"]].append(PackageEntry(m["name"], m["arch"], m["evr"]))
    return res


def install_packages(
    pkgs: typing.List[str],
    repository: typing.Optional[str] = None,
    force_package_config: bool = True,
    simulate: bool = False,
) -> typing.Optional[typing.Dict[str, typing.List[PackageEntry]]]:
    if len(pkgs) == 0:
        return None

    # repository specification is not supported now
    cmd = ["/usr/bin/apt-get", "install", "-y"]
    if force_package_config is True:
        cmd += APT_CHOOSE_OLD_FILES_OPTIONS
    if simulate:
        cmd.append("--simulate")
    cmd += pkgs

    cmd_out = util.logged_check_call(cmd, env={"PATH": os.environ["PATH"], "DEBIAN_FRONTEND": "noninteractive"})
    if simulate:
        return _parse_apt_get_simulation(cmd_out)
    return None


class PackageProtectionError(Exception):
    message: str
    protected_packages: typing.Optional[typing.Sequence[str]]

    def __init__(
        self,
        message: str = "Refusing to remove protected packages",
        protected_packages: typing.Optional[typing.Iterable[str]] = None,
    ):
        super().__init__()
        self.message = message
        self.protected_packages = list(protected_packages) if protected_packages is not None else []

    def __str__(self) -> str:
        msg = self.message
        if self.protected_packages:
            msg += f": {', '.join(self.protected_packages)}"
        return msg

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, protected_packages={self.protected_packages!r})"


def _find_protection_violations(
    sim_res: typing.Dict[str, typing.List[PackageEntry]],
    protected_pkgs: typing.Set[str],
) -> typing.Optional[typing.Set[str]]:
    if protected_pkgs and ("Remv" in sim_res or "Purg" in sim_res):
        removed_set = set(
            entry.name for entry in itertools.chain(
                sim_res.get("Remv", []),
                sim_res.get("Purg", []),
            )
        )
        violations = protected_pkgs & removed_set
        return violations
    return None


def safely_install_packages(
    pkgs: typing.List[str],
    repository: typing.Optional[str] = None,
    force_package_config: bool = True,
    protected_pkgs: typing.Optional[typing.Iterable[str]] = None,
) -> None:
    sim_res = install_packages(pkgs, repository, force_package_config, simulate=True)
    if sim_res is not None and protected_pkgs is not None:
        protected_set = set(protected_pkgs)
        violations = _find_protection_violations(sim_res, protected_set)
        if violations:
            raise PackageProtectionError(protected_packages=violations)
    install_packages(pkgs, repository, force_package_config)


def remove_packages(
    pkgs: typing.List[str],
    simulate: bool = False,
) -> typing.Optional[typing.Dict[str, typing.List[PackageEntry]]]:
    if len(pkgs) == 0:
        return None

    cmd = ["/usr/bin/apt-get", "remove", "-y"]
    if simulate:
        cmd.append("--simulate")
    cmd += pkgs
    cmd_out = util.logged_check_call(cmd)
    if simulate:
        return _parse_apt_get_simulation(cmd_out)
    return None


def safely_remove_packages(
    pkgs: typing.List[str],
    protected_pkgs: typing.Optional[typing.Iterable[str]] = None,
) -> None:
    sim_res = remove_packages(pkgs, simulate=True)
    if sim_res is not None and protected_pkgs is not None:
        protected_set = set(protected_pkgs)
        violations = _find_protection_violations(sim_res, protected_set)
        if violations:
            raise PackageProtectionError(protected_packages=violations)
    remove_packages(pkgs)


def find_related_repofiles(repository_file: str) -> typing.List[str]:
    return files.find_files_case_insensitive("/etc/apt/sources.list.d", repository_file)


def update_package_list() -> None:
    util.logged_check_call(["/usr/bin/apt-get", "update", "-y"])


def upgrade_packages(pkgs: typing.Optional[typing.List[str]] = None) -> None:
    if pkgs is None:
        pkgs = []

    cmd = ["/usr/bin/apt-get", "upgrade", "-y"] + APT_CHOOSE_OLD_FILES_OPTIONS + pkgs
    util.logged_check_call(cmd, env={"PATH": os.environ["PATH"], "DEBIAN_FRONTEND": "noninteractive"})


def autoremove_outdated_packages() -> None:
    util.logged_check_call(["/usr/bin/apt-get", "autoremove", "-y"],
                           env={"PATH": os.environ["PATH"], "DEBIAN_FRONTEND": "noninteractive"})


def depconfig_parameter_set(parameter: str, value: str) -> None:
    subprocess.run(["/usr/bin/debconf-communicate"], input=f"SET {parameter} {value}\n",
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, universal_newlines=True)


def depconfig_parameter_get(parameter: str) -> str:
    process = subprocess.run(["/usr/bin/debconf-communicate"], input=f"GET {parameter}\n",
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, universal_newlines=True)
    return process.stdout.split(" ")[1].strip()


def restore_installation() -> None:
    util.logged_check_call(["/usr/bin/apt-get", "-f", "install", "-y"])


def do_distupgrade() -> None:
    util.logged_check_call(["apt-get", "dist-upgrade", "-y"] + APT_CHOOSE_OLD_FILES_OPTIONS,
                           env={"PATH": os.environ["PATH"], "DEBIAN_FRONTEND": "noninteractive"})


def get_installed_packages_list(regex: str) -> typing.List[typing.Tuple[str, str]]:
    pkgs_info = subprocess.check_output(["/usr/bin/dpkg-query", "-W", "-f", "${binary:Package} ${Version}\n", regex],
                                        universal_newlines=True)
    result = []
    for pkg in pkgs_info.splitlines():
        name, version = pkg.split(" ", 1)
        result.append((name, version))
    return result
