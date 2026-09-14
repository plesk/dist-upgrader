# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import datetime
import os
import re
import unittest
import unittest.mock as mock
import zipfile

from src import feedback, log


class TestFeedback(unittest.TestCase):

    TARGET_FEEDBACK = "test_feedback.zip"

    def tearDown(self) -> None:
        if os.path.exists(self.TARGET_FEEDBACK):
            os.unlink(self.TARGET_FEEDBACK)

    def test_version_file_contains_required_data(self):
        test_feedback = feedback.Feedback("tests", "1.0.0-rev1", "TestUpgrader", "1.0.0-rev1")
        test_feedback.prepare()

        required_data = {
            "The 'tests' utility version: 1.0.0-rev1": False,
            "Upgrader 'TestUpgrader' version: 1.0.0-rev1": False,
            "Distribution information: ": False,
            "Kernel information: ": False,
            "PostgreSQL": False,
        }

        with open("versions.txt", "r") as versions_file:
            for line in versions_file:
                log.debug(f"Looking at {line!r} in {versions_file!r}")
                for key in required_data.keys():
                    if key in line:
                        required_data[key] = True

        for key, value in required_data.items():
            self.assertTrue(value, f"Required data '{key}' is not found in versions.txt")

    def test_create_simple_feedback(self):
        test_feedback = feedback.Feedback("tests", "1.0.0-rev1", "TestUpgrader", "1.0.0-rev1")
        test_feedback.prepare()
        test_feedback.save_archive(self.TARGET_FEEDBACK)
        self.assertTrue(os.path.exists(self.TARGET_FEEDBACK))

        with zipfile.ZipFile(self.TARGET_FEEDBACK, "r") as zip_file:
            self.assertEqual(zip_file.namelist(), ["versions.txt"])

    def test_create_feedback_with_attached_files(self):
        with open("testfile", "w") as testfile:
            testfile.write("test")

        test_feedback = feedback.Feedback("tests", "1.0.0-rev1", "TestUpgrader", "1.0.0-rev1", attached_files=["testfile"])
        test_feedback.prepare()
        test_feedback.save_archive(self.TARGET_FEEDBACK)
        self.assertTrue(os.path.exists(self.TARGET_FEEDBACK))

        with zipfile.ZipFile(self.TARGET_FEEDBACK, "r") as zip_file:
            self.assertTrue("testfile" in zip_file.namelist())
            self.assertTrue("versions.txt" in zip_file.namelist())

    def test_create_feedback_with_collected_data(self):
        def collect_data():
            with open("testfile", "w") as testfile:
                testfile.write("test")
            return ["testfile"]

        test_feedback = feedback.Feedback("tests", "1.0.0-rev1", "TestUpgrader", "1.0.0-rev1", collect_actions=[collect_data])
        test_feedback.prepare()
        test_feedback.save_archive(self.TARGET_FEEDBACK)
        self.assertTrue(os.path.exists(self.TARGET_FEEDBACK))

        with zipfile.ZipFile(self.TARGET_FEEDBACK, "r") as zip_file:
            self.assertTrue("testfile" in zip_file.namelist())
            self.assertTrue("versions.txt" in zip_file.namelist())

    @staticmethod
    def _read_versions_file(*args, **kwargs) -> str:
        test_feedback = feedback.Feedback("tests", "1.0.0-rev1", "TestUpgrader", "1.0.0-rev1")
        test_feedback.prepare()
        with open("versions.txt", "r") as versions_file:
            return versions_file.read()

    @mock.patch("src.postgres.is_postgres_installed", return_value=False)
    def test_version_file_postgres_not_installed(self, _mock_installed):
        content = self._read_versions_file()
        self.assertIn("PostgreSQL is not installed", content)

    @mock.patch("src.postgres.get_postgres_major_version", return_value=15)
    @mock.patch("src.postgres.is_postgres_installed", return_value=True)
    def test_version_file_postgres_version(self, _mock_installed, _mock_version):
        content = self._read_versions_file()
        self.assertIn("PostgreSQL version: 15", content)

    @mock.patch("src.postgres.get_postgres_major_version", side_effect=Exception("boom"))
    @mock.patch("src.postgres.is_postgres_installed", return_value=True)
    def test_version_file_postgres_version_unknown(self, _mock_installed, _mock_version):
        content = self._read_versions_file()
        self.assertIn("PostgreSQL version: unknown", content)
        # A failed PostgreSQL probe must not drop the other version lines (PGV-5/PGV-6).
        self.assertIn("The 'tests' utility version: 1.0.0-rev1", content)
        self.assertIn("Upgrader 'TestUpgrader' version: 1.0.0-rev1", content)
        self.assertIn("Distribution information: ", content)
        self.assertIn("Kernel information: ", content)


class TestGetArchiveName(unittest.TestCase):

    ARCHIVE_NAME_REGEX = re.compile(r"^(?P<util>.+)_feedback_(?P<timestamp>\d{8}-\d{6})\.zip$")

    def test_name_shape_keeps_the_utility_name(self):
        for util_name in ("centos2alma", "ubuntu20to22", "some-util.with.dots"):
            name = feedback.get_archive_name(util_name)
            match = self.ARCHIVE_NAME_REGEX.match(name)
            self.assertIsNotNone(match, f"The feedback archive name {name!r} does not have the expected shape")
            self.assertEqual(match.group("util"), util_name)

    def test_timestamp_is_local_time(self):
        before = datetime.datetime.now().replace(microsecond=0)
        match = self.ARCHIVE_NAME_REGEX.match(feedback.get_archive_name("tests"))
        after = datetime.datetime.now()

        # Parsed back as a naive local timestamp: a UTC one would fall outside the window on any
        # host that is not on UTC, which is what pins the format to local time.
        stamp = datetime.datetime.strptime(match.group("timestamp"), "%Y%m%d-%H%M%S")
        self.assertGreaterEqual(stamp, before)
        self.assertLessEqual(stamp, after)
