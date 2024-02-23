# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import os
import typing

from pleskdistup.common import action, systemd, util


class AddUpgradeSystemdService(action.ActiveAction):
    util_path: str
    options: typing.Any
    service_name: str
    _state_dir: str
    _name: str
    _service_file_path: str
    _service_content: str

    def __init__(
        self,
        util_path: str,
        options: typing.Any,
        name: str = "add the service {self.service_name!r} to resume Plesk dist-upgrade after reboot",
        service_name: str = "plesk-dist-upgrade-resume.service",
    ):
        self.util_path = util_path
        self.options = options
        self.service_name = service_name

        self._state_dir = options.state_dir
        self._name = name
        self._service_file_path = os.path.join("/etc/systemd/system", self.service_name)
        self._service_content = """
[Unit]
Description=Resume Plesk dist-upgrade after reboot
After=network.target network-online.target

[Service]
Type=simple
# want to run it once per boot time
RemainAfterExit=yes
ExecStart={util_path} --state-dir "{state_dir}" --resume {arguments}

[Install]
WantedBy=multi-user.target
"""

    @property
    def name(self):
        return self._name.format(self=self)

    @property
    def _service_arguments(self) -> typing.List[str]:
        args = []
        if self.options.verbose:
            args.append("--verbose")
        if self.options.log_file:
            args.append(f'--log-file "{self.options.log_file}"')
        return args

    def _prepare_action(self) -> action.ActionResult:
        systemd.add_systemd_service(
            self.service_name,
            self._service_content.format(
                util_path=self.util_path,
                state_dir=self._state_dir,
                arguments=" ".join(self._service_arguments)
            ),
        )
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        systemd.remove_systemd_service(self.service_name)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        systemd.remove_systemd_service(self.service_name)
        return action.ActionResult()


class DisablePleskRelatedServicesDuringUpgrade(action.ActiveAction):
    plesk_systemd_services: typing.List[str]
    oneshot_services: typing.List[str]

    def __init__(self):
        self.name = "rule plesk services"
        plesk_known_systemd_services = [
            "crond.service",
            "dovecot.service",
            "drwebd.service",
            "fail2ban.service",
            "httpd.service",
            "mailman.service",
            "mariadb.service",
            "mysqld.service",
            "named-chroot.service",
            "plesk-ext-monitoring-hcd.service",
            "plesk-ssh-terminal.service",
            "plesk-task-manager.service",
            "plesk-web-socket.service",
            "psa.service",
            "sw-collectd.service",
            "sw-cp-server.service",
            "sw-engine.service",
        ]
        self.plesk_systemd_services = [service for service in plesk_known_systemd_services if systemd.is_service_exists(service)]

        # Oneshot services are special, so they shouldn't be started on revert or after conversion, just enabled
        self.oneshot_services = [
            "plesk-ip-remapping.service",
        ]

        # We don't remove postfix service when remove it during qmail installation
        # so we should choose the right smtp service, otherwise they will conflict
        if systemd.is_service_exists("qmail.service"):
            self.plesk_systemd_services.append("qmail.service")
        elif systemd.is_service_exists("postfix.service"):
            self.plesk_systemd_services.append("postfix.service")

    def _prepare_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/bin/systemctl", "stop"] + self.plesk_systemd_services)
        util.logged_check_call(["/usr/bin/systemctl", "disable"] + self.plesk_systemd_services + self.oneshot_services)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/bin/systemctl", "enable"] + self.plesk_systemd_services + self.oneshot_services)
        # Don't do startup because the services will be started up after reboot at the end of the script anyway.
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/bin/systemctl", "enable"] + self.plesk_systemd_services + self.oneshot_services)
        util.logged_check_call(["/usr/bin/systemctl", "start"] + self.plesk_systemd_services)
        return action.ActionResult()

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        return 5

    def estimate_revert_time(self):
        return 10


class StartPleskBasicServices(action.ActiveAction):

    def __init__(self):
        self.name = "starting plesk services"
        self.plesk_basic_services = [
            "mariadb.service",
            "mysqld.service",
            "plesk-task-manager.service",
            "plesk-web-socket.service",
            "sw-cp-server.service",
            "sw-engine.service",
        ]
        self.plesk_basic_services = [service for service in self.plesk_basic_services if systemd.is_service_exists(service)]

    def _enable_services(self) -> action.ActionResult:
        # MariaDB could be started before, so we should stop it first
        # TODO. Or we could check it is started and just remove it from list
        util.logged_check_call(["/usr/bin/systemctl", "stop", "mariadb.service"])

        util.logged_check_call(["/usr/bin/systemctl", "enable"] + self.plesk_basic_services)
        util.logged_check_call(["/usr/bin/systemctl", "start"] + self.plesk_basic_services)
        return action.ActionResult()

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        self._enable_services()
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        self._enable_services()
        return action.ActionResult()
