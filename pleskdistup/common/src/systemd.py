# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
import re
import typing
import shutil
import subprocess

from . import dist, log, util

SYSTEMCTL_BIN_PATH = "/usr/bin/systemctl"
if dist.get_distro().deb_based:
    SYSTEMCTL_BIN_PATH = "/bin/systemctl"

SYSTEMCTL_SERVICES_PATH = "/etc/systemd/system"
if dist.get_distro().deb_based:
    SYSTEMCTL_SERVICES_PATH = "/lib/systemd/system"


def is_service_exists(service: str) -> bool:
    res = subprocess.run([SYSTEMCTL_BIN_PATH, 'cat', service], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0


def is_service_active(service: str) -> bool:
    res = subprocess.run([SYSTEMCTL_BIN_PATH, 'is-active', service], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0


def get_required_services(service: str) -> typing.List[str]:
    res = subprocess.run(
        [SYSTEMCTL_BIN_PATH, 'show', '--property', 'Requires', service],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        universal_newlines=True
    )

    required_services = [service for service in res.stdout.split('s=')[1].split() if '.service' in service]
    return required_services


def is_service_masked(service: str) -> bool:
    # is-enabled for masked service will return return code 1
    # so don't check operation result by the standard subprocess.run() way
    res = subprocess.run(
        [SYSTEMCTL_BIN_PATH, 'is-enabled', service],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if res.stdout.startswith('masked'):
        return True
    return False


def is_service_startable(
        service: str,
        already_checked: typing.Optional[typing.Set[str]] = None
        ) -> bool:
    if not is_service_exists(service):
        log.debug(f"Service '{service}' doesn't exist")
        return False
    if is_service_masked(service):
        log.debug(f"Service '{service}' can't be started because it is masked")
        return False

    if already_checked is not None and service in already_checked:
        return True

    if already_checked is None:
        already_checked = {service}
    else:
        already_checked.add(service)

    required_services = get_required_services(service)
    for required_service in required_services:
        if not is_service_startable(required_service, already_checked):
            log.debug(f"Service '{service}' can't be started because required service '{required_service}' doesn't exist")
            return False
    return True


def reload_systemd_daemon():
    util.logged_check_call([SYSTEMCTL_BIN_PATH, "daemon-reload"])


def start_services(services: typing.List[str]):
    existed_services = [service for service in services if is_service_exists(service)]
    if not existed_services:
        return

    util.logged_check_call([SYSTEMCTL_BIN_PATH, "start"] + existed_services)


def stop_services(services: typing.List[str]):
    existed_services = [service for service in services if is_service_exists(service)]
    if not existed_services:
        return

    util.logged_check_call([SYSTEMCTL_BIN_PATH, "stop"] + existed_services)


def enable_services(services: typing.List[str]):
    existed_services = [service for service in services if is_service_exists(service)]
    if not existed_services:
        return

    util.logged_check_call([SYSTEMCTL_BIN_PATH, "enable"] + existed_services)


def disable_services(services: typing.List[str]):
    existed_services = [service for service in services if is_service_exists(service)]
    if not existed_services:
        return

    util.logged_check_call([SYSTEMCTL_BIN_PATH, "disable"] + existed_services)


def restart_services(services: typing.List[str]):
    existed_services = [service for service in services if is_service_exists(service)]
    if not existed_services:
        return

    util.logged_check_call([SYSTEMCTL_BIN_PATH, "restart"] + existed_services)


def do_reboot():
    subprocess.call([SYSTEMCTL_BIN_PATH, "reboot"])


def add_systemd_service(service: str, content: str):
    with open(f"{SYSTEMCTL_SERVICES_PATH}/{service}", "w") as dst:
        dst.write(content)

    enable_services([service])


def remove_systemd_service(service: str):
    service_config = f"{SYSTEMCTL_SERVICES_PATH}/{service}"

    if os.path.exists(service_config):
        disable_services([service])
        os.remove(service_config)


def get_systemd_config(path_to_config: str, section: str, variable: str) -> typing.Optional[str]:
    if not os.path.exists(path_to_config):
        return None

    with open(path_to_config, "r") as original:
        in_section = False
        for line in original.readlines():
            sec_match = re.match(r"\s*\[\s*(?P<sec_name>\S+)\s*\]", line)
            if sec_match:
                in_section = sec_match["sec_name"] == section
                continue
            if in_section:
                var_match = re.match(f"\\s*{variable}\\s*=\\s*(?P<value>.*)", line)
                if var_match:
                    return var_match["value"]
    return None


def inject_systemd_config(path_to_config: str, section: str, variable: str, value: str) -> None:
    if not os.path.exists(path_to_config):
        with open(path_to_config, "w") as dst:
            dst.write(f"[{section}]\n{variable}={value}\n")
        return

    with open(path_to_config, "r") as original, open(path_to_config + ".next", "w") as dst:
        section_found = in_section = False
        variable_found = False
        for line in original.readlines():
            sec_match = re.match(r"\s*\[\s*(?P<sec_name>\S+)\s*\]", line)
            if sec_match:
                if in_section:
                    in_section = False
                    if not variable_found:
                        dst.write(f"{variable}={value}\n")
                else:
                    in_section = sec_match["sec_name"] == section
                    section_found = in_section is True

            if in_section and re.match(f"\\s*{variable}\\s*=", line):
                line = f"{variable}={value}\n"
                variable_found = True

            dst.write(line)

        if not section_found:
            dst.write(f"\n[{section}]\n{variable}={value}\n")
        elif in_section and not variable_found:
            dst.write(f"{variable}={value}\n")

    shutil.move(path_to_config + ".next", path_to_config)
