# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import typing

from pleskdistup.common import dist
from pleskdistup.upgrader import DistUpgraderFactory


_upgraders: typing.List[DistUpgraderFactory] = []


def register_upgrader(upgrader: DistUpgraderFactory) -> None:
    _upgraders.append(upgrader)


def unregister_upgrader(upgrader: DistUpgraderFactory) -> None:
    _upgraders.remove(upgrader)


def iter_upgraders(
    from_system: typing.Optional[dist.Distro] = None,
    to_system: typing.Optional[dist.Distro] = None,
    upgrader_name: typing.Optional[str] = None,
) -> typing.Generator[DistUpgraderFactory, None, None]:
    for u in _upgraders:
        if (
            u.supports(from_system, to_system)
            and (upgrader_name is None or upgrader_name == u.upgrader_name)
        ):
            yield u
