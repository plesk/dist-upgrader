import os
import unittest
import shutil

import src.systemd as systemd


class TestGetSystemdConfig(unittest.TestCase):
    TEST_DIRECTORY = "test_get_systemd_config"

    def setUp(self):
        if os.path.exists(self.TEST_DIRECTORY):
            shutil.rmtree(self.TEST_DIRECTORY)
        os.mkdir(self.TEST_DIRECTORY)

    def tearDown(self):
        if os.path.exists(self.TEST_DIRECTORY):
            shutil.rmtree(self.TEST_DIRECTORY)

    def test_get_systemd_config_existing_section_and_variable(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_existing_section_and_variable.conf")
        with open(path_to_config, "w") as f:
            f.write("[Section1]\nkey1=value1\n")

        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section1", "key1"),
            "value1",
        )

    def test_get_systemd_config_existing_section_new_variable(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_existing_section_new_variable.conf")
        with open(path_to_config, "w") as f:
            f.write("[Section1]\nkey1=value1\n")

        self.assertIsNone(
            systemd.get_systemd_config(path_to_config, "Section1", "key2"),
        )

    def test_get_systemd_config_new_section(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_new_section.conf")
        with open(path_to_config, "w") as f:
            f.write("[Section1]\nkey1=value1\n")

        self.assertIsNone(
            systemd.get_systemd_config(path_to_config, "Section2", "key1"),
        )


class TestInjectSystemdConfig(unittest.TestCase):

    TEST_DIRECTORY = "test_set_systemd_config"

    def setUp(self):
        if os.path.exists(self.TEST_DIRECTORY):
            shutil.rmtree(self.TEST_DIRECTORY)
        os.mkdir(self.TEST_DIRECTORY)

    def tearDown(self):
        if os.path.exists(self.TEST_DIRECTORY):
            shutil.rmtree(self.TEST_DIRECTORY)

    def test_inject_systemd_config_existing_section_and_variable(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_existing_section_and_variable.conf")
        with open(path_to_config, "w") as f:
            f.write("[Section1]\nkey1=value1\n")

        section = "Section1"
        variable = "key1"
        value = "new_value"

        systemd.inject_systemd_config(path_to_config, section, variable, value)

        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section1", "key1"),
            "new_value",
        )

    def test_inject_systemd_config_existing_section_new_variable(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_existing_section_new_variable.conf")
        with open(path_to_config, "w") as f:
            f.write("[Section1]\nkey1=value1\n")

        section = "Section1"
        variable = "key2"
        value = "value2"

        systemd.inject_systemd_config(path_to_config, section, variable, value)

        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section1", "key1"),
            "value1",
        )
        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section1", "key2"),
            "value2",
        )

    def test_inject_systemd_config_new_section(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_new_section.conf")
        with open(path_to_config, "w") as f:
            f.write("[Section1]\nkey1=value1\n")

        section = "Section2"
        variable = "key1"
        value = "value1"

        systemd.inject_systemd_config(path_to_config, section, variable, value)

        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section2", "key1"),
            "value1",
        )

    def test_inject_systemd_config_variable_into_middle(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_variable_into_middle.conf")
        with open(path_to_config, "w") as f:
            f.write("[Section1]\nkey1=value1\nkey2=value2\n[Section2]\nkey3=value3\n[Section3]\nkey4=value4\n")

        section = "Section2"
        variable = "key_new"
        value = "value_new"

        systemd.inject_systemd_config(path_to_config, section, variable, value)

        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section2", "key_new"),
            "value_new",
        )

    def test_inject_systemd_config_variable_intersection(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_variable_intersection.conf")
        with open(path_to_config, "w") as f:
            f.write("[Section1]\nkey1=value1\n[Section2]\nkey1=old_value\n")

        section = "Section2"
        variable = "key1"
        value = "new_value"

        systemd.inject_systemd_config(path_to_config, section, variable, value)

        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section2", "key1"),
            "new_value",
        )
        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section1", "key1"),
            "value1",
        )

    def test_inject_systemd_config_file_not_exists(self):
        path_to_config = os.path.join(self.TEST_DIRECTORY, "test_config_file_not_exists.conf")

        section = "Section1"
        variable = "key1"
        value = "value1"

        systemd.inject_systemd_config(path_to_config, section, variable, value)

        self.assertEqual(
            systemd.get_systemd_config(path_to_config, "Section1", "key1"),
            "value1",
        )
