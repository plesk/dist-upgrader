# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import unittest
import os
import shutil

import src.rpm as rpm


class RemoveRepositoriesTests(unittest.TestCase):
    REPO_FILE_CONTENT = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

    REPO_FILE_NAME = "repo_file.txt"

    def setUp(self):
        with open(self.REPO_FILE_NAME, "w") as f:
            f.write(self.REPO_FILE_CONTENT)

    def tearDown(self):
        if os.path.exists(self.REPO_FILE_NAME):
            os.remove(self.REPO_FILE_NAME)

    def test_remove_first_repo(self):
        expected_content = """[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3, _4: id == "repo1"])

        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_multiple_repos(self):
        expected_content = """[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3, _4: id == "repo1",
                                                      lambda id, _1, _2, _3, _4: id == "repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_all_repos(self):
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3, _4: id == "repo1",
                                                      lambda id, _1, _2, _3, _4: id == "repo2",
                                                      lambda id, _1, _2, _3, _4: id == "repo3"])
        self.assertEqual(os.path.exists(self.REPO_FILE_NAME), False)

    def test_remove_non_existing_repo(self):
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3, _4: id == "repo4"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), self.REPO_FILE_CONTENT)

    def test_remove_last_repo(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0

"""

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3, _4: id == "repo3"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_with_metalink(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""
        additional_repo = """[metarepo]
name=metarepo
metalink=http://metarepo
enabled=1
gpgcheck=0
"""
        with open(self.REPO_FILE_NAME, "a") as f:
            f.write(additional_repo)

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda _1, _2, _3, metalink, _4: metalink == "http://metarepo"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_with_specific_name(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda _1, name, _2, _3, _4: name == "repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_with_specific_baseurl(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda _1, _2, baseurl, _3, _4: baseurl == "http://repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_by_id_or_url(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

"""
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, baseurl, _3, _4: id == "repo2" or baseurl == "http://repo3"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_by_mirrorlist(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""
        additional_repo = """[mirrorrepo]
name=mirrorrepo
mirrorlist=http://mirrorrepo
enabled=1
gpgcheck=0
"""
        with open(self.REPO_FILE_NAME, "a") as f:
            f.write(additional_repo)

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda _1, _2, _3, _4, mirrorlist: mirrorlist == "http://mirrorrepo"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)


class WriteRepodataTests(unittest.TestCase):
    REPO_FILE_CONTENT = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

"""

    REPO_FILE_NAME = "repo_file.txt"

    def setUp(self):
        with open(self.REPO_FILE_NAME, "w") as f:
            f.write(self.REPO_FILE_CONTENT)

    def tearDown(self):
        if os.path.exists(self.REPO_FILE_NAME):
            os.remove(self.REPO_FILE_NAME)

    def test_write_repodata(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0
"""
        rpm.write_repodata(self.REPO_FILE_NAME, "repo2", "repo2", "http://repo2", None, None, ["enabled=1\n", "gpgcheck=0\n"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    # Yeah, we don't check if reposiory is already in file. Maybe we will add the check in the future.
    def test_write_exsisted_repodata(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0
"""
        rpm.write_repodata(self.REPO_FILE_NAME, "repo1", "repo1", "http://repo1", None, None, ["enabled=1\n", "gpgcheck=0\n"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_write_repodata_with_metalink(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
metalink=http://repo2
enabled=1
gpgcheck=0
"""
        rpm.write_repodata(self.REPO_FILE_NAME, "repo2", "repo2", None, "http://repo2", None, ["enabled=1\n", "gpgcheck=0\n"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_write_repodata_with_mirrorlist(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
mirrorlist=http://repo2
enabled=1
gpgcheck=0
"""
        rpm.write_repodata(self.REPO_FILE_NAME, "repo2", "repo2", None, None, "http://repo2", ["enabled=1\n", "gpgcheck=0\n"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)


class HandleRpmnewFilesTests(unittest.TestCase):
    test_dir: str = "rpm_test_dir"

    def tearDown(self):
        tests_related_files = ["test.txt", "test.txt.rpmnew", "test.txt.rpmsave"]
        for file in tests_related_files:
            if os.path.exists(file):
                os.remove(file)

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_no_rpmnew(self):
        with open("test.txt", "w") as f:
            f.write("test")

        self.assertFalse(rpm.handle_rpmnew("test.txt"))

    def test_has_rpmnew(self):
        with open("test.txt", "w") as f:
            f.write("1")

        with open("test.txt.rpmnew", "w") as f:
            f.write("2")

        self.assertTrue(rpm.handle_rpmnew("test.txt"))
        self.assertTrue(os.path.exists("test.txt"))
        self.assertEqual(open("test.txt").read(), "2")

        self.assertTrue(os.path.exists("test.txt.rpmsave"))
        self.assertEqual(open("test.txt.rpmsave").read(), "1")

    def test_missing_original(self):
        with open("test.txt.rpmnew", "w") as f:
            f.write("2")

        self.assertTrue(rpm.handle_rpmnew("test.txt"))
        self.assertTrue(os.path.exists("test.txt"))
        self.assertEqual(open("test.txt").read(), "2")

        self.assertFalse(os.path.exists("test.txt.rpmsave"))

    def test_handle_whole_directory(self):
        os.mkdir(self.test_dir)

        original_files = {
            "test1.txt": "1",
            "test1.txt.rpmnew": "2",
            "test2.txt": "3",
            "test2.txt.rpmnew": "4",
            "test3.txt": "5",
            "test4.txt.rpmnew": "6"
        }

        expected_files = {
            "test1.txt": "2",
            "test2.txt": "4",
            "test3.txt": "5",
            "test4.txt": "6"
        }

        for file, content in original_files.items():
            with open(os.path.join(self.test_dir, file), "w") as f:
                f.write(content)

        result = rpm.handle_all_rpmnew_files(self.test_dir)

        for file, content in expected_files.items():
            full_filepath = os.path.join(self.test_dir, file)
            # since test3.txt was not substituted, it should not be in the result
            if file != "test3.txt":
                self.assertTrue(full_filepath in result)
            else:
                self.assertFalse(full_filepath in result)

            self.assertTrue(os.path.exists(full_filepath))
            self.assertEqual(open(full_filepath).read(), content)

        shutil.rmtree(self.test_dir)


class repositoryHasNoneLinkTest(unittest.TestCase):
    def test_no_link(self):
        self.assertFalse(rpm.repository_has_none_link(None, None, None, None, None))

    def test_url(self):
        self.assertTrue(rpm.repository_has_none_link("id", "name", "none", None, None))

    def test_metalink(self):
        self.assertTrue(rpm.repository_has_none_link("id", "name", None, "none", None))

    def test_mirrorlist(self):
        self.assertTrue(rpm.repository_has_none_link("id", "name", None, None, "none"))

    def test_all(self):
        self.assertTrue(rpm.repository_has_none_link("id", "name", "none", "none", "none"))

    def test_links_are_fine(self):
        self.assertFalse(rpm.repository_has_none_link("id", "name", "url", "metalink", "mirrorlist"))
