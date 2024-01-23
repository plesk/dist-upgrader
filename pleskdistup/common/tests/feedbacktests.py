# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import unittest
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
