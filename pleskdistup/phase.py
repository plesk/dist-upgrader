# Copyright 1999-2023. Plesk International GmbH. All rights reserved.

import enum


class Phase(enum.Enum):
    CONVERT = "convert"
    FINISH = "finish"
    REVERT = "revert"
    TEST = "test"

    @classmethod
    def from_str(cls, value: str):
        if value == "start":
            value = "convert"
        return cls(value)
