# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
import pwd
import shutil
import sys
import typing

from pleskdistup.common import action, dist, files, packages, plesk, log, systemd, util


class DisableGrafana(action.ActiveAction):
    def __init__(self):
        self.name = "disable grafana"

    def _is_required(self) -> bool:
        return systemd.is_service_exists("grafana-server.service")

    def _prepare_action(self) -> action.ActionResult:
        systemd.stop_services(["grafana-server.service"])
        systemd.disable_services(["grafana-server.service"])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        systemd.enable_services(["grafana-server.service"])
        systemd.start_services(["grafana-server.service"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        systemd.enable_services(["grafana-server.service"])
        systemd.start_services(["grafana-server.service"])
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 20

    def estimate_post_time(self) -> int:
        return 20

    def estimate_revert_time(self) -> int:
        return 20


# We should do rebundling of ruby applications after the conversion
# because some of our libraries will be missing.
# The prime example of missing library - libmysqlclient.so.18 required by mysql2 gem
class RebundleRubyApplications(action.ActiveAction):
    plesk_apache_configs_path: str

    def __init__(self) -> None:
        self.name = "rebundling ruby applications"
        self.description = "rebundling ruby applications"

        self.plesk_apache_configs_path = "/etc/httpd/conf/plesk.conf.d/vhosts/"
        if dist.get_distro().deb_based:
            self.plesk_apache_configs_path = "/etc/apache2/plesk.conf.d/vhosts/"

    def _is_ruby_domain(self, domain_path) -> bool:
        if not os.path.isdir(domain_path) or domain_path in ["system", "chroot"]:
            # Not a domain actually
            return False

        return os.path.exists(os.path.join(domain_path, ".rbenv"))

    def _get_ruby_domains(self) -> typing.List[str]:
        return [domain_path.name for domain_path in os.scandir("/var/www/vhosts") if self._is_ruby_domain(domain_path)]

    def _is_required(self) -> bool:
        if not os.path.exists("/var/lib/rbenv/versions/"):
            return False

        return any(self._is_ruby_domain(domain) for domain in os.scandir("/var/www/vhosts"))

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _get_ruby_application_path_by_config(self, domain_name: str) -> typing.Optional[str]:
        apache_config = os.path.join(self.plesk_apache_configs_path, domain_name + ".conf")

        if not os.path.isfile(apache_config) or not files.find_file_substrings(apache_config, "PassengerRuby"):
            # Likely it means ruby application is not enabled, so we need to do direct search in the filesystem
            return None

        application_root = files.find_file_substrings(apache_config, "PassengerAppRoot")
        if not application_root:
            return None

        # Record format is: PassengerAppRoot "[path]"
        # We can expect it is always in this format since configuration is generated by plesk
        return application_root[0].split()[1].strip("\"")

    def _get_ruby_application_path_by_bundle_subdir(self, domain_home: str) -> typing.Optional[str]:
        bundle = files.find_subdirectory_by(
            domain_home,
            lambda subdir: os.path.basename(subdir) == "bundle" and os.path.exists(os.path.join(subdir, "ruby"))
        )
        if bundle is None or not os.path.isdir(bundle):
            return None

        return os.path.dirname(os.path.dirname(bundle))

    def _get_ruby_application_paths(self, domain_path: str) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        app_directory = self._get_ruby_application_path_by_config(domain_path)
        if app_directory is None:
            log.debug(f"Ruby application is disabled. Search for application root in filesystem. Domain home directory: {domain_path}")
            app_directory = self._get_ruby_application_path_by_bundle_subdir(domain_path)

        if app_directory is None:
            return None, None

        return app_directory, os.path.join(app_directory, "vendor", "bundle")

    def _post_action(self) -> action.ActionResult:
        for domain_path in self._get_ruby_domains():
            log.debug(f"Re-bundling ruby application in domain: {domain_path}")

            app_directory, bundle = self._get_ruby_application_paths(domain_path)

            if bundle is None or not os.path.isdir(bundle) or app_directory is None:
                log.debug(f"Skip re-bundling for non bundling domain '{domain_path}'")
                continue

            stat_info = os.stat(app_directory)
            username = pwd.getpwuid(stat_info.st_uid).pw_name

            log.debug(f"Bundle: {bundle}. App directory: {app_directory}. Username: {username}")

            shutil.rmtree(bundle)
            util.logged_check_call(["/usr/sbin/plesk", "sbin", "rubymng", "run-bundler", username, app_directory])

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self) -> int:
        return 60 * len(self._get_ruby_domains())


class UninstallTuxcareEls(action.ActiveAction):
    """ TuxCare ELS extension is installed on EoL OSes and may enable repositories incompatible with
        the target OS version. Uninstalling also removes the repositories.
    """
    ext_name: str

    def __init__(self) -> None:
        self.name = "uninstall tuxcare-els"
        self.ext_name = "tuxcare-els"

    def _is_required(self) -> bool:
        try:
            return self.ext_name in dict(plesk.list_installed_extensions())
        except plesk.PleskDatabaseIsDown:
            # If database is not ready we will not be able to uninstall the extension anyway
            log.warn("Mark the Tuxcare ELS extension uninstallation as unnecessary because the Plesk database isn't running")
            return False

    def _prepare_action(self) -> action.ActionResult:
        try:
            plesk.uninstall_extension(self.ext_name)
        except plesk.PleskDatabaseIsDown:
            log.warn("Removing TuxCare ELS extension called when Plesk database is already down")
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        try:
            plesk.install_extension(self.ext_name)
        except plesk.PleskDatabaseIsDown:
            log.warn("Re-installing TuxCare ELS extension called when Plesk database is still down")
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 10

    def estimate_revert_time(self) -> int:
        return 20


class PostInstallTuxcareEls(action.ActiveAction):
    """ TuxCare ELS extension should be installed on select target EoL OSes.
    """
    ext_name: str

    def __init__(self) -> None:
        self.name = "install tuxcare-els"
        self.ext_name = "tuxcare-els"

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        try:
            plesk.install_extension(self.ext_name)
        except plesk.PleskDatabaseIsDown:
            log.warn("Installing TuxCare ELS extension called when Plesk database is still down")
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        try:
            plesk.uninstall_extension(self.ext_name)
        except plesk.PleskDatabaseIsDown:
            log.warn("Uninstalling TuxCare ELS extension called when Plesk database is already down")
        return action.ActionResult()

    def estimate_post_time(self) -> int:
        return 20

    def estimate_revert_time(self) -> int:
        return 10


class AssertPleskExtensions(action.CheckAction):
    installed: typing.Set[str]
    not_installed: typing.Set[str]
    installed_description: str
    not_installed_description: str
    installed_violations: typing.Set[str]
    not_installed_violations: typing.Set[str]
    _name: str

    def __init__(
        self,
        installed: typing.Optional[typing.Iterable[str]] = None,
        not_installed: typing.Optional[typing.Iterable[str]] = None,
        name: str = "check Plesk extensions state:",
        installed_description: typing.Optional[str] = None,
        not_installed_description: typing.Optional[str] = None,
    ):
        if installed is None and not_installed is None:
            raise ValueError("'installed' and 'not_installed' can't be both None")
        self.installed = set(installed) if installed is not None else set()
        self.not_installed = set(not_installed) if not_installed is not None else set()
        self._name = name
        self.installed_violations = set()
        self.not_installed_violations = set()

        self._installed_description = "Required Plesk extensions are missing. To continue, please install the following extensions:\n\t- {installed_violations}"
        if installed_description is not None:
            self._installed_description = installed_description

        self._not_installed_description = "There are conflicting Plesk extensions installed. To proceed, please remove the following extensions:\n\t- {not_installed_violations}"
        if not_installed_description is not None:
            self._not_installed_description = not_installed_description

    @property
    def name(self) -> str:
        res = self._name
        if res.endswith(":"):
            comp_list = [f"+{c}" for c in self.installed]
            comp_list += [f"-{c}" for c in self.not_installed]
            comp_list.sort()
            res += f" {', '.join(comp_list)}"
        return res

    @name.setter
    def name(self, val: str) -> None:
        self._name = val

    @property
    def description(self) -> str:
        desc: typing.List[str] = []
        if self._installed_description and self.installed_violations:
            desc.append(self._installed_description.format(installed_violations='\n\t- '.join(self.installed_violations)))
        if self._not_installed_description and self.not_installed_violations:
            desc.append(self._not_installed_description.format(not_installed_violations='\n\t- '.join(self.not_installed_violations)))
        if desc:
            return "\n\t".join(desc)
        return "Plesk extensions state check passed"

    @description.setter
    def description(self, val: str) -> None:
        raise NotImplementedError

    def _do_check(self) -> bool:
        try:
            extensions = dict(plesk.list_installed_extensions())
            log.debug(f"Detected installed Plesk extensions: {extensions}")

            self.installed_violations = set(extension for extension in self.installed if extension not in extensions)
            log.debug(f"Missing required extensions: {self.installed_violations}")

            self.not_installed_violations = set(extension for extension in self.not_installed if extension in extensions)
            log.debug(f"Installed conflicting extensions: {self.not_installed_violations}")

            return not self.installed_violations and not self.not_installed_violations
        except plesk.PleskDatabaseIsDown:
            return True


class AssertEnoughRamForAmavis(action.CheckAction):
    required_ram: int
    amavis_upgrade_allowed: bool

    def __init__(self, required_ram: int, amavis_upgrade_allowed: bool):
        self.name = "asserting enough RAM for Amavis"
        self.required_ram = required_ram
        self.amavis_upgrade_allowed = amavis_upgrade_allowed
        self.description = f"""You have Amavis antivirus installed. It needs at least {required_ram / 1073741824} GB of RAM to work properly on the target OS.
\tIf you don’t have enough RAM, Amavis might crash or cause your system to stop working.
\tIf you accept this risk, you can proceed by running `{os.path.basename(sys.argv[0])} --amavis-upgrade-allowed`.
\tAlternatively, you can remove Amavis antivirus to proceed with the conversion.
"""

    def _get_available_ram(self) -> int:
        with open('/proc/meminfo', 'r') as meminfo:
            for line in meminfo:
                if line.startswith('MemAvailable:'):
                    # We got data in KB, so we need to convert it to bytes
                    return int(line.split()[1]) * 1024
        return 0

    def _do_check(self) -> bool:
        # Amavis consumes a lot of RAM on AlmaLinux 8, which for example causes hangs on t2.micro instances
        # Therefore, it's advisable to inform users about potential issues beforehand
        # If you add support for other OSes it worth to check the RAM requirements for amavis on them
        return not packages.is_package_installed("amavis") or self._get_available_ram() > self.required_ram or self.amavis_upgrade_allowed


class ReinstallAmavisAntivirus(action.ActiveAction):
    def __init__(self):
        self.name = "reinstalling amavis antivirus"

    def _is_required(self) -> bool:
        return packages.is_package_installed("amavis")

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        packages.install_packages(["amavis"])

        amavis_systemd_service = "amavisd.service"
        if systemd.is_service_startable(amavis_systemd_service):
            util.logged_check_call(["/usr/bin/systemctl", "enable", amavis_systemd_service])

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self) -> int:
        return 30
