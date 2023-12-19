# Copyright 1999-2023. Plesk International GmbH. All rights reserved.

import typing

from pleskdistup.phase import Phase


class ResumeData:
    phase: Phase
    argv: typing.List[str]
    upgrader_name: str
    stage: typing.Optional[str]
    _exported_attributes = (
        "phase",
        "argv",
        "upgrader_name",
        "stage"
    )

    def __init__(
        self,
        phase: Phase,
        argv: typing.Iterable[str],
        upgrader_name: str,
        stage: typing.Optional[str] = None,
    ):
        self.phase = phase
        self.argv = list(argv)
        self.upgrader_name = upgrader_name
        self.stage = stage

    @classmethod
    def from_dict(cls, dic: typing.Dict[str, typing.Any]):
        src = {k: v for k, v in dic.items() if k in cls._exported_attributes}
        if isinstance(src["phase"], str):
            src["phase"] = Phase.from_str(src["phase"])
        return cls(**src)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        res = {k: getattr(self, k) for k in self._exported_attributes}
        res["phase"] = str(res["phase"].value)
        return res

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"
