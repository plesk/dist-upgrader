# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
from pleskdistup.common import action, systemd


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
