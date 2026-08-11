# Copyright 1999-2026. WebPros International GmbH. All rights reserved.

import unittest
import os

import src.packages as packages


class TestPackages(unittest.TestCase):
    TMP_CONF_FILE = 'packagestests_tmp.conf'

    def setUp(self):
        pass

    def tearDown(self):
        self._rm_conflict(self.TMP_CONF_FILE)

    def _create_conflict(self, filepath: str) -> str:
        _, new_ext = packages.get_package_conflict_file_extensions()
        p = filepath + new_ext
        with open(p, 'w') as f:
            f.write("test test")
        return p

    def _rm_conflict(self, filepath: str) -> None:
        _, new_ext = packages.get_package_conflict_file_extensions()
        if os.path.exists(filepath + new_ext):
            os.remove(filepath + new_ext)

    def test_exists(self):
        conflict = self._create_conflict(self.TMP_CONF_FILE)
        self.assertEqual(
            conflict,
            packages.get_conflict_file(self.TMP_CONF_FILE)
        )

    def test_not_exists(self):
        self._rm_conflict(self.TMP_CONF_FILE)
        self.assertFalse(
            bool(packages.get_conflict_file(self.TMP_CONF_FILE))
        )
