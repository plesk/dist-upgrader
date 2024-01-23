# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import os
import typing
from abc import ABC, abstractmethod

from pleskdistup.common import action, feedback
from pleskdistup.phase import Phase


PathType = typing.Union[os.PathLike, str]


class SystemDescription(ABC):
    @property
    @abstractmethod
    def os_name(self) -> typing.Optional[str]:
        pass

    @property
    @abstractmethod
    def os_version(self) -> typing.Optional[str]:
        pass


class DistUpgrader(ABC):
    # None as from_system or to_system is a wildcard meaning "any"
    @abstractmethod
    def supports(
        self,
        from_system: typing.Optional[SystemDescription] = None,
        to_system: typing.Optional[SystemDescription] = None,
    ) -> bool:
        pass

    # N. B.: upgrader name can be used to select the upgrader, so it
    # must be unique. It's recommended to prefix some namespace
    # identifier to prevent collisions, e.g. Plesk::Debian11to12Upgrader
    @property
    @abstractmethod
    def upgrader_name(self) -> str:
        pass

    @property
    @abstractmethod
    def upgrader_version(self) -> str:
        pass

    @property
    @abstractmethod
    def issues_url(self) -> typing.Optional[str]:
        pass

    @abstractmethod
    def prepare_feedback(
        self,
        feed: feedback.Feedback,
    ) -> feedback.Feedback:
        pass

    @abstractmethod
    def construct_actions(self, upgrader_bin_path: PathType, options: typing.Any, phase: Phase) -> typing.Dict[str, typing.List[action.ActiveAction]]:
        pass

    @abstractmethod
    def get_check_actions(self, options: typing.Any, phase: Phase) -> typing.List[action.CheckAction]:
        pass


class DistUpgraderFactory(ABC):
    @abstractmethod
    def supports(
        self,
        from_system: typing.Optional[SystemDescription] = None,
        to_system: typing.Optional[SystemDescription] = None,
    ) -> bool:
        pass

    # N. B.: upgrader name can be used to select the upgrader, so it
    # must be unique. It's recommended to prefix some namespace
    # identifier to prevent collisions, e.g. Plesk::Debian11to12Upgrader
    @property
    @abstractmethod
    def upgrader_name(self) -> str:
        pass

    @abstractmethod
    def create_upgrader(self, *args, **kwargs) -> DistUpgrader:
        pass
