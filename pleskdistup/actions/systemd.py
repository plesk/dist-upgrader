# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import os
import typing

from pleskdistup.common import action, log, systemd, util


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
    ) -> None:
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
        if systemd.is_service_exists(self.service_name):
            log.debug(f"Enable systemd '{self.service_name}' service")
            systemd.enable_services([self.service_name])
            return action.ActionResult()

        log.debug(f"Create systemd '{self.service_name}' service")
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
        if systemd.is_service_exists(self.service_name):
            systemd.remove_systemd_service(self.service_name)
        return action.ActionResult()

    def _on_prepare_failure(self) -> action.ActionResult:
        if systemd.is_service_exists(self.service_name):
            log.debug(f"Disable systemd '{self.service_name}' service after conversion failure")
            systemd.disable_services([self.service_name])
        return action.ActionResult()

    def _should_be_repeated_if_succeeded(self) -> bool:
        # Don't forget to re-enable the service if we disabled it in the _on_prepare_failure method
        return True


class DisablePleskRelatedServicesDuringUpgrade(action.ActiveAction):
    plesk_systemd_services: typing.List[str]
    oneshot_services: typing.List[str]

    def __init__(self) -> None:
        self.name = "disable plesk related services"
        # Be cautious when adding the mailman service here. If mailman is not configured, the service will not start.
        # The best way to handle mailman is to use the DisableServiceDuringUpgrade action.
        plesk_known_systemd_services = [
            "crond.service",
            "dovecot.service",
            "drwebd.service",
            "fail2ban.service",
            "httpd.service",
            "mariadb.service",
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
        self.plesk_systemd_services = [
            service for service in plesk_known_systemd_services if systemd.is_service_startable(service)
        ]

        # Oneshot services are special, so they shouldn't be started on revert or after conversion, just enabled
        self.oneshot_services = [
            "plesk-ip-remapping.service",
        ]

        # Once MariaDB has started, systemctl will not be able to control mysqld as a linked unit.
        # Therefore, we should manage mysqld separately and only if MariaDB is not present
        if "mariadb.service" not in self.plesk_systemd_services and systemd.is_service_startable("mysqld.service"):
            self.plesk_systemd_services.append("mysqld.service")

        # We don't remove postfix service when remove it during qmail installation
        # so we should choose the right smtp service, otherwise they will conflict
        if systemd.is_service_startable("qmail.service"):
            self.plesk_systemd_services.append("qmail.service")
        elif systemd.is_service_startable("postfix.service"):
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

    def estimate_prepare_time(self) -> int:
        return 10

    def estimate_post_time(self) -> int:
        return 5

    def estimate_revert_time(self) -> int:
        return 10


class HandlePleskFirewallService(action.ActiveAction):
    plesk_firewall_service: str

    def __init__(self) -> None:
        self.name = "handle plesk-firewall service"
        self.plesk_firewall_service = "plesk-firewall.service"

    def _is_required(self) -> bool:
        return systemd.is_service_startable(self.plesk_firewall_service) and systemd.is_service_active(self.plesk_firewall_service)

    def _prepare_action(self) -> action.ActionResult:
        # We avoid handling Plesk Firewall and Firewalld services during the preparation stage because
        # we will not be able to restart them during the revert stage without causing a loss of network connection
        # If we lose the connection, the revert process will be interrupted, which is undesirable.
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        # The firewalld service conflicts with the plesk-firewall service, so we need to ensure
        # that it does not start on the target system
        if systemd.is_service_exists("firewalld.service"):
            util.logged_check_call(["/usr/bin/systemctl", "stop", "firewalld.service"])
            util.logged_check_call(["/usr/bin/systemctl", "disable", "firewalld.service"])

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class DisableServiceDuringUpgrade(action.ActiveAction):
    target_service: str

    def __init__(self, target_service: str) -> None:
        self.name = f"handle {target_service} service"
        self.target_service = target_service

    def _is_required(self) -> bool:
        return systemd.is_service_startable(self.target_service) and systemd.is_service_active(self.target_service)

    def _prepare_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/bin/systemctl", "stop", self.target_service])
        util.logged_check_call(["/usr/bin/systemctl", "disable", self.target_service])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/bin/systemctl", "enable", self.target_service])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/bin/systemctl", "enable", self.target_service])
        util.logged_check_call(["/usr/bin/systemctl", "start", self.target_service])
        return action.ActionResult()


class StartPleskBasicServices(action.ActiveAction):
    plesk_basic_services: typing.List[str]

    def __init__(self) -> None:
        self.name = "starting plesk services"
        self.plesk_basic_services = [
            "mariadb.service",
            "plesk-task-manager.service",
            "plesk-web-socket.service",
            "sw-cp-server.service",
            "sw-engine.service",
        ]
        self.plesk_basic_services = [service for service in self.plesk_basic_services if systemd.is_service_exists(service)]

        # Once MariaDB has started, systemctl will not be able to control mysqld as a linked unit.
        # Therefore, we should manage mysqld separately and only if MariaDB is not present
        if "mariadb.service" not in self.plesk_basic_services and systemd.is_service_startable("mysqld.service"):
            self.plesk_basic_services.append("mysqld.service")

    def _enable_services(self) -> action.ActionResult:
        # MariaDB could be started before, so we should stop it first
        # TODO. Or we could check it is started and just remove it from list
        if systemd.is_service_exists("mariadb.service"):
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
