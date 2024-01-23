# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import typing

import pleskdistup.upgrader


class BasicSystemDescription(pleskdistup.upgrader.SystemDescription):
    def __init__(self, os_name: typing.Optional[str], os_version: typing.Optional[str]):
        super().__init__()
        self._os_name = os_name
        self._os_version = os_version

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(os_name={self.os_name!r}, os_version={self.os_version!r})"

    @property
    def os_name(self) -> typing.Optional[str]:
        return self._os_name

    @property
    def os_version(self) -> typing.Optional[str]:
        return self._os_version
