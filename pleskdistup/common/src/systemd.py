# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import typing
import subprocess

from . import dist, util

SYSTEMCTL_BIN_PATH = "/usr/bin/systemctl"
if dist._is_deb_based(dist.get_distro()):
    SYSTEMCTL_BIN_PATH = "/bin/systemctl"

SYSTEMCTL_SERVICES_PATH = "/etc/systemd/system"
if dist._is_deb_based(dist.get_distro()):
    SYSTEMCTL_SERVICES_PATH = "/lib/systemd/system"


def is_service_exists(service: str):
    res = subprocess.run([SYSTEMCTL_BIN_PATH, 'cat', service], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0


def is_service_active(service: str):
    res = subprocess.run([SYSTEMCTL_BIN_PATH, 'is-active', service])
    return res.returncode == 0


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
