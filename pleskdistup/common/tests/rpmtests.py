# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
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

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.id == "repo1"])

        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_multiple_repos(self):
        expected_content = """[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.id == "repo1",
                                                      lambda repo: repo.id == "repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_all_repos(self):
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.id == "repo1",
                                                      lambda repo: repo.id == "repo2",
                                                      lambda repo: repo.id == "repo3"])
        self.assertEqual(os.path.exists(self.REPO_FILE_NAME), False)

    def test_remove_non_existing_repo(self):
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.id == "repo4"])
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

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.id == "repo3"])
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

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.metalink == "http://metarepo"])
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
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.name == "repo2"])
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
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.url == "http://repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_by_id_or_url(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

"""
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.id == "repo2" or repo.url == "http://repo3"])
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

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda repo: repo.mirrorlist == "http://mirrorrepo"])
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
        rpm.write_repodata(self.REPO_FILE_NAME,  rpm.Repository("repo2", "repo2", "http://repo2", None, None, ["enabled=1\n", "gpgcheck=0\n"]))
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
        rpm.write_repodata(self.REPO_FILE_NAME, rpm.Repository("repo1", "repo1", "http://repo1", None, None, ["enabled=1\n", "gpgcheck=0\n"]))
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
        rpm.write_repodata(self.REPO_FILE_NAME, rpm.Repository("repo2", "repo2", None, "http://repo2", None, ["enabled=1\n", "gpgcheck=0\n"]))
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
        rpm.write_repodata(self.REPO_FILE_NAME, rpm.Repository("repo2", "repo2", None, None, "http://repo2", ["enabled=1\n", "gpgcheck=0\n"]))
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_write_repodata_with_all_links(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo2
metalink=http://repo2
mirrorlist=http://repo2
enabled=1
gpgcheck=0
"""

        rpm.write_repodata(self.REPO_FILE_NAME, rpm.Repository("repo2", "repo2", "http://repo2", "http://repo2", "http://repo2", ["enabled=1\n", "gpgcheck=0\n"]))
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
        self.assertFalse(rpm.repository_has_none_link(rpm.Repository(None, None, None, None, None)))

    def test_url(self):
        self.assertTrue(rpm.repository_has_none_link(rpm.Repository("id", "name", "none", None, None)))

    def test_metalink(self):
        self.assertTrue(rpm.repository_has_none_link(rpm.Repository("id", "name", None, "none", None)))

    def test_mirrorlist(self):
        self.assertTrue(rpm.repository_has_none_link(rpm.Repository("id", "name", None, None, "none")))

    def test_all(self):
        self.assertTrue(rpm.repository_has_none_link(rpm.Repository("id", "name", "none", "none", "none")))

    def test_links_are_fine(self):
        self.assertFalse(rpm.repository_has_none_link(rpm.Repository("id", "name", "url", "metalink", "mirrorlist")))


class repositorySourceIsIp(unittest.TestCase):
    def test_no_links(self):
        self.assertFalse(rpm.repository_source_is_ip(rpm.Repository("id", "name", None, None, None)))

    def test_url_is_ip(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", "name", "https://192.168.0.1/repo", None, None)))

    def test_metalink_is_ip(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", "name", None, "https://192.168.0.1/repo", None)))

    def test_mirrorlist_is_ip(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", "name", None, None, "https://192.168.0.1/repo")))

    def test_all_are_fine(self):
        self.assertFalse(rpm.repository_source_is_ip(rpm.Repository("id", "name", "https://my.repo/repo", "https://my.repo/repo", "https://my.repo/repo")))

    def test_ipv6_address(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", "name", "https://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]/repo", None, None)))

    def test_url_is_ip_with_port(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", "name", "https://192.168.0.1:8080/repo", None, None)))

    def test_url_is_ip_with_credentials(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", "name", "https://user:pass@192.168.0.1:8080/repo", None, None)))

    def test_url_is_not_ip_but_ip_in_path(self):
        self.assertFalse(rpm.repository_source_is_ip(rpm.Repository("id", "name", "https://my.repo/repo/192.168.0.1/target", None, None)))

    def test_non_url_string(self):
        self.assertFalse(rpm.repository_source_is_ip(rpm.Repository("id", "name", "Just a random string", None, None)))


class RepositoryTests(unittest.TestCase):
    def test_from_lines(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, "http://metalink")
        self.assertEqual(repo.mirrorlist, "http://mirrorlist")
        self.assertEqual(repo.additional, ["enabled=1\n", "gpgcheck=0\n"])

    def test_from_lines_no_id(self):
        lines = [
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        with self.assertRaises(ValueError):
            rpm.Repository.from_lines(lines)

    def test_from_lines_no_name(self):
        lines = [
            "[repo1]\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, None)
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, "http://metalink")
        self.assertEqual(repo.mirrorlist, "http://mirrorlist")
        self.assertEqual(repo.additional, ["enabled=1\n", "gpgcheck=0\n"])

    def test_from_lines_no_baseurl(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, None)
        self.assertEqual(repo.metalink, "http://metalink")
        self.assertEqual(repo.mirrorlist, "http://mirrorlist")
        self.assertEqual(repo.additional, ["enabled=1\n", "gpgcheck=0\n"])

    def test_from_lines_no_metalink(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, None)
        self.assertEqual(repo.mirrorlist, "http://mirrorlist")
        self.assertEqual(repo.additional, ["enabled=1\n", "gpgcheck=0\n"])

    def test_from_lines_no_mirrorlist(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "metalink=http://metalink\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, "http://metalink")
        self.assertEqual(repo.mirrorlist, None)
        self.assertEqual(repo.additional, ["enabled=1\n", "gpgcheck=0\n"])

    def test_from_lines_no_additional(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, "http://metalink")
        self.assertEqual(repo.mirrorlist, "http://mirrorlist")
        self.assertEqual(repo.additional, [])

    def test_multiline_additional(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "gpgkey=http://key1.com/key.gpg\n",
            "       http://key2.com/key.gpg\n",
            "       http://key3.com/key.gpg\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, None)
        self.assertEqual(repo.mirrorlist, None)
        self.assertEqual(repo.additional, ["enabled=1\n", "gpgcheck=0\n", "gpgkey=http://key1.com/key.gpg\n", "       http://key2.com/key.gpg\n", "       http://key3.com/key.gpg\n"])

    def test_with_commentary(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "#basecomment\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "#comment\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, "http://metalink")
        self.assertEqual(repo.mirrorlist, "http://mirrorlist")
        self.assertEqual(repo.additional, ["#basecomment\n", "enabled=1\n", "gpgcheck=0\n", "#comment\n"])
