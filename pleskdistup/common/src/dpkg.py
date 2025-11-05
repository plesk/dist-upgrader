# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import itertools
import os
import re
import shutil
import subprocess
import typing
import time

from . import files, log, util

DPKG_TEMPFAIL_RETRY: typing.List[int] = [30, 60, 90, 120]

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


def _exec_retry_when_locked(
    apt_get_cmd: typing.List[str],
    tmpfail_retry_intervals: typing.Optional[typing.List[int]] = None,
    collect_stdout: bool = False,
) -> str:
    cant_get_lock = False
    stdout = []

    if tmpfail_retry_intervals is None:
        tmpfail_retry_intervals = DPKG_TEMPFAIL_RETRY

    def process_stdout(line: str) -> None:
        if collect_stdout:
            nonlocal stdout  # noqa: F824
            stdout.append(line)
        log.info("stdout: {}".format(line.rstrip('\n')), to_stream=False)

    def process_stderr(line: str) -> None:
        log.info("stderr: {}".format(line.rstrip('\n')))
        nonlocal cant_get_lock
        if cant_get_lock:
            return
        if "E: Could not get lock" in line:
            cant_get_lock = True

    i = 0
    while True:
        cant_get_lock = False
        stdout.clear()
        log.info(f"Executing: {' '.join(apt_get_cmd)}")
        exit_code = util.exec_get_output_streamed(
            apt_get_cmd, process_stdout, process_stderr,
            env={
                "PATH": os.environ["PATH"],
                "DEBIAN_FRONTEND": "noninteractive",
                "LC_ALL": "C",
                "LANG": "C",
            },
        )
        if exit_code == 0:
            break
        if i >= len(tmpfail_retry_intervals) or not cant_get_lock:
            raise subprocess.CalledProcessError(returncode=exit_code, cmd=apt_get_cmd)
        log.info(f"{apt_get_cmd[0]} failed because lock is already held, will retry in {tmpfail_retry_intervals[i]} seconds..")
        time.sleep(tmpfail_retry_intervals[i])
        i += 1
    return "".join(stdout)


def remove_packages(
    pkgs: typing.List[str],
    simulate: bool = False,
    tmpfail_retry_intervals: typing.Optional[typing.List[int]] = None,
) -> typing.Optional[typing.Dict[str, typing.List[PackageEntry]]]:
    if len(pkgs) == 0:
        return None

    cmd = ["/usr/bin/apt-get", "remove", "-y"]
    if simulate:
        cmd.append("--simulate")
    cmd += pkgs
    cmd_out = _exec_retry_when_locked(cmd, tmpfail_retry_intervals, collect_stdout=True)
    if simulate:
        return _parse_apt_get_simulation(cmd_out)
    return None


def safely_remove_packages(
    pkgs: typing.List[str],
    protected_pkgs: typing.Optional[typing.Iterable[str]] = None,
    tmpfail_retry_intervals: typing.Optional[typing.List[int]] = None,
) -> None:
    sim_res = remove_packages(pkgs, simulate=True)
    if sim_res is not None and protected_pkgs is not None:
        protected_set = set(protected_pkgs)
        violations = _find_protection_violations(sim_res, protected_set)
        if violations:
            raise PackageProtectionError(protected_packages=violations)
    remove_packages(pkgs, False, tmpfail_retry_intervals)


def find_related_repofiles(repository_file: str) -> typing.List[str]:
    return files.find_files_case_insensitive("/etc/apt/sources.list.d", repository_file)


def find_all_repofiles(sources_dir: str = "/etc/apt/sources.list.d") -> typing.List[str]:
    return files.find_files_case_insensitive(sources_dir, "*.list")


def update_package_list(tmpfail_retry_intervals: typing.Optional[typing.List[int]] = None) -> None:
    cmd = ["/usr/bin/apt-get", "update", "-y"]
    _exec_retry_when_locked(cmd, tmpfail_retry_intervals)


def upgrade_packages(
    pkgs: typing.Optional[typing.List[str]] = None,
    tmpfail_retry_intervals: typing.Optional[typing.List[int]] = None,
    allow_downgrade: bool = False,
) -> None:
    if pkgs is None:
        pkgs = []

    cmd = ["/usr/bin/apt-get", "upgrade", "-y"] + APT_CHOOSE_OLD_FILES_OPTIONS
    if allow_downgrade:
        cmd += ["--allow-downgrades"]
    cmd += pkgs

    _exec_retry_when_locked(cmd, tmpfail_retry_intervals)


def autoremove_outdated_packages(tmpfail_retry_intervals: typing.Optional[typing.List[int]] = None) -> None:
    cmd = ["/usr/bin/apt-get", "autoremove", "-y"]
    _exec_retry_when_locked(cmd, tmpfail_retry_intervals)


def depconfig_parameter_set(parameter: str, value: str) -> None:
    subprocess.run(["/usr/bin/debconf-communicate"], input=f"SET {parameter} {value}\n",
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, universal_newlines=True)


def depconfig_parameter_get(parameter: str) -> str:
    process = subprocess.run(["/usr/bin/debconf-communicate"], input=f"GET {parameter}\n",
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, universal_newlines=True)
    return process.stdout.split(" ")[1].strip()


def restore_installation(tmpfail_retry_intervals: typing.Optional[typing.List[int]] = None) -> None:
    cmd = ["/usr/bin/apt-get", "-f", "install", "-y"]
    _exec_retry_when_locked(cmd, tmpfail_retry_intervals)


def do_distupgrade(tmpfail_retry_intervals: typing.Optional[typing.List[int]] = None) -> None:
    cmd = ["apt-get", "dist-upgrade", "-y"] + APT_CHOOSE_OLD_FILES_OPTIONS
    _exec_retry_when_locked(cmd, tmpfail_retry_intervals)


def get_installed_packages_list(regex: str) -> typing.List[typing.Tuple[str, str]]:
    pkgs_info = subprocess.check_output(["/usr/bin/dpkg-query", "-W", "-f", "${binary:Package} ${Version}\n", regex],
                                        universal_newlines=True)
    result = []
    for pkg in pkgs_info.splitlines():
        name, version = pkg.split(" ", 1)
        result.append((name, version))
    return result


def handle_dpkg_dist(original_path: str) -> bool:
    if not os.path.exists(original_path + ".dpkg-dist"):
        return False

    if os.path.exists(original_path):
        log.debug("The '{path}' file has a '.dpkg-dist' analogue file. Going to replace the file with this new file. "
                  "The file itself will be saved as .dpkg-old".format(path=original_path))
        shutil.move(original_path, original_path + ".dpkg-old")
    else:
        log.debug("The '{path}' file is missing, but has '.dpkg-dist' analogue file. Going to use it".format(path=original_path))

    shutil.move(original_path + ".dpkg-dist", original_path)

    return True


def get_repositories_urls(repofile: str) -> typing.Set[str]:
    """
    Get the set of URLs from the repository file.
    :param repofile: path to the repository file
    :return: set of URLs
    """
    if not os.path.exists(repofile):
        return set()

    urls = set()
    with open(repofile, "r") as f:
        for line in f:
            line = line.strip().rstrip()

            if not line.startswith("deb ") and not line.startswith("deb-src "):
                continue

            # We ignore '[arch=...]' and '[trusted=yes]' parts for now for simplicity
            # if there will be any issues with that, we should fix it.
            match = re.search(r"https?://[^\s]+", line)
            if not match:
                continue

            url = match.group(0)

            dist_name = line.split(url)[1].strip().split(" ")[0]

            url = url.rstrip("/") + "/dists/" + dist_name
            urls.add(url)

    return urls


def get_repository_metafile_url(repository_url: str) -> str:
    """
    Get the URL of the repository metafile.
    :param repository_url: URL of the repository
    :return: URL of the repository metafile
    """
    return repository_url.rstrip("/") + "/Release"


def is_package_available(package_name: str) -> bool:
    """
    Check if the package is available in enabled repositories.
    :param package_name: name of the package to check
    :return: True if the package is available, False otherwise
    """
    cmd = ["/usr/bin/apt-cache", "show", package_name]
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    if res.returncode != 0:
        log.debug(f"apt-cache show {package_name} failed with stdout: {res.stdout}, stderr: {res.stderr}")

    return res.returncode == 0


def prohibit_package_from_repository(package: str, repository: str) -> None:
    """
    Prohibit the package from being installed from the given repository.
    :param package: package name
    :param repository: repository URL or its part
    """
    pin_file = "/etc/apt/preferences.d/prohibit-{}-from-{}.pref".format(package, re.sub(r'[^a-zA-Z0-9]', '_', repository))
    with open(pin_file, "w") as f:
        f.write("Package: {}\n".format(package))
        f.write("Pin: origin {}\n".format(repository))
        f.write("Pin-Priority: -1\n")


def allow_package_from_repository(package: str, repository: str) -> None:
    """
    Allow the package to be installed from the given repository.
    :param package: package name
    :param repository: repository URL or its part
    """
    pin_file = "/etc/apt/preferences.d/prohibit-{}-from-{}.pref".format(package, re.sub(r'[^a-zA-Z0-9]', '_', repository))
    if os.path.exists(pin_file):
        os.remove(pin_file)


def is_repository_url_enabled(repository_url: str, sources_dir: str = "/etc/apt/sources.list.d/") -> bool:
    """
    Check if the repository is enabled.
    :param repository_url: URL of the repository
    :return: True if the repository is enabled, False otherwise
    """
    for repofile in find_all_repofiles(sources_dir=sources_dir):
        with open(repofile, "r") as f:
            for line in f:
                line = line.strip().rstrip()
                if (line.startswith("deb ") or line.startswith("deb-src ")) and repository_url in line:
                    return True
    return False


def get_package_installed_version(package_name: str) -> typing.Optional[str]:
    """
    Get the installed version of the package.
    :param package_name: name of the package
    :return: installed version or None if the package is not installed
    """
    res = subprocess.run(
        ["/usr/bin/dpkg-query", "--showformat", "${Version}", "--show", package_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
    )
    if res.returncode != 0:
        return None
    return res.stdout if res.stdout else None
