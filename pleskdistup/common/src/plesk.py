# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import enum
import os
import re
import subprocess
import typing
import urllib.request
import xml.etree.ElementTree as ElementTree

from . import dist, log, mariadb, systemd, version, util

# http://autoinstall.plesk.com/products.inf3 is an xml file with available products,
# including all versions of Plesk.
DEFAULT_AUTOINSTALL_PRODUCTS_FILE = "http://autoinstall.plesk.com/products.inf3"


def send_error_report(error_message: str) -> None:
    log.debug(f"Error report: {error_message}")
    # Todo. For now we works only on RHEL-based distros, so the path
    # to the send-error-report utility will be the same.
    # But if we will support Debian-based we should choose path carefully
    send_error_path = "/usr/local/psa/admin/bin/send-error-report"
    try:
        if os.path.exists(send_error_path):
            subprocess.run([send_error_path, "backend"], input=error_message.encode(),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log.debug("Sent error report")
    except Exception as ex:
        log.debug(f"Sending error report failed: {ex}")


def get_plesk_version() -> version.PleskVersion:
    version_info = subprocess.check_output(["/usr/sbin/plesk", "version"], universal_newlines=True).splitlines()
    for line in version_info:
        if line.startswith("Product version"):
            return version.PleskVersion(line.split()[-1])

    raise Exception("Unable to parse plesk version output.")


def extract_plesk_versions(products_xml: str) -> typing.List[version.PleskVersion]:
    if not products_xml:
        return []

    versions = []
    root = ElementTree.fromstring(products_xml)
    for product in root.findall('.//product[@id="plesk"]'):
        release_key = product.get('release-key')
        if release_key and '-' in release_key:
            versions.append(version.PleskVersion(release_key.split("-", 1)[1]))
    return versions


def get_available_plesk_versions(
    autoinstall_products_file_url: str = DEFAULT_AUTOINSTALL_PRODUCTS_FILE
) -> typing.List[version.PleskVersion]:
    try:
        with urllib.request.urlopen(autoinstall_products_file_url) as response:
            products_config = response.read().decode('utf-8')
            return extract_plesk_versions(products_config)

    except Exception as ex:
        log.warn(f"Unable to retrieve available versions of plesk from '{autoinstall_products_file_url}': {ex}")
    return []


def get_plesk_full_version() -> typing.List[str]:
    return subprocess.check_output(["/usr/sbin/plesk", "version"], universal_newlines=True).splitlines()


def prepare_conversion_flag(status_flag_path: str) -> None:
    with open(status_flag_path, "w"):
        pass


def send_conversion_status(succeed: bool, status_flag_path: str) -> None:
    results_sender_path = None
    for path in ["/var/cache/parallels_installer/report-update", "/root/parallels/report-update"]:
        if os.path.exists(path):
            results_sender_path = path
            break

    # For now we are not going to install sender in scope of conversion.
    # So if we have one, use it. If not, just skip send the results
    if results_sender_path is None:
        log.warn("Unable to find report-update utility. Skip sending conversion status")
        return

    if not os.path.exists(status_flag_path):
        log.warn("Conversion status flag file does not exist. Skip sending conversion status")
        return

    plesk_version = str(get_plesk_version())

    try:
        log.debug(f"Trying to send status of conversion by report-update utility {results_sender_path!r}")
        subprocess.run(
            ["/usr/bin/python3", results_sender_path, "--op", "dist-upgrade", "--rc", "0" if succeed else "1",
             "--start-flag", status_flag_path, "--from", plesk_version, "--to", plesk_version],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as ex:
        log.warn("Unable to send conversion status: {}".format(ex))

    # usually the file should be removed by report-update utility
    # but if it will be failed, we should remove it manually
    remove_conversion_flag(status_flag_path)


def remove_conversion_flag(status_flag_path: str) -> None:
    if os.path.exists(status_flag_path):
        os.unlink(status_flag_path)


def list_installed_extensions() -> typing.List[typing.Tuple[str, str]]:
    if not is_plesk_database_ready():
        raise PleskDatabaseIsDown("retrieving installed extensions")

    ext_info = subprocess.check_output(["/usr/sbin/plesk", "bin", "extension", "--list"], universal_newlines=True).splitlines()
    res: typing.List[typing.Tuple[str, str]] = []
    for line in ext_info:
        if " - " in line:
            name, display_name = line.split(" - ", maxsplit=1)
            res.append((name, display_name))
    return res


def install_extension(name: str) -> None:
    if not is_plesk_database_ready():
        raise PleskDatabaseIsDown(f"extension {name!r} installation")

    util.logged_check_call(["/usr/sbin/plesk", "bin", "extension", "--install", name])


def uninstall_extension(name: str) -> None:
    if not is_plesk_database_ready():
        raise PleskDatabaseIsDown(f"extension {name!r} uninstallation")

    util.logged_check_call(["/usr/sbin/plesk", "bin", "extension", "--uninstall", name])


class PleskComponentState(enum.Enum):
    INSTALL = "install"
    UPGRADE = "upgrade"
    UP2DATE = "up2date"
    ERROR = "ERROR"


class PleskComponent:
    name: str
    state: PleskComponentState
    description: str

    def __init__(
        self,
        name: str,
        state: PleskComponentState,
        description: str,
    ):
        self.name = name
        self.state = state
        self.description = description

    def __str__(self) -> str:
        return f"{self.name} [{self.state}] - {self.description}"

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

    @property
    def is_installed(self) -> bool:
        return self.state in (PleskComponentState.UPGRADE, PleskComponentState.UP2DATE)


def list_installed_components() -> typing.Dict[str, PleskComponent]:
    """List installed Plesk components.

    Returns:
        A dictionary mapping component names to PleskComponent instances.
    """
    cmd = ["/usr/sbin/plesk", "installer", "--select-release-current", "--show-components"]
    log.debug(f"Listing installed Plesk components by {cmd}")
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        universal_newlines=True,
    )
    log.debug(f"Command {cmd} returned {proc.returncode}, stdout: '{proc.stdout}', stderr: '{proc.stderr}'")
    comp_info = proc.stdout.splitlines()
    res: typing.Dict[str, PleskComponent] = {}
    comp_re = re.compile(r"\s*(?P<name>\S+)\s*\[(?P<state>[^]]+)\]\s*-\s*(?P<desc>.*)")
    for line in comp_info:
        log.debug(f"Parsing line {line!r} of components listing")
        m = comp_re.match(line)
        if m:
            c = PleskComponent(
                name=m["name"],
                state=PleskComponentState(m["state"]),
                description=m["desc"],
            )
            log.debug(f"Discovered component {c}")
            res[c.name] = c
    return res


class PleskDatabaseIsDown(Exception):
    def __init__(self, message: str = ""):
        self.message = f"Plesk database is not ready at: {message}"
        super().__init__(self.message)


def is_plesk_database_ready() -> bool:
    if mariadb.is_mariadb_installed():
        return systemd.is_service_active("mariadb")
    return systemd.is_service_active("mysql")


def get_from_plesk_database(query: str) -> typing.Optional[typing.List[str]]:
    if not is_plesk_database_ready():
        # This could be fine when we just restart the conversion/distupgrade tool
        # However, let's log this anyway, it might be a good point to reveal problems
        log.warn("Plesk database is not ready")
        return None

    cmd = ["/usr/sbin/plesk", "db", "-B", "-N", "-e", query]
    log.debug(f"Executing query {cmd}")
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        universal_newlines=True,
    )
    log.debug(f"Command {cmd} returned {proc.returncode}, stdout: '{proc.stdout}', stderr: '{proc.stderr}'")
    return proc.stdout.splitlines()


def get_repository_by_os_from_inf3(inf3_content: typing.Union[ElementTree.Element, str], os: dist.Distro) -> typing.Optional[str]:
    if isinstance(inf3_content, str):
        if not inf3_content:
            return None
        inf3_content = ElementTree.fromstring(inf3_content)

    for build in inf3_content.findall(".//build"):
        entry_os_vendor = build.get("os_vendor")
        entry_os_version = build.get("os_version")
        if not entry_os_vendor or not entry_os_version:
            continue

        if entry_os_vendor == os.name and entry_os_version.split('.')[0] == os.version:
            entry_config_attr = build.get("config")
            if entry_config_attr:
                return entry_config_attr.rsplit("/", 1)[0]
            return None
    return None
