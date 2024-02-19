# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import subprocess
import unittest
from unittest import mock

from pleskdistup.actions.common_checks import (
    AssertMinFreeDiskSpace,
    MinFreeDiskSpaceViolation,
    check_min_free_disk_space,
)


class FindmntMock:
    def __init__(self, args, results):
        self.args = args
        self.results = results

    def __call__(self, cmd, *args, **kwargs):
        target = cmd[-1]
        out = """
{{
   "filesystems": [
      {{
         "source": "{source}",
         "target": "{target}",
         "avail": {avail}
      }}
   ]
}}
""".format(**self.results[target])
        return subprocess.CompletedProcess(
            args=self.args,
            returncode=0,
            stdout=out,
            stderr="",
        )


class TestCheckMinFreeDiskSpace(unittest.TestCase):
    _requirements = {
        # Space requirements in bytes
        "/boot": 150 * 1024**2,
        "/opt": 150 * 1024**2,
        "/usr": 1800 * 1024**2,
        "/var": 2000 * 1024**2,
    }
    _findmnt_cmd = [
        "/bin/findmnt", "--output", "source,target,avail",
        "--bytes", "--json", "-T",
    ]

    def _get_expected_calls(self, paths):
        return [
            mock.call(
                self._findmnt_cmd + [path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                universal_newlines=True,
            ) for path in paths
        ]

    def setUp(self):
        self.maxDiff = None

    def test_no_violations(self):
        req_sum = sum(
            self._requirements[k] for k in ("/boot", "/opt", "/usr")
        )
        findmnt_results = {
            "/boot": {"source": "/dev/sda1", "target": "/", "avail": req_sum},
            "/opt": {"source": "/dev/sda1", "target": "/", "avail": req_sum},
            "/usr": {"source": "/dev/sda1", "target": "/", "avail": req_sum},
            "/var": {"source": "/dev/sdb1", "target": "/var", "avail": self._requirements["/var"]},
        }
        with mock.patch(
            'subprocess.run',
            side_effect=FindmntMock(self._findmnt_cmd, findmnt_results),
        ) as run_mock:
            violations = check_min_free_disk_space(self._requirements)
            self.assertEqual(violations, [])
            self.assertListEqual(
                run_mock.mock_calls,
                self._get_expected_calls(self._requirements),
            )

    def test_violations(self):
        # Insufficient space on /dev/sda1, /dev/sda2
        dev_avail = {
            "/dev/sda1": self._requirements["/boot"] + self._requirements["/opt"] - 1,
            "/dev/sda2": self._requirements["/usr"] - 1,
            "/dev/sda3": self._requirements["/var"],
        }
        findmnt_results = {
            "/boot": {"source": "/dev/sda1", "target": "/"},
            "/opt": {"source": "/dev/sda1", "target": "/"},
            "/usr": {"source": "/dev/sda2", "target": "/usr"},
            "/var": {"source": "/dev/sda3", "target": "/var"},
        }
        for path, fs_data in findmnt_results.items():
            fs_data["avail"] = dev_avail[fs_data["source"]]
        expected_violations = [
            MinFreeDiskSpaceViolation(
                "/dev/sda1",
                self._requirements["/boot"] + self._requirements["/opt"],
                dev_avail["/dev/sda1"],
                {"/boot", "/opt"}
            ),
            MinFreeDiskSpaceViolation(
                "/dev/sda2",
                self._requirements["/usr"],
                dev_avail["/dev/sda2"],
                {"/usr"}
            ),
        ]
        with mock.patch(
            'subprocess.run',
            side_effect=FindmntMock(self._findmnt_cmd, findmnt_results),
        ) as run_mock:
            violations = check_min_free_disk_space(self._requirements)
            self.assertListEqual(violations, expected_violations)
            self.assertListEqual(
                run_mock.mock_calls,
                self._get_expected_calls(self._requirements),
            )


class TestAssertMinFreeDiskSpace(unittest.TestCase):
    _requirements = {
        # Space requirements in bytes
        "/boot": 150 * 1024**2,
        "/opt": 150 * 1024**2,
        "/usr": 1800 * 1024**2,
        "/var": 2000 * 1024**2,
    }

    def setUp(self):
        self.maxDiff = None

    def test_description_pass(self):
        with mock.patch(
            'pleskdistup.actions.common_checks.check_min_free_disk_space',
            return_value=[],
        ) as check_min_free_disk_space_mock:
            assrt = AssertMinFreeDiskSpace(self._requirements)
            self.assertEqual(assrt.description, "")
            self.assertTrue(assrt.do_check())
            self.assertEqual(assrt.description, "")
            check_min_free_disk_space_mock.assert_called_once_with(self._requirements)

    def test_description_fail(self):
        # Insufficient space on /dev/sda1, /dev/sda2
        dev_avail = {
            "/dev/sda1": self._requirements["/boot"] + self._requirements["/opt"] - 1,
            "/dev/sda2": self._requirements["/usr"] - 1,
            "/dev/sda3": self._requirements["/var"],
        }
        violations = [
            MinFreeDiskSpaceViolation(
                "/dev/sda1",
                self._requirements["/boot"] + self._requirements["/opt"],
                dev_avail["/dev/sda1"],
                {"/boot", "/opt"}
            ),
            MinFreeDiskSpaceViolation(
                "/dev/sda2",
                self._requirements["/usr"],
                dev_avail["/dev/sda2"],
                {"/usr"}
            ),
        ]
        expected_description = "There's not enough free disk space: "
        expected_description += ", ".join(
            f"on filesystem {v.dev!r} for "
            f"{', '.join(repr(p) for p in sorted(v.paths))} "
            f"(need {v.req_bytes / 1024**2} MiB, "
            f"got {v.avail_bytes / 1024**2} MiB)" for v in violations
        )
        with mock.patch(
            'pleskdistup.actions.common_checks.check_min_free_disk_space',
            return_value=violations,
        ) as check_min_free_disk_space_mock:
            assrt = AssertMinFreeDiskSpace(self._requirements)
            self.assertEqual(assrt.description, "")
            self.assertFalse(assrt.do_check())
            self.assertEqual(assrt.description, expected_description)
            check_min_free_disk_space_mock.assert_called_once_with(self._requirements)
