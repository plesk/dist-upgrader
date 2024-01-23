# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import json
import os
import subprocess
import typing

from pleskdistup.common import action, log, packages, version


class AssertMinPhpVersion(action.CheckAction):
    min_version: version.PHPVersion
    description: str
    fix_domains_step: str
    remove_php_step: str
    _name: str

    def __init__(
        self,
        min_version: str,
        name: str = "check for minimal PHP version {min_version}",
    ):
        self.min_version = version.PHPVersion(min_version)
        self.description = "Outdated PHP versions were detected: '{}'. To proceed with the conversion:"
        self.fix_domains_step = """Switch the following domains to {} or later:
\t- {}

\tYou can do so by running the following command:
\t> plesk bin domain -u [domain] -php_handler_id plesk-php80-fastcgi
"""
        self.remove_php_step = """Remove outdated PHP packages via Plesk Installer. You can do it by calling the following command:
\tplesk installer remove --components {}
"""
        self._name = name

    @property
    def name(self) -> str:
        return self._name.format(min_version=self.min_version)

    @name.setter
    def name(self, val: str) -> None:
        self._name = val

    def _do_check(self) -> bool:
        log.debug(f"Checking for minimal PHP version of {self.min_version}")
        # TODO: get rid of the explicit version list
        known_php_versions = [
            version.PHPVersion(f"PHP {ver}") for ver in (
                "5.2", "5.3", "5.4", "5.5", "5.6",
                "7.0", "7.1", "7.2", "7.3", "7.4",
                "8.0", "8.1", "8.2", "8.3",
            )
        ]
        log.debug(f"Known PHP versions: {known_php_versions}")
        outdated_php_versions = [php for php in known_php_versions if php < self.min_version]
        outdated_php_packages = {f"plesk-php{php.major}{php.minor}": str(php) for php in outdated_php_versions}
        log.debug(f"Outdated PHP versions: {outdated_php_versions}")

        installed_pkgs = packages.filter_installed_packages(outdated_php_packages.keys())
        log.debug(f"Outdated PHP packages installed: {installed_pkgs}")
        if len(installed_pkgs) == 0:
            log.debug("No outdated PHP versions installed")
            return True

        php_hanlers = {"'{}-fastcgi'", "'{}-fpm'", "'{}-fpm-dedicated'"}
        outdated_php_handlers = []
        for installed in installed_pkgs:
            outdated_php_handlers += [handler.format(installed) for handler in php_hanlers]
        log.debug(f"Outdated PHP handlers: {outdated_php_handlers}")

        try:
            looking_for_domains_sql_request = """
                SELECT d.name FROM domains d JOIN hosting h ON d.id = h.dom_id WHERE h.php_handler_id in ({});
            """.format(", ".join(outdated_php_handlers))
            outdated_php_domains = subprocess.check_output(["/usr/sbin/plesk", "db", looking_for_domains_sql_request],
                                                           universal_newlines=True)
            outdated_php_domains_lst = [
                domain[2:-2] for domain in outdated_php_domains.splitlines()
                if domain.startswith("|") and not domain.startswith("| name ")
            ]
            log.debug(f"Outdated PHP domains: {outdated_php_domains_lst}")
            outdated_php_domains = "\n\t- ".join(outdated_php_domains_lst)
        except Exception:
            outdated_php_domains = "Unable to get domains list. Please check it manually."

        self.description = self.description.format(", ".join([outdated_php_packages[installed] for installed in installed_pkgs]))
        if outdated_php_domains:
            self.description += "\n\t1. " + self.fix_domains_step.format(self.min_version, outdated_php_domains) + "\n\t2. "
        else:
            self.description += "\n\t"

        self.description += self.remove_php_step.format(" ".join(outdated_php_packages[installed].replace(" ", "") for installed in installed_pkgs).lower())

        log.debug("Outdated PHP versions found")
        return False


class AssertNotInContainer(action.CheckAction):
    def __init__(self):
        self.name = "check if the system not in a container"
        self.description = "The system is running in a container-like environment ({}). The conversion is not supported for such systems."

    def _is_docker(self) -> bool:
        return os.path.exists("/.dockerenv")

    def _is_podman(self) -> bool:
        return os.path.exists("/run/.containerenv")

    def _is_vz_like(self) -> bool:
        return os.path.exists("/proc/vz")

    def _do_check(self) -> bool:
        log.debug("Checking if running in a container")
        if self._is_docker():
            self.description = self.description.format("Docker container")
            log.debug("Running in Docker container")
            return False
        elif self._is_podman():
            self.description = self.description.format("Podman container")
            log.debug("Running in Podman container")
            return False
        elif self._is_vz_like():
            self.description = self.description.format("Virtuozzo container")
            log.debug("Running in Virtuozzo container")
            return False

        return True


class AssertPleskWatchdogNotInstalled(action.CheckAction):
    def __init__(self):
        self.name = "check if Plesk watchdog extension is not installed"
        self.description = """The Plesk Watchdog extension is installed. Unfortunately the extension is unsupported on Ubuntu 20 and later.
\tPlease remove the extension be calling: plesk installer remove --components watchdog
"""

    def _do_check(self) -> bool:
        return not packages.is_package_installed("psa-watchdog")


class AssertDpkgNotLocked(action.CheckAction):
    def __init__(self):
        self.name = "check if dpkg is not locked"
        self.description = """It looks like some other process is using dpkg. Please wait until it finishes and try again."""

    def _do_check(self) -> bool:
        return subprocess.run(["/bin/fuser", "/var/lib/apt/lists/lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0


class MinFreeDiskSpaceViolation(typing.NamedTuple):
    """Information about a filesystem with insufficient free disk space."""
    dev: str
    """Device name."""
    req_bytes: int
    """Required space on the device (in bytes)."""
    avail_bytes: int
    """Available space on the device (in bytes)."""
    paths: typing.Set[str]
    """Paths belonging to this device."""


class AssertMinFreeDiskSpace(action.CheckAction):
    """Check if there's enough free disk space.

    Args:
        requirements: A dictionary mapping paths to minimum free disk
            space (in bytes) on the devices containing them.
        name: Name of the check.
        description: Description to show if the assertion is violated. If ends
            with a colon, list of violations will be added automatically.
    """
    violations: typing.List[MinFreeDiskSpaceViolation]
    """List of filesystems with insiffucient free disk space."""
    _description: str

    def __init__(
        self,
        requirements: typing.Dict[str, int],
        name: str = "check if there's enough free disk space",
        description: str = "There's not enough free disk space:",
    ):
        self.requirements = requirements
        self.name = name
        self._description = description
        self.violations = []

    @property
    def description(self) -> str:
        """Description of violations or empty string.

        Can be set to change the message template.
        """
        if not self.violations:
            return ""
        res = self._description
        if res.endswith(":"):
            res += " " + ", ".join(
                f"on filesystem {v.dev!r} for "
                f"{', '.join(repr(p) for p in sorted(v.paths))} "
                f"(need {v.req_bytes / 1024**2} MiB, "
                f"got {v.avail_bytes / 1024**2} MiB)" for v in self.violations
            )
        return res

    @description.setter
    def description(self, val: str) -> None:
        self._description = val

    def _do_check(self) -> bool:
        """Perform the check."""
        log.debug("Checking minimum free disk space")
        cmd = [
            "findmnt", "--output", "source,target,avail",
            "--bytes", "--json", "-T",
        ]
        self.violations = []
        filesystems: typing.Dict[str, dict] = {}
        for path, req in self.requirements.items():
            log.debug(f"Checking {path!r} minimum free disk space requirement of {req}")
            proc = subprocess.run(
                cmd + [path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                universal_newlines=True,
            )
            log.debug(
                f"Command {cmd + [path]} returned {proc.returncode}, "
                f"stdout: '{proc.stdout}', stderr: '{proc.stderr}'"
            )
            fs_data = json.loads(proc.stdout)["filesystems"][0]
            fs_data["req"] = 0
            fs_data["paths"] = []
            if fs_data["source"] not in filesystems:
                log.debug(f"Discovered new filesystem {fs_data}")
                filesystems[fs_data["source"]] = fs_data
            log.debug(
                f"Adding space requirement of {req} to "
                f"{filesystems[fs_data['source']]}"
            )
            filesystems[fs_data["source"]]["req"] += req
            filesystems[fs_data["source"]]["paths"].append(path)
        for dev, fs_data in filesystems.items():
            if fs_data["req"] > fs_data["avail"]:
                self.violations.append(
                    MinFreeDiskSpaceViolation(
                        dev,
                        fs_data["req"],
                        fs_data["avail"],
                        set(fs_data["paths"]),
                    )
                )
        return len(self.violations) == 0
