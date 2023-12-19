# Copyright 1999-2023. Plesk International GmbH. All rights reserved.

import unittest

from src import log


class TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        log.debug(f"Running the test case {cls.__name__}")
