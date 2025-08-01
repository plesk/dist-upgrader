# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import configparser
import json
import os
import subprocess
import typing
import urllib.request
from abc import abstractmethod

from pleskdistup.common import action, log, packages, php, plesk, version


# This action should be considered as deprecated
# It was split into AssertMinPhpVersionInstalled and AssertMinPhpVersionUsedByWebsites
# because there still can be domains connected with outdated php version even when we
# remove this version from the system. So we should check it separately.
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


class AssertInstalledPhpVersionsByCondition(action.CheckAction):
    condition: typing.Callable[[version.PHPVersion], bool]
    formatter: typing.Callable[[typing.List[version.PHPVersion]], str]

    def __init__(
        self,
        name: str,
        description: str,
        formatter: typing.Callable[[typing.List[version.PHPVersion]], str],
        condition: typing.Callable[[version.PHPVersion], bool],
    ):
        self.name = name
        self.description = description
        self.formatter = formatter
        self.condition = condition

    def _do_check(self) -> bool:
        log.debug("Checking that all installed PHP versions satisfy the condition")

        installed_violating_php = php.get_php_versions_by_condition(
            lambda php: not self.condition(php) and packages.is_package_installed(f"plesk-php{php.major}{php.minor}")
        )

        if len(installed_violating_php) == 0:
            log.debug("No installed PHP versions violate the condition")
            return True

        self.description = self.formatter(installed_violating_php)

        return False


class AssertInstalledPhpVersionsInList(AssertInstalledPhpVersionsByCondition):
    def __init__(
        self,
        allowed_versions: typing.Set[str],
    ):
        _allowed_versions = {version.PHPVersion(ver) for ver in allowed_versions}
        super().__init__(
            name="check for not supported PHP versions",
            description="""Not supported PHP versions were detected: {versions}.
\tRemove unsupported PHP packages via Plesk Installer to proceed with the conversion:
\tYou can do it by calling the following command:
\tplesk installer remove --components {remove_arg}
""",
            formatter=lambda installed_unsupported_php: self._format_description(installed_unsupported_php),
            condition=lambda php: php in _allowed_versions,
        )

    def _format_description(self, installed_unsupported_php: typing.List[version.PHPVersion]) -> str:
        unsupported_php_descriptions = [str(php) for php in installed_unsupported_php]
        return self.description.format(
            versions=", ".join(unsupported_php_descriptions),
            remove_arg=" ".join([php_version.replace(" ", "") for php_version in unsupported_php_descriptions]).lower()
        )


class AssertMinPhpVersionInstalled(AssertInstalledPhpVersionsByCondition):
    def __init__(
        self,
        min_version: str,
    ):
        minimal_php_version = version.PHPVersion(min_version)
        super().__init__(
            name="check for outdated PHP versions",
            description="""Outdated PHP versions were detected: {versions}.
\tRemove outdated PHP packages via Plesk Installer to proceed with the conversion:
\tYou can do it by calling the following command:
\tplesk installer remove --components {remove_arg}
""",
            formatter=lambda installed_unsupported_php: self._format_description(installed_unsupported_php),
            condition=lambda php: php >= minimal_php_version,
        )

    def _format_description(self, installed_unsupported_php: typing.List[version.PHPVersion]) -> str:
        unsupported_php_descriptions = [str(php) for php in installed_unsupported_php]
        return self.description.format(
            versions=", ".join(unsupported_php_descriptions),
            remove_arg=" ".join([php_version.replace(" ", "") for php_version in unsupported_php_descriptions]).lower()
        )


class AssertPhpVersionsUsedByWebsitesByCondition(action.CheckAction):
    condition: typing.Callable[[version.PHPVersion], bool]
    formatter: typing.Callable[[typing.List[str]], str]
    optional: bool

    def __init__(
        self,
        name: str,
        description: str,
        formatter: typing.Callable[[typing.List[str]], str],
        condition: typing.Callable[[version.PHPVersion], bool],
        optional: bool = True,
    ):
        self.name = name
        self.description = description
        self.formatter = formatter
        self.condition = condition
        self.optional = optional

    def _do_check(self) -> bool:
        log.debug("Checking that all PHP versions being used by the websites satisfy the condition")
        if not plesk.is_plesk_database_ready():
            if self.optional:
                log.info("Plesk database is not ready. Skipping the minimum PHP for websites check.")
                return True
            raise RuntimeError("Plesk database is not ready. Skipping the minimum PHP for websites check.")

        violating_php_handlers = [f"'{handler}'" for handler in php.get_php_handlers_by_condition(lambda php: not self.condition(php))]
        log.debug(f"Violating PHP handlers: {violating_php_handlers}")
        try:
            looking_for_domains_sql_request = """
                SELECT d.name FROM domains d JOIN hosting h ON d.id = h.dom_id WHERE h.php_handler_id in ({});
            """.format(", ".join(violating_php_handlers))

            violating_php_domains = plesk.get_from_plesk_database(looking_for_domains_sql_request)
            if not violating_php_domains:
                return True

            log.debug(f"Violating PHP domains: {violating_php_domains}")
            self.description = self._format_description(violating_php_domains)
        except Exception as ex:
            log.err("Unable to get domains list from plesk database!")
            raise RuntimeError("Unable to get domains list from plesk database!") from ex

        return False

    @abstractmethod
    def _format_description(self, violating_php_domains: typing.List[str]) -> str:
        pass


class AssertPhpVersionsUsedByWebsitesInList(AssertPhpVersionsUsedByWebsitesByCondition):
    allowed_versions: typing.Set[version.PHPVersion]
    optional: bool

    def __init__(
        self,
        allowed_versions: typing.Set[str],
        optional: bool = True,
    ):
        self.allowed_versions = {version.PHPVersion(ver) for ver in allowed_versions}
        super().__init__(
            name="checking domains using not supported PHP",
            description="""We have identified that the domains are using not supported versions of PHP.
\tSupported PHP versions are: {versions}.
\tSwitch the following domains to one of the supported versions in order to continue with the conversion process:
\t- {domains}

\tYou can achieve this by executing the following command:
\t> plesk bin domain -u [domain] -php_handler_id plesk-php80-fastcgi
""",
            formatter=lambda installed_unsupported_php: self._format_description(installed_unsupported_php),
            condition=lambda php: php in self.allowed_versions,
            optional=optional,
        )

    def _format_description(self, violating_php_domains: typing.List[str]) -> str:
        return self.description.format(
            versions=sorted([str(php) for php in self.allowed_versions]),
            domains="\n\t- ".join(violating_php_domains),
        )


class AssertMinPhpVersionUsedByWebsites(AssertPhpVersionsUsedByWebsitesByCondition):
    min_version: version.PHPVersion

    def __init__(
        self,
        min_version: str,
        optional: bool = True,
    ):
        self.min_version = version.PHPVersion(min_version)
        super().__init__(
            name="checking domains using outdated PHP",
            description="""We have identified that the domains are using older versions of PHP.
\tSwitch the following domains to {modern} or later in order to continue with the conversion process:
\t- {domains}

\tYou can achieve this by executing the following command:
\t> plesk bin domain -u [domain] -php_handler_id plesk-php80-fastcgi
""",
            formatter=lambda installed_unsupported_php: self._format_description(installed_unsupported_php),
            condition=lambda php: php >= self.min_version,
            optional=optional,
        )

    def _format_description(self, violating_php_domains: typing.List[str]) -> str:
        return self.description.format(
            modern=str(self.min_version),
            domains="\n\t- ".join(violating_php_domains),
        )


class AssertPhpVersionsUsedByCronByCondition(action.CheckAction):
    condition: typing.Callable[[version.PHPVersion], bool]
    formatter: typing.Callable[[typing.List[str]], str]
    optional: bool

    def __init__(
        self,
        name: str,
        description: str,
        formatter: typing.Callable[[typing.List[str]], str],
        condition: typing.Callable[[version.PHPVersion], bool],
        optional: bool = True,
    ):
        self.name = name
        self.description = description
        self.formatter = formatter
        self.condition = condition
        self.optional = optional

    def _do_check(self) -> bool:
        log.debug("Checking that all PHP versions being used in cronjobs satisfy the condition")
        if not plesk.is_plesk_database_ready():
            if self.optional:
                log.info("Plesk database is not ready. Skipping the minimum PHP for cronjobs check.")
                return True
            raise RuntimeError("Plesk database is not ready. Skipping the minimum PHP for cronjobs check.")

        violating_php_handlers = [f"'{handler}'" for handler in php.get_php_handlers_by_condition(lambda php: not self.condition(php))]
        log.debug(f"violating PHP handlers: {violating_php_handlers}")

        try:
            looking_for_cronjobs_sql_request = """
                SELECT command from ScheduledTasks WHERE type = "php" and phpHandlerId in ({});
            """.format(", ".join(violating_php_handlers))

            violating_php_cronjobs = plesk.get_from_plesk_database(looking_for_cronjobs_sql_request)
            if not violating_php_cronjobs:
                return True

            log.debug(f"violating PHP cronjobs: {violating_php_cronjobs}")
            self.description = self._format_description(violating_php_cronjobs)
        except Exception as ex:
            log.err("Unable to get cronjobs list from plesk database!")
            raise RuntimeError("Unable to get cronjobs list from plesk database!") from ex

        return False

    @abstractmethod
    def _format_description(self, violating_php_cronjobs: typing.List[str]) -> str:
        pass


class AssertPhpVersionsUsedByCronInList(AssertPhpVersionsUsedByCronByCondition):
    allowed_versions: typing.Set[version.PHPVersion]
    optional: bool

    def __init__(
        self,
        allowed_versions: typing.Set[str],
        optional: bool = True,
    ):
        self.allowed_versions = {version.PHPVersion(ver) for ver in allowed_versions}
        super().__init__(
            name="checking cronjob using outdated PHP",
            description="""We have detected that some cronjobs are using not supported PHP versions.
    \tSupported PHP versions are: {versions}.
    \tSwitch the following cronjobs to one of the supported versions in order to continue with the conversion process:"
    \t- {cronjobs}

    \tYou can do this in the Plesk web interface by going “Tools & Settings” → “Scheduled Tasks”.
    """,
            formatter=lambda installed_unsupported_php: self._format_description(installed_unsupported_php),
            condition=lambda php: php in self.allowed_versions,
            optional=optional,
        )

    def _format_description(self, violating_php_cronjobs: typing.List[str]) -> str:
        return self.description.format(
            versions=sorted([str(php) for php in self.allowed_versions]),
            cronjobs="\n\t- ".join(violating_php_cronjobs),
        )


class AssertMinPhpVersionUsedByCron(AssertPhpVersionsUsedByCronByCondition):
    min_version: version.PHPVersion

    def __init__(
        self,
        min_version: str,
        optional: bool = True,
    ):
        self.min_version = version.PHPVersion(min_version)
        super().__init__(
            name="checking cronjob using outdated PHP",
            description="""We have detected that some cronjobs are using outdated PHP versions.
    \tSwitch the following cronjobs to {modern} or later in order to continue with the conversion process:"
    \t- {cronjobs}

    \tYou can do this in the Plesk web interface by going “Tools & Settings” → “Scheduled Tasks”.
    """,
            formatter=lambda installed_unsupported_php: self._format_description(installed_unsupported_php),
            condition=lambda php: php >= self.min_version,
            optional=optional,
        )

    def _format_description(self, violating_php_cronjobs: typing.List[str]) -> str:
        return self.description.format(
            modern=self.min_version,
            cronjobs="\n\t- ".join(violating_php_cronjobs),
        )


class AssertOsVendorPhpUsedByWebsites(action.CheckAction):
    min_version: version.PHPVersion

    def __init__(
            self,
            min_version: str,
    ):
        self.name = "checking OS vendor PHP used by websites"
        self.min_version = version.PHPVersion(min_version)
        self.description = """We have detected that some domains are using the OS vendor PHP version.
\tSwitch the following domains to {modern} or later in order to continue with the conversion process:
\t- {domains}

\tYou can achieve this by executing the following command:
\t> plesk bin domain -u [domain] -php_handler_id plesk-php80-fastcgi
"""

    def _do_check(self) -> bool:
        log.debug("Checking the OS vendor PHP version used by the websites")
        if not plesk.is_plesk_database_ready():
            log.info("Plesk database is not ready. Skipping the OS vendor PHP check.")
            return True

        os_vendor_php_handlers = [f"'{handler}'" for handler in ["fpm", "fastcgi"]]
        log.debug(f"OS vendor PHP handlers: {os_vendor_php_handlers}")

        try:
            looking_for_domains_sql_request = """
                SELECT d.name FROM domains d JOIN hosting h ON d.id = h.dom_id WHERE h.php_handler_id in ({});
            """.format(", ".join(os_vendor_php_handlers))

            os_vendor_php_domains = plesk.get_from_plesk_database(looking_for_domains_sql_request)
            if not os_vendor_php_domains:
                return True

            log.debug(f"OS vendor PHP domains: {os_vendor_php_domains}")
            self.description = self.description.format(
                modern=self.min_version,
                domains="\n\t- ".join(os_vendor_php_domains),
            )
        except Exception as ex:
            error_msg = "Unable to retrieve the list of domains using the PHP provided by the operating system vendor from the Plesk database"
            log.err(error_msg)
            raise RuntimeError(error_msg) from ex

        return False


class AssertNotInContainer(action.CheckAction):
    def __init__(self):
        self.name = "check if the system not in a container"
        self.description = "The system is running in a container-like environment ({}). The conversion is not supported for such systems."

    def _is_docker(self) -> bool:
        return os.path.exists("/.dockerenv")

    def _is_podman(self) -> bool:
        return os.path.exists("/run/.containerenv")

    def _is_cloudlinux(self) -> bool:
        try:
            os_release_filename = '/etc/os-release'
            section_name = 'top'
            config = configparser.ConfigParser()
            with open(os_release_filename, encoding='utf-8') as stream:
                config.read_string(f"[{section_name}]\n" + stream.read())
            os_name = config.get(section_name, 'ID').strip('"')
            return os_name == "cloudlinux"
        except (OSError, IOError, configparser.Error):
            return False

    def _is_vz_like(self) -> bool:
        return os.path.exists("/proc/vz") and not self._is_cloudlinux()

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


# TODO: Unfortunately there is no "--bytes" and "--json" options in findmnt on CentOS 7,
# So we need to redo following check action to make sure it is usable in centos2alma utility.
class AssertMinFreeDiskSpace(action.CheckAction):
    """Check if there's enough free disk space.

    Args:
        requirements: A dictionary mapping paths to minimum free disk
            space (in bytes) on the devices containing them.
        name: Name of the check.
    """
    violations: typing.List[MinFreeDiskSpaceViolation]
    """List of filesystems with insiffucient free disk space."""

    def __init__(
        self,
        requirements: typing.Dict[str, int],
        name: str = "check if there's enough free disk space",
    ):
        self.requirements = requirements
        self.name = name
        self.violations = []

    def _update_description(self) -> None:
        """Update description of violations."""
        if not self.violations:
            self.description = ""
            return
        res = "There's not enough free disk space: "
        res += ", ".join(
            f"on filesystem {v.dev!r} for "
            f"{', '.join(repr(p) for p in sorted(v.paths))} "
            f"(need {v.req_bytes / 1024**2} MiB, "
            f"got {v.avail_bytes / 1024**2} MiB)" for v in self.violations
        )
        self.description = res

    def _do_check(self) -> bool:
        """Perform the check."""
        log.debug("Checking minimum free disk space")
        cmd = [
            "/bin/findmnt", "--output", "source,target,avail",
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
            if fs_data["source"] not in filesystems:
                log.debug(f"Discovered new filesystem {fs_data}")
                fs_data["req"] = 0
                fs_data["paths"] = set()
                filesystems[fs_data["source"]] = fs_data
            log.debug(
                f"Adding space requirement of {req} to "
                f"{filesystems[fs_data['source']]}"
            )
            filesystems[fs_data["source"]]["req"] += req
            filesystems[fs_data["source"]]["paths"].add(path)
        for dev, fs_data in filesystems.items():
            if fs_data["req"] > fs_data["avail"]:
                self.violations.append(
                    MinFreeDiskSpaceViolation(
                        dev,
                        fs_data["req"],
                        fs_data["avail"],
                        fs_data["paths"],
                    )
                )
        self._update_description()
        return len(self.violations) == 0


class AssertGrubInstalled(action.CheckAction):
    def __init__(self):
        self.name = "checking if grub is installed"
        self.description = """The /etc/default/grub file is missing. GRUB may not be installed.
\tMake sure that GRUB is installed and try again.
"""

    def _do_check(self) -> bool:
        return os.path.exists("/etc/default/grub")


class AssertGrub2Installed(action.CheckAction):
    def __init__(self):
        self.name = "checking if grub2 is installed"
        self.description = """Grub2 does not appear to be installed.
\tTo proceed with the conversion, please install the 'grub2', 'grub2-common' and/or 'grub2-tools' packages
"""

    def _do_check(self) -> bool:
        return os.path.exists("/etc/default/grub") and packages.is_package_installed("grub2-common")


class AssertNoMoreThenOneKernelDevelInstalled(action.CheckAction):
    def __init__(self):
        self.name = "checking if more than one kernel-devel package is installed"
        self.description = """More than one kernel-devel package is installed.
\tTo proceed with the conversion, please remove all kernel-devel packages except the one that corresponds to the running kernel.
\tKernel packages list:
\t- {}
"""

    def _do_check(self) -> bool:
        kernel_devel_packages = packages.get_installed_packages_list("kernel-devel")
        if len(kernel_devel_packages) <= 1:
            return True

        self.description = self.description.format("\n\t- ".join([pkg + "-" + ver for pkg, ver in kernel_devel_packages]))
        return False


class AssertSshPermitRootLoginConfigured(action.CheckAction):
    """
    Validates that `PermitRootLogin` is configured correctly in configuration file for sshd.
    By default, this check fails on known outdated values such as `'without-password'`,
    since it's unclear whether substitution actions will be applied or not.
    If you intend to allow such values, make sure to also invoke
    `SubstituteSshPermitRootLoginConfigured` to handle them appropriately.
    """
    skip_known_substitudes: bool

    def __init__(self, skip_known_substitudes=False) -> None:
        self.name = "checking if PermitRootLogin is configured in sshd_config"
        self.description = """The PermitRootLogin setting is missing in the /etc/ssh/sshd_config file.
\tBy default, this will be set to 'prohibit-password' on the new system, which may prevent SSH connection.
\tTo proceed with the conversion, you need to set PermitRootLogin explicitly in /etc/ssh/sshd_config.
\t- If you use password authentication, add "PermitRootLogin yes" to the file.
\t- If you use key-based authentication, add "PermitRootLogin prohibit-password" to the file.
"""
        self.skip_known_substitudes = skip_known_substitudes

    def _do_check(self) -> bool:
        sshd_config = "/etc/ssh/sshd_config"
        if not os.path.exists(sshd_config):
            return False

        with open(sshd_config, "r") as f:
            for line in f:
                if line.strip().startswith("PermitRootLogin yes") or \
                   line.strip().startswith("PermitRootLogin prohibit-password"):
                    return True

                if self.skip_known_substitudes and line.strip().startswith("PermitRootLogin without-password"):
                    log.debug("Skipping known substitute for PermitRootLogin")
                    return True

        return False


class AssertScriptVersionUpToDate(action.CheckAction):
    def __init__(self, githubURL: str, tool: str, version: version.DistupgradeToolVersion):
        self.name = f"checking if {tool} is up-to-date"
        self.description = """The '{}' new version is available. Current version is '{}', available version is '{}'.
\tPlease use the new version, or use --allow-old-script-version to proceed with the conversion.
"""

        self.githubURL = githubURL
        self.tool = tool
        self.version = version

    def _do_check(self):
        releases_url = f"{self.githubURL}/releases/latest"

        try:
            with urllib.request.urlopen(releases_url) as response:
                latest_version_url = response.geturl()
                latest_version = latest_version_url.split('/')[-1]
                latest_version = version.DistupgradeToolVersion(latest_version)
                if latest_version > self.version:
                    self.description = self.description.format(self.tool, self.version, latest_version)
                    return False
        except Exception as e:
            log.warn(f"Failed to check the latest version of {self.tool}: {e}")
            return True

        return True
