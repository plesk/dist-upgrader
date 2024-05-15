# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import sys


class Writer():
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def write(self, message: str):
        raise NotImplementedError("Not implemented writer call")

    def __exit__(self, *args):
        pass


class StdoutWriter(Writer):
    def __init__(self):
        self.out = open(1, 'w', closefd=False)

    def write(self, message: str) -> None:
        self.out.write(message)
        self.out.flush()

    def __exit__(self, *args):
        self.out.close()


class FileWriter(Writer):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def __enter__(self):
        self.file = open(self.filename, "w")
        return self

    def write(self, message: str) -> None:
        self.file.write(message)
        self.file.flush()

    def __exit__(self, *args):
        self.file.close()
        os.unlink(self.filename)
