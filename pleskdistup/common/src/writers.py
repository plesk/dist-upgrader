# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import codecs
import os


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


class StdoutEncodingReplaceWriter(Writer):
    encoding_errors_met: bool

    def __init__(self):
        self.out = open(1, 'w', closefd=False, errors='backslashreplace')
        self.encoding_errors_met = False

    def write(self, message: str) -> None:
        self.out.write(message)
        self.out.flush()

        recoded_message = codecs.encode(message, self.out.encoding, errors='replace').decode(self.out.encoding)
        if recoded_message != message:
            self.encoding_errors_met = True

    def has_encoding_errors(self) -> bool:
        return self.encoding_errors_met

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
