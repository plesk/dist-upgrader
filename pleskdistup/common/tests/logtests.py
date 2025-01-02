# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import os
import unittest

import src.log as log


class TestLog(unittest.TestCase):
    DEFAULT_LOG_STORE = "test.log"

    def setUp(self) -> None:
        log.logger.init_logger([self.DEFAULT_LOG_STORE], [], console=False)

    def tearDown(self) -> None:
        if os.path.exists(self.DEFAULT_LOG_STORE):
            os.unlink(self.DEFAULT_LOG_STORE)

    def test_error_log(self):
        log.err("Test message")
        self.assertTrue(os.path.exists(self.DEFAULT_LOG_STORE))
        with open(self.DEFAULT_LOG_STORE, "r") as log_file:
            self.assertTrue("Test message" in log_file.read())

    def test_no_debug_by_default(self):
        log.debug("Test message")
        self.assertTrue(os.path.exists(self.DEFAULT_LOG_STORE))
        with open(self.DEFAULT_LOG_STORE, "r") as log_file:
            self.assertEqual("", log_file.read())

    def test_debug_log(self):
        log.init_logger([self.DEFAULT_LOG_STORE], [], console=False, loglevel=log.logging.DEBUG)
        log.debug("Test message")
        self.assertTrue(os.path.exists(self.DEFAULT_LOG_STORE))
        with open(self.DEFAULT_LOG_STORE, "r") as log_file:
            self.assertTrue("Test message" in log_file.read())

    def test_write_bad_encoded(self):
        # To trigger an exception, we need to set the locale to a non-utf8 one
        # but we can't be sure what locale will be installed on the test machine
        # So it looks like it is enough to make sure message was re-decoded before
        # writing to the log file by checking logfile content.
        log.init_logger([self.DEFAULT_LOG_STORE], [], console=False, encoding='ascii')
        log.err("Test message ü")
        self.assertTrue(os.path.exists(self.DEFAULT_LOG_STORE))
        with open(self.DEFAULT_LOG_STORE, "r") as log_file:
            self.assertTrue("Test message \\xfc" in log_file.read())
