# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import os
import pathlib
import subprocess
import typing

from pleskdistup.common import action, packages, plesk, log, util


def _change_plesk_components(
    add_components: typing.Optional[typing.Iterable[str]] = None,
    remove_components: typing.Optional[typing.Iterable[str]] = None,
) -> None:
    log.debug(f"Changing Plesk components. Add: {add_components}, remove: {remove_components}")
    if add_components is None and remove_components is None:
        raise ValueError("add_components and remove_components can't be both None")
    add_comp_list = list(add_components) if add_components else []
    rm_comp_list = list(remove_components) if remove_components else []
    if not add_comp_list and not rm_comp_list:
        return
    cmd = ["/usr/sbin/plesk", "installer", "--select-product-id", "plesk", "--select-release-current"]
    # Installation of "panel" is a precaution against accidentally
    # removing Plesk (e.g. removing Postfix without installing msmtp
    # at the same time on Ubuntu 18 has this effect)
    if rm_comp_list and "panel" not in add_comp_list:
        add_comp_list.append("panel")
    for c in add_comp_list:
        cmd += ["--install-component", c]
    for c in rm_comp_list:
        cmd += ["--remove-component", c]
    util.logged_check_call(cmd)


class RemoveMailComponents(action.ActiveAction):
    name: str
    state_dir: str

    def __init__(self, state_dir: str):
        self.name = "remove mail components, switch to msmtp"
        self.state_dir = state_dir

    @property
    def _removed_components_list_file(self) -> str:
        return os.path.join(self.state_dir, "plesk-dist-upgrade-removed_mail_components.txt")

    def _prepare_action(self) -> action.ActionResult:
        mail_components_2_packages = {
            "postfix": "postfix",
            "dovecot": "plesk-dovecot",
            "qmail": "psa-qmail",
            "courier": "psa-courier-imap",
            "spamassassin": "psa-spamassassin",
            "mailman": "psa-mailman",
        }

        log.debug("Checking if there are mail components to remove...")
        components_to_remove = []
        for component, package in mail_components_2_packages.items():
            if packages.is_package_installed(package):
                components_to_remove.append(component)
        if not components_to_remove:
            log.debug("No mail components to remove")
            return action.ActionResult()
        log.debug(f"Mail components to remove: {components_to_remove}")

        with open(self._removed_components_list_file, "w") as f:
            f.write("\n".join(components_to_remove))

        log.debug(f"Replacing {components_to_remove} with msmtp...")
        _change_plesk_components(add_components=["msmtp"], remove_components=components_to_remove)
        return action.ActionResult()

    def _reinstall_removed_components(self):
        if not os.path.exists(self._removed_components_list_file):
            log.warn("File with removed email components list does not exist. The reinstallation is skipped.")
            return action.ActionResult()

        log.debug("Checking if there are mail components to reinstall...")
        with open(self._removed_components_list_file, "r") as f:
            components_to_install = f.read().splitlines()
        if components_to_install:
            log.debug(f"Reinstalling removed mail components: {components_to_install}")
            _change_plesk_components(add_components=components_to_install)

        os.unlink(self._removed_components_list_file)

    def _post_action(self) -> action.ActionResult:
        self._reinstall_removed_components()
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        self._reinstall_removed_components()
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 2 * 60

    def estimate_post_time(self) -> int:
        return 3 * 60

    def estimate_revert_time(self) -> int:
        return 3 * 60


class RemovePleskComponents(action.ActiveAction):
    _name: str
    components_to_remove: typing.List[str]
    state_dir: str
    post_reinstall: bool

    def __init__(
        self,
        components_to_remove: typing.Iterable[str],
        state_dir: str,
        name: str = "remove Plesk components",
        post_reinstall: bool = False,
    ):
        self._name = name
        self.components_to_remove = list(components_to_remove)
        self.state_dir = state_dir
        self.post_reinstall = post_reinstall

    @property
    def name(self) -> str:
        return f"{self._name}: {', '.join(self.components_to_remove)}"

    @property
    def _removed_components_list_file(self) -> str:
        return os.path.join(self.state_dir, f"plesk-dist-upgrade-{self.__class__.__name__}.txt")

    def _prepare_action(self) -> action.ActionResult:
        log.debug(f"Going to remove Plesk components: {self.components_to_remove}")
        _change_plesk_components(remove_components=self.components_to_remove)
        with open(self._removed_components_list_file, "w") as f:
            f.write("\n".join(self.components_to_remove))

        return action.ActionResult()

    def _reinstall_removed_components(self) -> None:
        if not os.path.exists(self._removed_components_list_file):
            log.warn("File with removed components list does not exist. The reinstallation is skipped.")

        with open(self._removed_components_list_file, "r") as f:
            components_to_install = f.read().splitlines()

        if components_to_install:
            log.debug(f"Reinstalling removed Plesk components: {components_to_install}")
            _change_plesk_components(add_components=components_to_install)

        os.unlink(self._removed_components_list_file)

    def _post_action(self) -> action.ActionResult:
        if self.post_reinstall:
            self._reinstall_removed_components()
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        self._reinstall_removed_components()
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 2 * 60

    def estimate_post_time(self) -> int:
        return 3 * 60

    def estimate_revert_time(self) -> int:
        return 3 * 60


class UpdatePlesk(action.ActiveAction):
    name: str
    update_cmd_args: typing.List[str]

    def __init__(
        self,
        name: str = "update Plesk",
        update_cmd_args: typing.Optional[typing.Iterable[str]] = None,
    ):
        self.name = name
        self.update_cmd_args = list(update_cmd_args) if update_cmd_args is not None else []

    def _prepare_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"] + self.update_cmd_args)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult(action.ActionState.SKIPPED)

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult(action.ActionState.SKIPPED)

    def estimate_prepare_time(self) -> int:
        return 3 * 60

    def estimate_post_time(self) -> int:
        return 0

    def estimate_revert_time(self) -> int:
        return 0


class UpdatePleskExtensions(action.ActiveAction):
    _name: str
    extensions_to_update: typing.Optional[typing.Set[str]]

    # If extensions_to_update is None or empty, all installed extensions are updated
    def __init__(
        self,
        extensions_to_update: typing.Optional[typing.Iterable[str]] = None,
        name: str = "update Plesk extensions",
    ):
        self.extensions_to_update = set(extensions_to_update) if extensions_to_update is not None else None
        if not self.extensions_to_update:
            raise RuntimeError("extensions_to_update may not be empty")
        self._name = name

    @property
    def name(self):
        res = self._name
        if self.extensions_to_update:
            res += f": {', '.join(sorted(self.extensions_to_update))}"
        return res

    def _prepare_action(self) -> action.ActionResult:
        installed_extensions = set(ext[0] for ext in plesk.list_installed_extensions())
        log.debug(f"Currently installed extensions: {installed_extensions}")
        if installed_extensions:
            res_ext = installed_extensions
            if self.extensions_to_update is not None:
                res_ext &= self.extensions_to_update
            if res_ext:
                ext_list = sorted(res_ext)
                log.debug(f"Going to update extensions: {ext_list}")
                for ext in ext_list:
                    util.logged_check_call(
                        ["/usr/sbin/plesk", "bin", "extension", "-i", str(ext)]
                    )
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult(action.ActionState.SKIPPED)

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult(action.ActionState.SKIPPED)

    def estimate_prepare_time(self) -> int:
        if self.extensions_to_update is not None:
            extnum = len(self.extensions_to_update)
        else:
            extnum = len(set(ext[0] for ext in plesk.list_installed_extensions()))
        return 20 * extnum

    def estimate_post_time(self) -> int:
        return 0

    def estimate_revert_time(self) -> int:
        return 0


class SwitchPleskRepositories(action.ActiveAction):
    to_os_version: str
    name: str

    def __init__(
        self,
        to_os_version: str,
        name: str = "switch Plesk repositories",
    ):
        self.to_os_version = to_os_version
        self.name = name

    def _prepare_action(self) -> action.ActionResult:
        for f in pathlib.Path("/etc/apt/sources.list.d/").glob("plesk*.list"):
            log.debug(f"Removing {f}")
            os.unlink(f)
        util.logged_check_call([
            "/usr/sbin/plesk", "installer", "--override-os-version",
            self.to_os_version, "--check-updates", "--skip-cleanup",
        ])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult(action.ActionState.SKIPPED)

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult(action.ActionState.SKIPPED)

    def estimate_prepare_time(self) -> int:
        return 2 * 60

    def estimate_post_time(self) -> int:
        return 0

    def estimate_revert_time(self) -> int:
        return 0


class EnableEnhancedSecurityMode(action.ActiveAction):
    name: str

    def __init__(
        self,
        name: str = "turn on the enhanced security mode in Plesk (encrypt passwords)",
    ):
        self.name = name

    def _prepare_action(self) -> action.ActionResult:
        util.logged_check_call([
            "/usr/sbin/plesk", "bin", "passwords", "--encrypt",
        ])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult(action.ActionState.SKIPPED)

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult(action.ActionState.SKIPPED)

    def estimate_prepare_time(self) -> int:
        return 10

    def estimate_post_time(self) -> int:
        return 0

    def estimate_revert_time(self) -> int:
        return 0


class AssertPleskComponents(action.CheckAction):
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
        name: str = "check Plesk components state:",
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
        if installed_description is None:
            self._installed_description = "These not installed Plesk components need to be installed before upgrading to the new OS version: {installed_violations}. Please install them using Plesk installer."
        if not_installed_description is None:
            self._not_installed_description = "These installed Plesk components need to be removed before upgrading to the new OS version: {not_installed_violations}. Please remove them using Plesk installer."

    @property
    def name(self) -> str:
        res = self._name
        if res.endswith(":"):
            comp_list = [f"+{c}" for c in self.installed]
            comp_list += [f"-{c}" for c in self.not_installed]
            comp_list.sort()
            res += f" {', '.join(comp_list)}"
        return res

    @property
    def description(self) -> str:
        desc: typing.List[str] = []
        if self._installed_description and self.installed_violations:
            desc.append(self._installed_description.format(installed_violations=self.installed_violations))
        if self._not_installed_description and self.not_installed_violations:
            desc.append(self._not_installed_description.format(not_installed_violations=self.not_installed_violations))
        if desc:
            return "\n".join(desc)
        return "Plesk components state check passed"

    def _do_check(self) -> bool:
        comp_list = plesk.list_installed_components()
        log.debug(f"Detected installed Plesk components: {comp_list}")
        # TODO error out for unknown components
        self.installed_violations = set(comp for comp in self.installed if comp not in comp_list or not comp_list[comp].is_installed)
        log.debug(f"Components we want, but don't have: {self.installed_violations}")
        self.not_installed_violations = set(comp for comp in self.not_installed if comp in comp_list and comp_list[comp].is_installed)
        log.debug(f"Components we have, but don't want: {self.not_installed_violations}")
        return not self.installed_violations and not self.not_installed_violations


class AssertPleskInstallerNotInProgress(action.CheckAction):
    def __init__(self):
        self.name = "check if Plesk installer is in progress"
        self.description = """The conversion process cannot continue because Plesk Installer is working.
\tPlease wait until it finishes or call 'plesk installer stop' to abort it.
"""

    def _do_check(self) -> bool:
        installer_status = subprocess.check_output(
            ["/usr/sbin/plesk", "installer", "--query-status", "--enable-xml-output"],
            universal_newlines=True,
        )
        return ("query_ok" in installer_status)


class AssertMinPleskVersion(action.CheckAction):
    min_version: typing.List[int]
    _name: str
    _description: str

    def __init__(
        self,
        min_version: str,
        name: str = "check for minimal Plesk version {min_version}",
        description: str = "Only Plesk Obsidian {min_version} or later is supported. Please upgrade Plesk and try again.",
    ):
        try:
            vlist = min_version.split(".")
            if len(vlist) not in (3, 4):
                raise ValueError("Incorrect version length")
            self.min_version = [int(v) for v in vlist]
            if any(v < 0 for v in self.min_version):
                raise ValueError("Negative number in version")
            if len(self.min_version) == 3:
                self.min_version.append(0)
        except Exception as e:
            raise ValueError("Plesk version must be in the 1.2.3[.4] format, e.g. 18.0.58 or 18.0.58.0") from e
        assert len(self.min_version) == 4
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name.format(min_version=self.min_version_str)

    @property
    def description(self) -> str:
        return self._description.format(min_version=self.min_version_str)

    @property
    def min_version_str(self) -> str:
        return ".".join(str(v) for v in self.min_version)

    def _do_check(self) -> bool:
        try:
            cur_version = [int(v) for v in plesk.get_plesk_version()]
            log.debug(f"Checking if cur_version >= min_version ({cur_version!r} >= {self.min_version!r})")
            assert len(cur_version) == 4, "Incorrect version length"
            return cur_version >= self.min_version
        except Exception as e:
            log.err(f"Checking Plesk version has failed with error: {e}")
            raise
