# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import unittest

from src import log


class TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        log.debug(f"Running the test case {cls.__name__}")
