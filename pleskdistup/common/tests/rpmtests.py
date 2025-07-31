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
        rpm.write_repodata(self.REPO_FILE_NAME,  rpm.Repository("repo2", name="repo2", url="http://repo2", metalink=None, mirrorlist=None, enabled=1, gpgcheck=0))
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
        rpm.write_repodata(self.REPO_FILE_NAME, rpm.Repository("repo1", name="repo1", url="http://repo1", metalink=None, mirrorlist=None, enabled=1, gpgcheck=0))
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
        rpm.write_repodata(self.REPO_FILE_NAME, rpm.Repository("repo2", name="repo2", url=None, metalink="http://repo2", mirrorlist=None, enabled=1, gpgcheck=0))
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
        rpm.write_repodata(self.REPO_FILE_NAME, rpm.Repository("repo2", name="repo2", url=None, metalink=None, mirrorlist="http://repo2", enabled=1, gpgcheck=0))
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

        rpm.write_repodata(self.REPO_FILE_NAME, rpm.Repository("repo2", name="repo2", url="http://repo2", metalink="http://repo2", mirrorlist="http://repo2", enabled=1, gpgcheck=0))
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
        self.assertFalse(rpm.repository_has_none_link(rpm.Repository(None, name=None, url=None, metalink=None, mirrorlist=None)))

    def test_url(self):
        self.assertTrue(rpm.repository_has_none_link(rpm.Repository("id", name="name", url="none", metalink=None, mirrorlist=None)))

    def test_metalink(self):
        self.assertTrue(rpm.repository_has_none_link(rpm.Repository("id", name="name", url=None, metalink="none", mirrorlist=None)))

    def test_mirrorlist(self):
        self.assertTrue(rpm.repository_has_none_link(rpm.Repository("id", name="name", url=None, metalink=None, mirrorlist="none")))

    def test_all(self):
        self.assertTrue(rpm.repository_has_none_link(rpm.Repository("id", name="name", url="none", metalink="none", mirrorlist="none")))

    def test_links_are_fine(self):
        self.assertFalse(rpm.repository_has_none_link(rpm.Repository("id", name="name", url="url", metalink="metalink", mirrorlist="mirrorlist")))


class repositorySourceIsIp(unittest.TestCase):
    def test_no_links(self):
        self.assertFalse(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url=None, metalink=None, mirrorlist=None)))

    def test_url_is_ip(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url="https://192.168.0.1/repo", metalink=None, mirrorlist=None)))

    def test_metalink_is_ip(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url=None, metalink="https://192.168.0.1/repo", mirrorlist=None)))

    def test_mirrorlist_is_ip(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url=None, metalink=None, mirrorlist="https://192.168.0.1/repo")))

    def test_all_are_fine(self):
        self.assertFalse(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url="https://my.repo/repo", metalink="https://my.repo/repo", mirrorlist="https://my.repo/repo")))

    def test_ipv6_address(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url="https://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]/repo", metalink=None, mirrorlist=None)))

    def test_url_is_ip_with_port(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url="https://192.168.0.1:8080/repo", metalink=None, mirrorlist=None)))

    def test_url_is_ip_with_credentials(self):
        self.assertTrue(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url="https://user:pass@192.168.0.1:8080/repo", metalink=None, mirrorlist=None)))

    def test_url_is_not_ip_but_ip_in_path(self):
        self.assertFalse(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url="https://my.repo/repo/192.168.0.1/target", metalink=None, mirrorlist=None)))

    def test_non_url_string(self):
        self.assertFalse(rpm.repository_source_is_ip(rpm.Repository("id", name="name", url="Just a random string", metalink=None, mirrorlist=None)))


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
            "unknown=unknown\n",
            "something=else\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, "http://metalink")
        self.assertEqual(repo.mirrorlist, "http://mirrorlist")
        self.assertEqual(repo.enabled, "1")
        self.assertEqual(repo.gpgcheck, "0")
        self.assertEqual(repo.additional, ["unknown=unknown\n", "something=else\n",])

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
        self.assertEqual(repo.enabled, "1")
        self.assertEqual(repo.gpgcheck, "0")

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
        self.assertEqual(repo.enabled, "1")
        self.assertEqual(repo.gpgcheck, "0")

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
        self.assertEqual(repo.enabled, "1")
        self.assertEqual(repo.gpgcheck, "0")

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
        self.assertEqual(repo.enabled, "1")
        self.assertEqual(repo.gpgcheck, "0")

    def test_from_lines_no_enabled(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "gpgcheck=0\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.enabled, None)

    def test_from_lines_no_gpgcheck(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.gpgcheck, None)

    def test_from_lines_no_additional(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "metalink=http://metalink\n",
            "mirrorlist=http://mirrorlist\n",
            "enabled=1\n",
            "gpgcheck=0\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, "http://metalink")
        self.assertEqual(repo.mirrorlist, "http://mirrorlist")
        self.assertEqual(repo.enabled, "1")
        self.assertEqual(repo.gpgcheck, "0")
        self.assertEqual(repo.additional, [])

    def test_gpg_key(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "gpgkey=http://key1.com/key.gpg\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.gpgkeys, ["http://key1.com/key.gpg"])

    def test_multiline_gpg_key(self):
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

        self.assertEqual(repo.gpgkeys, ["http://key1.com/key.gpg", "http://key2.com/key.gpg", "http://key3.com/key.gpg"])

    def test_multiline_additional(self):
        lines = [
            "[repo1]\n",
            "name=repo1\n",
            "baseurl=http://repo1\n",
            "enabled=1\n",
            "gpgcheck=0\n",
            "multiline=http://key1.com/key.gpg\n",
            "       http://key2.com/key.gpg\n",
            "       http://key3.com/key.gpg\n",
        ]

        repo = rpm.Repository.from_lines(lines)

        self.assertEqual(repo.id, "repo1")
        self.assertEqual(repo.name, "repo1")
        self.assertEqual(repo.url, "http://repo1")
        self.assertEqual(repo.metalink, None)
        self.assertEqual(repo.mirrorlist, None)
        self.assertEqual(repo.additional, ["multiline=http://key1.com/key.gpg\n", "       http://key2.com/key.gpg\n", "       http://key3.com/key.gpg\n"])

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
        self.assertEqual(repo.additional, ["#basecomment\n", "#comment\n"])


class CollectAllGpgKeysFromRepofilesTests(unittest.TestCase):
    def setUp(self):
        if not os.path.exists("test_dir"):
            os.mkdir("test_dir")

    def tearDown(self):
        if os.path.exists("test_dir"):
            shutil.rmtree("test_dir")

    def test_no_repofiles(self):
        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["not_existing.repo"]), [])

    def test_invalid_file_format(self):
        with open("test_dir/invalid.repo", "w") as f:
            f.write("This is not a valid repo file")
        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["*.repo"]), [])

    def test_no_gpgkeys(self):
        with open("test_dir/repo1.repo", "w") as f:
            f.write("[repo1]\n"
                    "name=repo1\n"
                    "baseurl=http://repo1\n"
                    "enabled=1\n"
                    "gpgcheck=0\n")

        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["repo1.repo"]), [])

    def test_single_gpgkey(self):
        with open("test_dir/repo1.repo", "w") as f:
            f.write("[repo1]\n"
                    "name=repo1\n"
                    "baseurl=http://repo1\n"
                    "enabled=1\n"
                    "gpgcheck=0\n"
                    "gpgkey=http://key1.com/key.gpg\n")

        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["repo1.repo"]), ["http://key1.com/key.gpg"])

    def test_multiple_gpgkeys(self):
        with open("test_dir/repo1.repo", "w") as f:
            f.write("[repo1]\n"
                    "name=repo1\n"
                    "baseurl=http://repo1\n"
                    "enabled=1\n"
                    "gpgcheck=0\n"
                    "gpgkey=http://key1.com/key.gpg\n"
                    "       http://key2.com/key.gpg\n"
                    "       http://key3.com/key.gpg\n")

        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["repo1.repo"]), ["http://key1.com/key.gpg", "http://key2.com/key.gpg", "http://key3.com/key.gpg"])

    def test_multiple_repofiles(self):
        with open("test_dir/repo1.repo", "w") as f:
            f.write("[repo1]\n"
                    "name=repo1\n"
                    "baseurl=http://repo1\n"
                    "enabled=1\n"
                    "gpgcheck=0\n"
                    "gpgkey=http://key1.com/key.gpg\n")

        with open("test_dir/repo2.repo", "w") as f:
            f.write("[repo2]\n"
                    "name=repo2\n"
                    "baseurl=http://repo2\n"
                    "enabled=1\n"
                    "gpgcheck=0\n"
                    "gpgkey=http://key2.com/key.gpg\n")

        self.assertEqual(sorted(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["repo1.repo", "repo2.repo"])), ["http://key1.com/key.gpg", "http://key2.com/key.gpg"])

    def test_several_repo_in_file(self):
        with open("test_dir/repo1.repo", "w") as f:
            f.write("[repo1]\n"
                    "name=repo1\n"
                    "baseurl=http://repo1\n"
                    "enabled=1\n"
                    "gpgcheck=0\n"
                    "gpgkey=http://key1.com/key.gpg\n"
                    "[repo2]\n"
                    "name=repo2\n"
                    "baseurl=http://repo2\n"
                    "enabled=1\n"
                    "gpgcheck=0\n"
                    "gpgkey=http://key2.com/key.gpg\n")

        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["repo1.repo"]), ["http://key1.com/key.gpg", "http://key2.com/key.gpg"])

    def test_duplicate_gpg_keys(self):
        with open("test_dir/repo1.repo", "w") as f:
            f.write("[repo1]\n"
                    "name=repo1\n"
                    "gpgkey=http://key1.com/key.gpg\n")
        with open("test_dir/repo2.repo", "w") as f:
            f.write("[repo2]\n"
                    "name=repo2\n"
                    "gpgkey=http://key1.com/key.gpg\n")
        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["*.repo"]),
                         ["http://key1.com/key.gpg", "http://key1.com/key.gpg"])

    def test_space_separated_gpgkeys(self):
        with open("test_dir/repo1.repo", "w") as f:
            f.write("[repo1]\n"
                    "name=repo1\n"
                    "baseurl=http://repo1\n"
                    "enabled=1\n"
                    "gpgcheck=0\n"
                    "gpgkey=http://key1.com/key.gpg http://key2.com/key.gpg http://key3.com/key.gpg\n")

        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["repo1.repo"]),
                         ["http://key1.com/key.gpg", "http://key2.com/key.gpg", "http://key3.com/key.gpg"])

    def test_tabs_separated_gpgkeys(self):
        with open("test_dir/repo1.repo", "w") as f:
            f.write("[repo1]\n"
                    "name=repo1\n"
                    "baseurl=http://repo1\n"
                    "enabled=1\n"
                    "gpgcheck=0\n"
                    "gpgkey=http://key1.com/key.gpg\thttp://key2.com/key.gpg\thttp://key3.com/key.gpg\n")

        self.assertEqual(rpm.collect_all_gpgkeys_from_repofiles("test_dir", ["repo1.repo"]),
                         ["http://key1.com/key.gpg", "http://key2.com/key.gpg", "http://key3.com/key.gpg"])


class TestGetRPMRepositoriesUrls(unittest.TestCase):
    def tearDown(self):
        if os.path.exists("test.repo"):
            os.remove("test.repo")

    def test_no_config_file(self):
        self.assertEqual(rpm.get_repositories_urls("nonexistent.repo"), set())

    def test_simple_repository(self):
        with open("test.repo", "w") as test_file:
            test_file.write("""
[repo1]
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
""")
        self.assertEqual(rpm.get_repositories_urls("test.repo"), set(["http://repo1", "http://repo2", "http://repo3"]))

    def test_repository_with_comments(self):
        with open("test.repo", "w") as test_file:
            test_file.write("""
[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0
# This is a comment
#[repo2]
#name=repo2
#baseurl=http://repo2
#enabled=1
#gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
""")
        self.assertEqual(rpm.get_repositories_urls("test.repo"), set(["http://repo1", "http://repo3"]))

    def test_repository_with_spaces(self):
        with open("test.repo", "w") as test_file:
            test_file.write("""
[repo1]
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
""")
        self.assertEqual(rpm.get_repositories_urls("test.repo"), set(["http://repo1", "http://repo2", "http://repo3"]))

    def test_repository_with_same_url(self):
        with open("test.repo", "w") as test_file:
            test_file.write("""
[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo1
enabled=1
gpgcheck=0
""")
        self.assertEqual(rpm.get_repositories_urls("test.repo"), set(["http://repo1"]))


class TestGetRPMRepositoryMetafileUrl(unittest.TestCase):

    def test_simple_case(self):
        self.assertEqual(rpm.get_repository_metafile_url("http://repo1"), "http://repo1/repodata/repomd.xml")


class ExtractGpgkeyFromRpmDatabaseTests(unittest.TestCase):
    TEST_DIR = "test_rpm_database"

    def setUp(self):

        if not os.path.exists(self.TEST_DIR):
            os.mkdir(self.TEST_DIR)

    def tearDown(self):
        if os.path.exists(self.TEST_DIR):
            shutil.rmtree(self.TEST_DIR)

    def test_no_rpm_database(self):
        src_file = os.path.join(self.TEST_DIR, "non_existing.txt")
        dst_file = os.path.join(self.TEST_DIR, "non_existing_res.asc")

        self.assertFalse(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertFalse(os.path.exists(dst_file))

    def test_rpm_database_no_matches(self):
        src_file = os.path.join(self.TEST_DIR, "non_match.txt")
        dst_file = os.path.join(self.TEST_DIR, "non_match_res.asc")

        with open(src_file, "w") as f:
            f.write("This is not a valid rpm database file")

        self.assertFalse(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertFalse(os.path.exists(dst_file))

    def test_rpm_database_match_no_data(self):
        src_file = os.path.join(self.TEST_DIR, "valid_rpm_database.txt")
        dst_file = os.path.join(self.TEST_DIR, "valid_rpm_database_res.asc")

        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Version     : aaaaaaaa
Release     : ffffffff
Architecture: (none)
Install Date: Mon May 26 11:46:21 2025
Group       : Public Keys
Size        : 0
License     : pubkey
Signature   : (none)
Source RPM  : (none)
Build Date  : Wed Oct  7 10:49:04 2009
Build Host  : localhost
Relocations : (not relocatable)
Packager    : My Packager (My Key) <packager@my.com>
Summary     : gpg(mykey Packager (my Key) <packager@my.com>)
""")

        self.assertFalse(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertFalse(os.path.exists(dst_file))

    def test_rpm_database_match_with_data(self):
        src_file = os.path.join(self.TEST_DIR, "multyple_key_rpm_database.txt")
        dst_file = os.path.join(self.TEST_DIR, "multyple_key_rpm_database_res.asc")

        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Version     : aaaaaaaa
Release     : ffffffff
Architecture: (none)
Install Date: Mon May 26 11:46:21 2025
Group       : Public Keys
Size        : 0
License     : pubkey
Signature   : (none)
Source RPM  : (none)
Build Date  : Wed Oct  7 10:49:04 2009
Build Host  : localhost
Relocations : (not relocatable)
Packager    : My Packager (My Key) <packager@my.com>
Summary     : gpg(mykey Packager (my Key) <packager@my.com>)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)

qlqlqlwekqweoqwekpoqwpkeopqwkepoqkwpe
-----END PGP PUBLIC KEY BLOCK-----
""")
        self.assertTrue(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertTrue(os.path.exists(dst_file))

        with open(dst_file, "r") as f:
            content = f.read()
            self.assertIn("-----BEGIN PGP PUBLIC KEY BLOCK-----\n", content)
            self.assertIn("Version: rpm-4.11.3 (NSS-3)\n", content)
            self.assertIn("qlqlqlwekqweoqwekpoqwpkeopqwkepoqkwpe\n", content)
            self.assertIn("-----END PGP PUBLIC KEY BLOCK-----\n", content)

    def test_rpm_database_match_with_multiple_keys(self):
        src_file = os.path.join(self.TEST_DIR, "valid_rpm_database.txt")
        dst_file = os.path.join(self.TEST_DIR, "valid_rpm_database_res.asc")

        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Version     : aaaaaaaa
Release     : ffffffff
Architecture: (none)
Install Date: Mon May 26 11:46:21 2025
Group       : Public Keys
Size        : 0
License     : pubkey
Signature   : (none)
Source RPM  : (none)
Build Date  : Wed Oct  7 10:49:04 2009
Build Host  : localhost
Relocations : (not relocatable)
Packager    : My Packager (My Key) <packager@my.com>
Summary     : gpg(mykey Packager (my Key) <packager@my.com>)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)

qlqlqlwekqweoqwekpoqwpkeopqwkepoqkwpe
-----END PGP PUBLIC KEY BLOCK-----

Name        : gpg-pubkey
Version     : bbbbbbbb
Release     : cccccccc
Architecture: (none)
Install Date: Mon May 26 11:46:21 2025
Group       : Public Keys
Size        : 0
License     : pubkey
Signature   : (none)
Source RPM  : (none)
Build Date  : Wed Oct  7 10:49:04 2009
Build Host  : localhost
Relocations : (not relocatable)
Packager    : Another Packager (Another Key) <packager@another.com>
Summary     : gpg(anotherkey Packager (Another Key) <packager@another.com>)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)

vjjfirwqqohjeiudxshafuqwehirhqweijqpwe
-----END PGP PUBLIC KEY BLOCK-----

Name        : gpg-pubkey
Version     : 11111111
Release     : 44444444
Architecture: (none)
Install Date: Mon May 26 11:46:21 2025
Group       : Public Keys
Size        : 0
License     : pubkey
Signature   : (none)
Source RPM  : (none)
Build Date  : Wed Oct  7 10:49:04 2009
Build Host  : localhost
Relocations : (not relocatable)
Packager    : Last Packager (Last Key) <packager@last.com>
Summary     : gpg(lastkey Packager (Last Key) <packager@last.com>)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)

oyiyjjhgjktoroprplfkmfhtyrturioqwpekqwejt
-----END PGP PUBLIC KEY BLOCK-----
""")
        self.assertTrue(rpm.extract_gpgkey_from_rpm_database(".*another.*", dst_file, src_file))
        self.assertTrue(os.path.exists(dst_file))

        with open(dst_file, "r") as f:
            content = f.read()
            self.assertIn("-----BEGIN PGP PUBLIC KEY BLOCK-----\n", content)
            self.assertIn("Version: rpm-4.11.3 (NSS-3)\n", content)
            self.assertIn("vjjfirwqqohjeiudxshafuqwehirhqweijqpwe\n", content)
            self.assertIn("-----END PGP PUBLIC KEY BLOCK-----\n", content)

    def test_empty_file(self):
        src_file = os.path.join(self.TEST_DIR, "empty.txt")
        dst_file = os.path.join(self.TEST_DIR, "empty_res.asc")
        with open(src_file, "w"):
            pass
        self.assertFalse(rpm.extract_gpgkey_from_rpm_database(".*", dst_file, src_file))
        self.assertFalse(os.path.exists(dst_file))

    def test_file_with_malformed_key_block(self):
        src_file = os.path.join(self.TEST_DIR, "malformed.txt")
        dst_file = os.path.join(self.TEST_DIR, "malformed_res.asc")
        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Summary     : gpg(mykey)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
qlqlqlwekqweoqwekpoqwpkeopqwkepoqkwpe
# missing END block
""")
        self.assertFalse(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertFalse(os.path.exists(dst_file))

    def test_file_with_malformed_key_block_by_name(self):
        src_file = os.path.join(self.TEST_DIR, "malformed.txt")
        dst_file = os.path.join(self.TEST_DIR, "malformed_res.asc")
        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Summary     : gpg(mykey)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
qlqlqlwekqweoqwekpoqwpkeopqwkepoqkwpe
# missing END block
Name        : another-gpg-pubkey
""")
        self.assertFalse(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertFalse(os.path.exists(dst_file))

    def test_multiple_matching_keys(self):
        src_file = os.path.join(self.TEST_DIR, "multi_match.txt")
        dst_file = os.path.join(self.TEST_DIR, "multi_match_res.asc")
        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Summary     : gpg(mykey)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)
KEY1
-----END PGP PUBLIC KEY BLOCK-----

Name        : gpg-pubkey
Summary     : gpg(mykey)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)
KEY2
-----END PGP PUBLIC KEY BLOCK-----
""")
        self.assertTrue(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertTrue(os.path.exists(dst_file))
        with open(dst_file, "r") as f:
            content = f.read()
            self.assertIn("KEY1", content)
            # For now only first matching key is extracted
            # Maybe later we should make several files or throw an error
            # not sure for now
            self.assertNotIn("KEY2", content)

    def test_partial_match(self):
        src_file = os.path.join(self.TEST_DIR, "partial_match.txt")
        dst_file = os.path.join(self.TEST_DIR, "partial_match_res.asc")
        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Summary     : gpg(somekey)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)
PARTIAL
-----END PGP PUBLIC KEY BLOCK-----
""")
        # Should not match 'mykey'
        self.assertFalse(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertFalse(os.path.exists(dst_file))

    def test_key_block_with_extra_whitespace(self):
        src_file = os.path.join(self.TEST_DIR, "whitespace.txt")
        dst_file = os.path.join(self.TEST_DIR, "whitespace_res.asc")
        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Summary     : gpg(mykey)
Description :

   -----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)
WHITESPACE
-----END PGP PUBLIC KEY BLOCK-----
""")
        self.assertTrue(rpm.extract_gpgkey_from_rpm_database(".*mykey.*", dst_file, src_file))
        self.assertTrue(os.path.exists(dst_file))
        with open(dst_file, "r") as f:
            content = f.read()
            self.assertIn("WHITESPACE", content)

    def test_wrong_regexp(self):
        src_file = os.path.join(self.TEST_DIR, "wrong_regexp.txt")
        dst_file = os.path.join(self.TEST_DIR, "wrong_regexp_res.asc")
        with open(src_file, "w") as f:
            f.write("""Name        : gpg-pubkey
Summary     : gpg(somekey)
Description :
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: rpm-4.11.3 (NSS-3)
PARTIAL
-----END PGP PUBLIC KEY BLOCK-----
""")
        with self.assertRaises(Exception):
            rpm.extract_gpgkey_from_rpm_database("[", dst_file, src_file)
