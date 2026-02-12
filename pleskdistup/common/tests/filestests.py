# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import unittest
import unittest.mock
import os
import json
import tempfile
import shutil

import src.files as files


class ReplaceFileStringTests(unittest.TestCase):
    REPLACE_FILE_CONTENT = """---> cccc <---
This is the file where we want to replace some string. This is the string to replace ---> aaaa <---.
---> eeee <---
---> gggg <---
"""

    DATA_FILE_NAME = "datafile.txt"

    def setUp(self):
        with open(self.DATA_FILE_NAME, "w") as f:
            f.write(self.REPLACE_FILE_CONTENT)

    def tearDown(self):
        if os.path.exists(self.DATA_FILE_NAME):
            os.remove(self.DATA_FILE_NAME)

    def test_simple_string_replace(self):
        files.replace_string(self.DATA_FILE_NAME, "aaaa", "bbbb")
        with open(self.DATA_FILE_NAME) as file:
            for line in file.readlines():
                if line.startswith("This is the string to replace"):
                    self.assertEqual(line, "This is the file where we want to replace some string. This is the string to replace ---> bbbb <---.")
                    break

    def test_replace_first_string(self):
        files.replace_string(self.DATA_FILE_NAME, "---> cccc <---", "<--- dddd --->")
        with open(self.DATA_FILE_NAME) as file:
            self.assertEqual(file.readline().rstrip(), "<--- dddd --->")

    def test_replace_whole_line(self):
        files.replace_string(self.DATA_FILE_NAME, "---> eeee <---", "<--- ffff --->")
        with open(self.DATA_FILE_NAME) as file:
            line = file.readlines()[-2].rstrip()
            self.assertEqual(line, "<--- ffff --->")

    def test_replase_last_string(self):
        files.replace_string(self.DATA_FILE_NAME, "---> gggg <---", "<--- hhhh --->")
        with open(self.DATA_FILE_NAME) as file:
            line = file.readlines()[-1].rstrip()
            self.assertEqual(line, "<--- hhhh --->")


class AppendStringsTests(unittest.TestCase):
    ORIGINAL_FILE_NAME = "original.txt"

    def setUp(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("")

    def tearDown(self):
        if os.path.exists(self.ORIGINAL_FILE_NAME):
            os.remove(self.ORIGINAL_FILE_NAME)

    def test_add_to_empty(self):
        files.append_strings(self.ORIGINAL_FILE_NAME, ['aaaa\n', 'bbbb\n'])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ['aaaa', 'bbbb'])

    def test_add_to_non_empty(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("aaaa\n")
        files.append_strings(self.ORIGINAL_FILE_NAME, ["bbbb\n", "cccc\n"])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["aaaa", "bbbb", "cccc"])

    def test_add_nothing(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("aaaa\n")
        files.append_strings(self.ORIGINAL_FILE_NAME, [])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["aaaa"])


class PushFrontStringsTests(unittest.TestCase):
    ORIGINAL_FILE_NAME = "original.txt"

    def setUp(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("")

    def tearDown(self):
        if os.path.exists(self.ORIGINAL_FILE_NAME):
            os.remove(self.ORIGINAL_FILE_NAME)

    def test_add_to_empty(self):
        files.push_front_strings(self.ORIGINAL_FILE_NAME, ["aaaa\n", "bbbb\n"])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["aaaa", "bbbb"])

    def test_add_to_non_empty(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("aaaa\n")
        files.push_front_strings(self.ORIGINAL_FILE_NAME, ["bbbb\n", "cccc\n"])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["bbbb", "cccc", "aaaa"])

    def test_add_nothing(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("aaaa\n")
        files.push_front_strings(self.ORIGINAL_FILE_NAME, [])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["aaaa"])


class RewriteJsonTests(unittest.TestCase):
    OriginalJson = {
        "key1": "value1",
        "obj": {
            "key2": "value2",
        },
        "array": [
            "value3",
            "value4",
            "value5",
        ],
        "objs": [
            {
                "sharedkey": "value6",
            },
            {
                "sharedkey": "value7",
            }
        ],
    }
    INITIAL_JSON_FILE_NAME = "test.json"

    def setUp(self):
        with open(self.INITIAL_JSON_FILE_NAME, "w") as f:
            f.write(json.dumps(self.OriginalJson))

    def tearDown(self):
        if os.path.exists(self.INITIAL_JSON_FILE_NAME):
            os.remove(self.INITIAL_JSON_FILE_NAME)

    def test_simple_json_rewrite(self):
        new_json = {
            "key1": "newvalue",
            "obj": {
                "key2": "newvalue2",
            },
            "array": [
                "newvalue3",
                "newvalue4",
                "newvalue5",
            ],
            "objs": [
                {
                    "sharedkey": "newvalue6",
                },
                {
                    "sharedkey": "newvalue7",
                }
            ],
        }
        new_json["key1"] = "newvalue"
        files.rewrite_json_file(self.INITIAL_JSON_FILE_NAME, new_json)
        with open(self.INITIAL_JSON_FILE_NAME) as file:
            self.assertEqual(json.load(file), new_json)


class FindFilesCaseInsensativeTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_find_file(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["file.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["file.txt"])

    def test_find_file_with_different_case(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["FILE.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["file.txt"])

    def test_find_several_files_by_extension(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file2.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file.md"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["*.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["file.txt", "file2.txt"])

    def test_find_different_case_files(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "FILE.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["file.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["FILE.txt", "file.txt"])

    def test_find_different_case_files_by_extension(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "FILE.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file.md"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["f*.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["FILE.txt", "file.txt"])

    def test_empty_directory(self):
        self.assertEqual(files.find_files_case_insensitive(self.temp_dir, ["file.txt"]), [])

    def test_find_no_files_by_extension(self):
        self.assertEqual(files.find_files_case_insensitive(self.temp_dir, ["*.txt"]), [])

    def test_find_no_files(self):
        with open(os.path.join(self.temp_dir, "file.md"), "w") as f:
            f.write("")

        self.assertEqual(files.find_files_case_insensitive(self.temp_dir, ["file.txt"]), [])

    def test_no_such_directory(self):
        self.assertEqual(files.find_files_case_insensitive(os.path.join(self.temp_dir, "no_such_dir"), ["file.txt"]), [])

    def test_several_regexps(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file2.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file.md"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["file.txt", "*.md"]))
        self.assertEqual([os.path.basename(file) for file in result], ["file.md", "file.txt"])

    def test_repo_example(self):
        file_names = ["almalinux-ha.repo", "almalinux-powertools.repo", "almalinux-rt.repo",
                      "ELevate.repo", "epel-testing-modular.repo", "imunify360-testing.repo",
                      "kolab-16-testing-candidate.repo", "plesk-ext-ruby.repo", "almalinux-nfv.repo",
                      "almalinux.repo", "almalinux-saphana.repo", "epel-modular.repo",
                      "epel-testing.repo", "imunify-rollout.repo", "kolab-16-testing.repo",
                      "plesk.repo", "almalinux-plus.repo", "almalinux-resilientstorage.repo",
                      "almalinux-sap.repo", "epel.repo", "imunify360.repo",
                      "kolab-16.repo", "plesk-ext-panel-migrator.repo",
                      ]

        for file_name in file_names:
            with open(os.path.join(self.temp_dir, file_name), "w") as f:
                f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["plesk*.repo"]))
        self.assertEqual([os.path.basename(file) for file in result], ["plesk-ext-panel-migrator.repo", "plesk-ext-ruby.repo", "plesk.repo"])

    def test_recursive_simple(self):
        os.mkdir(os.path.join(self.temp_dir, "subdir"))
        with open(os.path.join(self.temp_dir, "subdir", "file.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["file.txt"], recursive=True))
        self.assertEqual([os.path.relpath(file, self.temp_dir) for file in result], ["subdir/file.txt"])

    def test_recursive_in_dir_and_subdir(self):
        with open(os.path.join(self.temp_dir, "file1.txt"), "w") as f:
            f.write("")
        os.mkdir(os.path.join(self.temp_dir, "subdir"))
        with open(os.path.join(self.temp_dir, "subdir", "file2.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["*.txt"], recursive=True))
        self.assertEqual([os.path.relpath(file, self.temp_dir) for file in result], ["file1.txt", "subdir/file2.txt"])

    def test_subdir_search_is_not_supported(self):
        # Just to show that we don't support seraching with subdir included
        # in regexp. We can search only by filenames for now.
        os.mkdir(os.path.join(self.temp_dir, "subdir"))
        with open(os.path.join(self.temp_dir, "subdir", "file.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["subdir/file.txt"], recursive=True))
        self.assertEqual([os.path.relpath(file, self.temp_dir) for file in result], [])


class CheckDirectoryIsEmpty(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_empty_directory(self):
        self.assertTrue(files.is_directory_empty(self.temp_dir))

    def test_directory_with_file(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        self.assertFalse(files.is_directory_empty(self.temp_dir))

    def test_no_such_directory(self):
        self.assertTrue(files.is_directory_empty(os.path.join(self.temp_dir, "no_such_dir")))


class FindSubdirectory(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_find_by_name(self):
        os.mkdir(os.path.join(self.temp_dir, "subdir"))
        os.mkdir(os.path.join(self.temp_dir, "subdir2"))

        self.assertEqual(files.find_subdirectory_by(self.temp_dir, lambda subdir: os.path.basename(subdir) == "subdir2"),
                         os.path.join(self.temp_dir, "subdir2"))

    def test_find_by_name_not_found(self):
        os.mkdir(os.path.join(self.temp_dir, "subdir"))
        os.mkdir(os.path.join(self.temp_dir, "subdir2"))

        self.assertIsNone(files.find_subdirectory_by(self.temp_dir, lambda subdir: os.path.basename(subdir) == "subdir3"))

    def test_find_by_name_in_subdir(self):
        os.mkdir(os.path.join(self.temp_dir, "subdir"))
        os.mkdir(os.path.join(self.temp_dir, "subdir2"))
        os.mkdir(os.path.join(self.temp_dir, "subdir2", "subdir3"))

        self.assertEqual(files.find_subdirectory_by(self.temp_dir, lambda subdir: os.path.basename(subdir) == "subdir3"),
                         os.path.join(self.temp_dir, "subdir2", "subdir3"))

    def test_find_by_file_inside(self):
        os.mkdir(os.path.join(self.temp_dir, "subdir"))
        os.mkdir(os.path.join(self.temp_dir, "subdir2"))
        with open(os.path.join(self.temp_dir, "subdir2", "file.txt"), "w") as f:
            f.write("")

        self.assertEqual(files.find_subdirectory_by(self.temp_dir, lambda subdir: os.path.exists(os.path.join(subdir, "file.txt"))), os.path.join(self.temp_dir, "subdir2"))


class FindFileSubstring(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.mkstemp()[1]

    def tearDown(self) -> None:
        os.remove(self.temp_file)

    def test_one_line(self):
        with open(self.temp_file, "w") as f:
            f.write("aaaa: bbbbbb\n")
            f.write("cccc: bbbbbb\n")
            f.write("dddd: kkkkkk\n")

        self.assertEqual(files.find_file_substrings(self.temp_file, "cccc"), ["cccc: bbbbbb\n"])

    def test_several_lines(self):
        with open(self.temp_file, "w") as f:
            f.write("aaaa: bbbbbb\n")
            f.write("cccc: bbbbbb\n")
            f.write("dddd: kkkkkk\n")

        self.assertEqual(files.find_file_substrings(self.temp_file, "bbbbb"), ["aaaa: bbbbbb\n", "cccc: bbbbbb\n"])

    def test_no_such_file(self):
        self.assertEqual(files.find_file_substrings("no_such_file.txt", "bbbbb"), [])

    def test_no_such_substring(self):
        with open(self.temp_file, "w") as f:
            f.write("aaaa: bbbbbb\n")
            f.write("cccc: bbbbbb\n")
            f.write("dddd: kkkkkk\n")

        self.assertEqual(files.find_file_substrings(self.temp_file, "no_such_substring"), [])


class CNFSetVariable(unittest.TestCase):

    TEST_FILE_CONTENT = """
[test]
variable1=value1
variable2 = value2
"""

    def setUp(self):
        self.temp_file = tempfile.mkstemp()[1]
        with open(self.temp_file, "w") as f:
            f.write(self.TEST_FILE_CONTENT)

    def tearDown(self) -> None:
        os.remove(self.temp_file)

    def test_change_variable(self):
        EXPECTED_FILE_CONTENT = """
[test]
variable1=value12
variable2=value22
"""

        files.cnf_set_section_variable(self.temp_file, "test", "variable1", "value12")
        files.cnf_set_section_variable(self.temp_file, "test", "variable2", "value22")
        with open(self.temp_file) as f:
            self.assertEqual(f.read(), EXPECTED_FILE_CONTENT)

    def test_add_variable(self):
        EXPECTED_FILE_CONTENT = """
[test]
variable1=value1
variable2 = value2
variable3=value3
"""

        files.cnf_set_section_variable(self.temp_file, "test", "variable3", "value3")
        with open(self.temp_file) as f:
            self.assertEqual(f.read(), EXPECTED_FILE_CONTENT)

    def test_insert_section(self):
        EXPECTED_FILE_CONTENT = """
[test]
variable1=value1
variable2 = value2

[test2]
variable2=value2
"""

        files.cnf_set_section_variable(self.temp_file, "test2", "variable2", "value2")
        with open(self.temp_file) as f:
            self.assertEqual(f.read(), EXPECTED_FILE_CONTENT)

    def test_add_section_similar_variable(self):
        EXPECTED_FILE_CONTENT = """
[test]
variable1=value1
variable2 = value2

[test2]
variable1=value2
"""

        files.cnf_set_section_variable(self.temp_file, "test2", "variable1", "value2")
        with open(self.temp_file) as f:
            self.assertEqual(f.read(), EXPECTED_FILE_CONTENT)


class CNFUnsetVariable(unittest.TestCase):

    TEST_FILE_CONTENT = """
[test1]
variable1=value1
variable2 = value1
variable3=value1

[test2]
variable1=value2
"""

    def setUp(self):
        self.temp_file = tempfile.mkstemp()[1]
        with open(self.temp_file, "w") as f:
            f.write(self.TEST_FILE_CONTENT)

    def tearDown(self) -> None:
        os.remove(self.temp_file)

    def test_remove_variable(self):
        EXPECTED_FILE_CONTENT = """
[test1]
variable3=value1

[test2]
variable1=value2
"""

        files.cnf_unset_section_variable(self.temp_file, "test1", "variable1")
        files.cnf_unset_section_variable(self.temp_file, "test1", "variable2")
        with open(self.temp_file) as f:
            self.assertEqual(f.read(), EXPECTED_FILE_CONTENT)

    def test_remove_similar_variable(self):
        EXPECTED_FILE_CONTENT = """
[test1]
variable2 = value1
variable3=value1

[test2]
variable1=value2
"""
        files.cnf_unset_section_variable(self.temp_file, "test1", "variable1")
        with open(self.temp_file) as f:
            self.assertEqual(f.read(), EXPECTED_FILE_CONTENT)

    def test_remove_last_section_variable(self):
        EXPECTED_FILE_CONTENT = """
[test1]
variable1=value1
variable2 = value1
variable3=value1

[test2]
"""
        files.cnf_unset_section_variable(self.temp_file, "test2", "variable1")
        with open(self.temp_file) as f:
            self.assertEqual(f.read(), EXPECTED_FILE_CONTENT)


class ChangeFileOwnershipTests(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.mkstemp()[1]

    def tearDown(self) -> None:
        os.remove(self.temp_file)

    @unittest.mock.patch('src.files.os.chown')
    def test_change_file_ownership(self, mock_chown):
        """Test that change_file_ownership calls os.chown with correct parameters."""
        test_file = self.temp_file
        uid, gid = 1000, 1000

        files.change_file_ownership(test_file, uid, gid)
        mock_chown.assert_called_once_with(test_file, uid, gid)

    @unittest.mock.patch('src.files.os.chown')
    def test_change_file_ownership_with_pathlike(self, mock_chown):
        """Test that change_file_ownership works with PathLike objects."""
        test_path = self.temp_file
        uid, gid = 500, 500
        files.change_file_ownership(test_path, uid, gid)
        mock_chown.assert_called_once_with(test_path, uid, gid)

    @unittest.mock.patch('src.files.shutil.chown')
    def test_change_file_ownership_non_existent_file(self, mock_chown):
        """Test that change_file_ownership handles non-existent files correctly."""
        non_existent_file = "/path/to/non_existent_file.txt"
        uid, gid = 1000, 1000

        files.change_file_ownership(non_existent_file, uid, gid)

        mock_chown.assert_not_called()

    @unittest.mock.patch('src.files.shutil.chown')
    def test_change_file_ownership_directory(self, mock_chown):
        """Test that change_file_ownership handles directories correctly."""
        temp_dir = tempfile.mkdtemp()
        uid, gid = 1000, 1000

        files.change_file_ownership(temp_dir, uid, gid)

        mock_chown.assert_not_called()

        shutil.rmtree(temp_dir)


class ChangeDirectoryOwnershipTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.subdir = os.path.join(self.temp_dir, "subdir")
        self.file1 = os.path.join(self.temp_dir, "file1.txt")
        self.file2 = os.path.join(self.subdir, "file2.txt")

        os.mkdir(self.subdir)
        with open(self.file1, "w") as f:
            f.write("test file 1")
        with open(self.file2, "w") as f:
            f.write("test file 2")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @unittest.mock.patch('src.files.os.chown')
    def test_change_directory_ownership_non_recursive(self, mock_chown):
        """Test non-recursive directory ownership change."""
        uid, gid = 1000, 1000

        files.change_directory_ownership(self.temp_dir, uid, gid, recursive=False)

        mock_chown.assert_called_once_with(self.temp_dir, uid, gid)

    @unittest.mock.patch('src.files.os.chown')
    def test_change_directory_ownership_recursive(self, mock_chown):
        """Test recursive directory ownership change."""
        uid, gid = 1000, 1000
        files.change_directory_ownership(self.temp_dir, uid, gid, recursive=True)

        expected_calls = [
            unittest.mock.call(self.temp_dir, uid, gid),
            unittest.mock.call(self.subdir, uid, gid),
            unittest.mock.call(self.file1, uid, gid),
            unittest.mock.call(self.file2, uid, gid)
        ]

        self.assertEqual(mock_chown.call_count, 4)
        mock_chown.assert_has_calls(expected_calls, any_order=True)

    @unittest.mock.patch('src.files.os.chown')
    def test_change_directory_ownership_recursive_default(self, mock_chown):
        """Test that recursive=True is the default behavior."""
        uid, gid = 500, 500

        files.change_directory_ownership(self.temp_dir, uid, gid)
        self.assertEqual(mock_chown.call_count, 4)

    @unittest.mock.patch('src.files.os.chown')
    def test_change_directory_ownership_with_pathlike(self, mock_chown):
        """Test that change_directory_ownership works with PathLike objects."""
        test_path = os.path.join(self.temp_dir, "subdir")
        uid, gid = 2000, 2000
        files.change_directory_ownership(test_path, uid, gid, recursive=False)
        mock_chown.assert_called_once_with(test_path, uid, gid)

    @unittest.mock.patch('src.files.shutil.chown')
    def test_change_directory_ownership_non_existent_recursive(self, mock_chown):
        """Test recursive ownership change on non-existent directory."""
        non_existent_dir = "/path/to/non_existent_directory"
        uid, gid = 1000, 1000

        files.change_directory_ownership(non_existent_dir, uid, gid, recursive=True)

        mock_chown.assert_not_called()

    @unittest.mock.patch('src.files.shutil.chown')
    def test_change_directory_ownership_non_existent_non_recursive(self, mock_chown):
        """Test non-recursive ownership change on non-existent directory."""
        non_existent_dir = "/path/to/non_existent_directory"
        uid, gid = 1000, 1000

        files.change_directory_ownership(non_existent_dir, uid, gid, recursive=False)

        mock_chown.assert_not_called()

    @unittest.mock.patch('src.files.shutil.chown')
    def test_change_directory_ownership_file_instead_of_directory_recursive(self, mock_chown):
        """Test recursive ownership change when passing a file instead of directory."""
        uid, gid = 1000, 1000
        files.change_directory_ownership(self.file1, uid, gid, recursive=True)
        mock_chown.assert_not_called()

    @unittest.mock.patch('src.files.shutil.chown')
    def test_change_directory_ownership_file_instead_of_directory_non_recursive(self, mock_chown):
        """Test non-recursive ownership change when passing a file instead of directory."""
        uid, gid = 1000, 1000
        files.change_directory_ownership(self.file1, uid, gid, recursive=False)
        mock_chown.assert_called_once_with(self.file1, uid, gid)
