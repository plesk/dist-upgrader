# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import pwd
import shutil
import typing

from pleskdistup.common import action, dist, files, plesk, log, systemd, util


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

    def __init__(self):
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
        return self.ext_name in dict(plesk.list_installed_extensions())

    def _prepare_action(self) -> action.ActionResult:
        plesk.uninstall_extension(self.ext_name)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        plesk.install_extension(self.ext_name)
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 10

    def estimate_revert_time(self) -> int:
        return 20


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
        extensions = dict(plesk.list_installed_extensions())
        log.debug(f"Detected installed Plesk extensions: {extensions}")

        self.installed_violations = set(extension for extension in self.installed if extension not in extensions)
        log.debug(f"Missing required extensions: {self.installed_violations}")

        self.not_installed_violations = set(extension for extension in self.not_installed if extension in extensions)
        log.debug(f"Installed conflicting extensions: {self.not_installed_violations}")

        return not self.installed_violations and not self.not_installed_violations
