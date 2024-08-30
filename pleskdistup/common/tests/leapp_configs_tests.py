# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import unittest
import os
import json
import typing

import src.leapp_configs as leapp_configs


class AddMappingTests(unittest.TestCase):

    LEAPP_REPO_FILE = "leapp_repos.repo"
    LEAPP_MAP_FILE = "map.repo"

    def tearDown(self):
        for files in (self.LEAPP_REPO_FILE, self.LEAPP_MAP_FILE):
            if os.path.exists(files):
                os.remove(files)

    def _perform_test(self, repos: typing.Dict[str, str], expected_repos: str, expected_mapping: str, ignore: typing.Optional[typing.List[str]] = None) -> None:
        for filename, content in repos.items():
            with open(filename, "w") as f:
                f.write(content)

        leapp_configs.add_repositories_mapping(list(repos), ignore=ignore,
                                               leapp_repos_file_path=self.LEAPP_REPO_FILE,
                                               mapfile_path=self.LEAPP_MAP_FILE)

        with open(self.LEAPP_REPO_FILE) as f:
            lines = [line.rstrip() for line in f.readlines() if not line.rstrip() == ""]
            print(lines)
            self.assertEqual(lines, expected_repos.splitlines())

        with open(self.LEAPP_MAP_FILE) as f:
            lines = [line.rstrip() for line in f.readlines() if not line.rstrip() == ""]
            self.assertEqual(lines, expected_mapping.splitlines())

        for files in repos.keys():
            if os.path.exists(files):
                os.remove(files)

    def test_simple_mapping(self):
        simple_repos = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0
#no comment removed

[repo2]
name=repo2
baseurl=http://repo2/rpm-CentOS-7
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3/centos7
enabled=1
gpgcheck=0
"""

        expected_leapp_repos = """[alma-repo1]
name=Alma repo1
baseurl=http://repo1
enabled=1
gpgcheck=0
#no comment removed
[alma-repo2]
name=Alma repo2
baseurl=http://repo2/rpm-RedHat-el8
enabled=1
gpgcheck=0
[alma-repo3]
name=Alma repo3
baseurl=http://repo3/centos8
enabled=1
gpgcheck=0
"""
        expected_leapp_mapping = """repo1,alma-repo1,alma-repo1,all,all,x86_64,rpm,ga,ga
repo2,alma-repo2,alma-repo2,all,all,x86_64,rpm,ga,ga
repo3,alma-repo3,alma-repo3,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"simple_repos.repo": simple_repos},
                           expected_leapp_repos, expected_leapp_mapping)

    def test_kolab_related_mapping(self):
        kolab_repos = """[kolab-repo]
name=Kolab repo
baseurl=https://mirror.apheleia-it.ch/repos/Kolab:/16/CentOS_7_Plesk_17/src
enabled=0
priority=60
skip_if_unavailable=1
gpgcheck=1
"""

        expected_kolab_leapp_repos = """[alma-kolab-repo]
name=Alma Kolab repo
baseurl=https://mirror.apheleia-it.ch/repos/Kolab:/16/CentOS_8_Plesk_17/src
enabled=0
priority=60
skip_if_unavailable=1
gpgcheck=1
"""

        expected_kolab_leapp_mapping = """kolab-repo,alma-kolab-repo,alma-kolab-repo,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"kolab.repo": kolab_repos},
                           expected_kolab_leapp_repos, expected_kolab_leapp_mapping)

    def test_epel_mapping(self):
        epel_like_repos = """[epel-repo]
name=EPEL-7 repo
metalink=http://epel-repo/epel-7
enabled=1
gpgcheck=0

[epel-debug-repo]
name=EPEL-7 debug repo
metalink=http://epel-repo/epel-debug-7
enabled=1
gpgcheck=0

[epel-source-repo]
name=EPEL-7 source repo
metalink=http://epel-repo/epel-source-7
enabled=1
gpgcheck=0
"""
        expected_leapp_repos = """[alma-epel-repo]
name=Alma EPEL-8 repo
metalink=http://epel-repo/epel-8
enabled=1
gpgcheck=0
[alma-epel-debug-repo]
name=Alma EPEL-8 debug repo
metalink=http://epel-repo/epel-debug-8
enabled=1
gpgcheck=0
[alma-epel-source-repo]
name=Alma EPEL-8 source repo
metalink=http://epel-repo/epel-source-8
enabled=1
gpgcheck=0
"""
        expected_leapp_mapping = """epel-repo,alma-epel-repo,alma-epel-repo,all,all,x86_64,rpm,ga,ga
epel-debug-repo,alma-epel-debug-repo,alma-epel-debug-repo,all,all,x86_64,rpm,ga,ga
epel-source-repo,alma-epel-source-repo,alma-epel-source-repo,all,all,x86_64,rpm,ga,ga
"""
        self._perform_test({"epel_repos.repo": epel_like_repos},
                           expected_leapp_repos, expected_leapp_mapping)

    def test_plesk_mapping(self):
        plesk_like_repos = """[PLESK_18_0_XX-extras]
name=plesk extras repo
baseurl=http://plesk/rpm-CentOS-7/extras
enabled=1
gpgcheck=0

[PLESK_18_0_XX-PHP-5.5]
name=plesk php 5.5 repo
baseurl=http://plesk/rpm-CentOS-7/php-5.5
enabled=1
gpgcheck=0

[PLESK_18_0_XX-PHP72]
name=plesk php 7.2 repo
baseurl=http://plesk/rpm-CentOS-7/PHP_7.2
enabled=1
gpgcheck=0

[PLESK_18_0_XX-PHP80]
name=plesk php 8.0 repo
baseurl=http://plesk/rpm-CentOS-7/PHP_8.0
enabled=1
gpgcheck=0
"""
        expected_leapp_repos = """[alma-PLESK_18_0_XX-extras]
name=Alma plesk extras repo
baseurl=http://plesk/rpm-RedHat-el8/extras
enabled=1
gpgcheck=0
[alma-PLESK_18_0_XX]
name=Alma plesk  repo
baseurl=http://plesk/rpm-RedHat-el8/dist
enabled=1
gpgcheck=1
[alma-PLESK_18_0_XX-PHP72]
name=Alma plesk php 7.2 repo
baseurl=http://plesk/rpm-CentOS-8/PHP_7.2
enabled=1
gpgcheck=0
[alma-PLESK_18_0_XX-PHP80]
name=Alma plesk php 8.0 repo
baseurl=http://plesk/rpm-RedHat-el8/PHP_8.0
enabled=1
gpgcheck=0
"""
        expected_leapp_mapping = """PLESK_18_0_XX-extras,alma-PLESK_18_0_XX,alma-PLESK_18_0_XX,all,all,x86_64,rpm,ga,ga
PLESK_18_0_XX-extras,alma-PLESK_18_0_XX-extras,alma-PLESK_18_0_XX-extras,all,all,x86_64,rpm,ga,ga
PLESK_18_0_XX-PHP72,alma-PLESK_18_0_XX-PHP72,alma-PLESK_18_0_XX-PHP72,all,all,x86_64,rpm,ga,ga
PLESK_18_0_XX-PHP80,alma-PLESK_18_0_XX-PHP80,alma-PLESK_18_0_XX-PHP80,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"plesk_repos.repo": plesk_like_repos},
                           expected_leapp_repos, expected_leapp_mapping,
                           ignore=["PLESK_18_0_XX-PHP-5.5"])

    def test_mariadb_mapping(self):
        mariadb_like_repos = """[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/10.11/centos7-amd64
module_hotfixes=1
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1

[mariadb rhel]
name = Other MariaDB
baseurl=http://yum.mariadb.org/10.11.8/rhel7-amd64
module_hotfixes=1
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
"""

        expected_mariadb_repos = """[alma-mariadb]
name=Alma MariaDB
baseurl=http://yum.mariadb.org/10.11/rhel8-amd64
module_hotfixes=1
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
[alma-mariadb rhel]
name=Alma Other MariaDB
baseurl=http://yum.mariadb.org/10.11.8/rhel8-amd64
module_hotfixes=1
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1
"""

        expected_mariadb_mapping = """mariadb,alma-mariadb,alma-mariadb,all,all,x86_64,rpm,ga,ga
mariadb rhel,alma-mariadb rhel,alma-mariadb rhel,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"mariadb.repo": mariadb_like_repos},
                           expected_mariadb_repos, expected_mariadb_mapping)

    def test_official_postgresql_mapping(self):
        # Not full, but representative enough
        postgresql_like_repos = """[pgdg-common]
name=PostgreSQL common RPMs for RHEL / CentOS $releasever - $basearch
baseurl=https://download.postgresql.org/pub/repos/yum/common/redhat/rhel-$releasever-$basearch
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg15]
name=PostgreSQL 15 for RHEL / CentOS $releasever - $basearch
baseurl=https://download.postgresql.org/pub/repos/yum/15/redhat/rhel-$releasever-$basearch
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg-common-testing]
name=PostgreSQL common testing RPMs for RHEL / CentOS $releasever - $basearch
baseurl=https://download.postgresql.org/pub/repos/yum/testing/common/redhat/rhel-$releasever-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg16-updates-testing]
name=PostgreSQL 16 for RHEL / CentOS $releasever - $basearch - Updates testing
baseurl=https://download.postgresql.org/pub/repos/yum/testing/16/redhat/rhel-$releasever-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg15-updates-testing]
name=PostgreSQL 15 for RHEL / CentOS $releasever - $basearch - Updates testing
baseurl=https://download.postgresql.org/pub/repos/yum/testing/15/redhat/rhel-$releasever-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg-source-common]
name=PostgreSQL 12 for RHEL / CentOS $releasever - $basearch - Source
baseurl=https://download.postgresql.org/pub/repos/yum/srpms/common/redhat/rhel-$releasever-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg15-updates-testing-debuginfo]
name=PostgreSQL 15 for RHEL / CentOS $releasever - $basearch - Debuginfo
baseurl=https://download.postgresql.org/pub/repos/yum/testing/debug/15/redhat/rhel-$releasever-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg15-source-updates-testing]
name=PostgreSQL 15 for RHEL / CentOS $releasever - $basearch - Source updates testing
baseurl=https://download.postgresql.org/pub/repos/yum/srpms/testing/15/redhat/rhel-$releasever-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg14-source]
name=PostgreSQL 14 for RHEL / CentOS $releasever - $basearch - Source
baseurl=https://download.postgresql.org/pub/repos/yum/srpms/14/redhat/rhel-$releasever-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1

[pgdg14-source-updates-testing]
name=PostgreSQL 14 for RHEL / CentOS $releasever - $basearch - Source updates testing
baseurl=https://download.postgresql.org/pub/repos/yum/srpms/testing/14/redhat/rhel-$releasever-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 1
"""

        expected_postgresql_repos = """[alma-pgdg-common]
name=Alma PostgreSQL common RPMs for RHEL / CentOS 8 - $basearch
baseurl=https://download.postgresql.org/pub/repos/yum/common/redhat/rhel-8-$basearch
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg15]
name=Alma PostgreSQL 15 for RHEL / CentOS 8 - $basearch
baseurl=https://download.postgresql.org/pub/repos/yum/15/redhat/rhel-8-$basearch
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg-common-testing]
name=Alma PostgreSQL common testing RPMs for RHEL / CentOS 8 - $basearch
baseurl=https://download.postgresql.org/pub/repos/yum/testing/common/redhat/rhel-8-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg16-updates-testing]
name=Alma PostgreSQL 16 for RHEL / CentOS 8 - $basearch - Updates testing
baseurl=https://download.postgresql.org/pub/repos/yum/testing/16/redhat/rhel-8-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg15-updates-testing]
name=Alma PostgreSQL 15 for RHEL / CentOS 8 - $basearch - Updates testing
baseurl=https://download.postgresql.org/pub/repos/yum/15/redhat/rhel-8-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg-source-common]
name=Alma PostgreSQL 12 for RHEL / CentOS 8 - $basearch - Source
baseurl=https://download.postgresql.org/pub/repos/yum/srpms/common/redhat/rhel-8-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg15-updates-testing-debuginfo]
name=Alma PostgreSQL 15 for RHEL / CentOS 8 - $basearch - Debuginfo
baseurl=https://download.postgresql.org/pub/repos/yum/testing/debug/15/redhat/rhel-8-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg15-source-updates-testing]
name=Alma PostgreSQL 15 for RHEL / CentOS 8 - $basearch - Source updates testing
baseurl=https://download.postgresql.org/pub/repos/yum/srpms/testing/15/redhat/rhel-8-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg14-source]
name=Alma PostgreSQL 14 for RHEL / CentOS 8 - $basearch - Source
baseurl=https://download.postgresql.org/pub/repos/yum/srpms/14/redhat/rhel-8-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
[alma-pgdg14-source-updates-testing]
name=Alma PostgreSQL 14 for RHEL / CentOS 8 - $basearch - Source updates testing
baseurl=https://download.postgresql.org/pub/repos/yum/srpms/14/redhat/rhel-8-$basearch
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-PGDG
repo_gpgcheck = 0
"""

        expected_postgresql_mapping = """pgdg-common,alma-pgdg-common,alma-pgdg-common,all,all,x86_64,rpm,ga,ga
pgdg15,alma-pgdg15,alma-pgdg15,all,all,x86_64,rpm,ga,ga
pgdg-common-testing,alma-pgdg-common-testing,alma-pgdg-common-testing,all,all,x86_64,rpm,ga,ga
pgdg16-updates-testing,alma-pgdg16-updates-testing,alma-pgdg16-updates-testing,all,all,x86_64,rpm,ga,ga
pgdg15-updates-testing,alma-pgdg15-updates-testing,alma-pgdg15-updates-testing,all,all,x86_64,rpm,ga,ga
pgdg-source-common,alma-pgdg-source-common,alma-pgdg-source-common,all,all,x86_64,rpm,ga,ga
pgdg15-updates-testing-debuginfo,alma-pgdg15-updates-testing-debuginfo,alma-pgdg15-updates-testing-debuginfo,all,all,x86_64,rpm,ga,ga
pgdg15-source-updates-testing,alma-pgdg15-source-updates-testing,alma-pgdg15-source-updates-testing,all,all,x86_64,rpm,ga,ga
pgdg14-source,alma-pgdg14-source,alma-pgdg14-source,all,all,x86_64,rpm,ga,ga
pgdg14-source-updates-testing,alma-pgdg14-source-updates-testing,alma-pgdg14-source-updates-testing,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"pgdg-redhat-all.repo": postgresql_like_repos},
                           expected_postgresql_repos, expected_postgresql_mapping)

    def test_rackspace_mapping(self):
        mariadb_like_repos = """[epel]
name=Extra Packages for Enterprise Linux 7 - $basearch
baseurl=http://iad.mirror.rackspace.com/epel/7Server/x86_64/
#metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-7&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-7

[epel-debuginfo]
name=Extra Packages for Enterprise Linux 7 - $basearch - Debug
baseurl=http://iad.mirror.rackspace.com/epel/7Server/x86_64/debug/
#metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-debug-7&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-7
gpgcheck=1

[epel-source]
name=Extra Packages for Enterprise Linux 7 - $basearch - Source
baseurl=http://iad.mirror.rackspace.com/epel/7Server/SRPMS/
#metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-source-7&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-7
gpgcheck=1
"""

        expected_mariadb_repos = """[alma-epel]
name=Alma Extra Packages for Enterprise Linux 8 - $basearch
baseurl=http://iad.mirror.rackspace.com/epel/8/Everything/x86_64/
#metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-7&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8
[alma-epel-debuginfo]
name=Alma Extra Packages for Enterprise Linux 8 - $basearch - Debug
baseurl=http://iad.mirror.rackspace.com/epel/8/Everything/x86_64/debug/
#metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-debug-7&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8
gpgcheck=1
[alma-epel-source]
name=Alma Extra Packages for Enterprise Linux 8 - $basearch - Source
baseurl=http://iad.mirror.rackspace.com/epel/8/Everything/SRPMS/
#metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-source-7&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8
gpgcheck=1
"""

        expected_mariadb_mapping = """epel,alma-epel,alma-epel,all,all,x86_64,rpm,ga,ga
epel-debuginfo,alma-epel-debuginfo,alma-epel-debuginfo,all,all,x86_64,rpm,ga,ga
epel-source,alma-epel-source,alma-epel-source,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"mariadb.repo": mariadb_like_repos},
                           expected_mariadb_repos, expected_mariadb_mapping)

    def test_avoid_duplicated_prefixes(self):
        prefixed_repo = """[alma-repo1]
name=Alma repo1
baseurl=http://repo1/rpm-CentOS-7
enabled=1
gpgcheck=0
"""

        expected_leapp_repos = """[alma-repo1]
name=Alma repo1
baseurl=http://repo1/rpm-RedHat-el8
enabled=1
gpgcheck=0
"""

        expected_leapp_mapping = """alma-repo1,alma-repo1,alma-repo1,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"prefixed.repo": prefixed_repo}, expected_leapp_repos, expected_leapp_mapping)


class SetPackageRepositoryTests(unittest.TestCase):
    INITIAL_JSON = {
        "packageinfo": [
            {
                "id": "1",
                "in_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "1",
                },
                "out_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "other-repo",
                        },
                    ],
                    "set_id": "2",
                },
            },
            {
                "id": "2",
                "in_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "3",
                },
                "out_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "other-repo",
                        },
                    ],
                    "set_id": "4",
                },
            },
            {
                "id": "3",
                "in_packageset": {
                    "package": [
                        {
                            "name": "empty",
                            "repository": "no-outpout-repo",
                        },
                    ],
                    "set_id": "5",
                },
                "out_packageset": None,
            },
        ]
    }

    JSON_FILE_PATH = "leapp_upgrade_repositories.json"
    # Since json could take pretty much symbols remove the restriction
    maxDiff = None

    def setUp(self):
        with open(self.JSON_FILE_PATH, "w") as f:
            f.write(json.dumps(self.INITIAL_JSON, indent=4))

    def tearDown(self):
        if os.path.exists(self.JSON_FILE_PATH):
            os.remove(self.JSON_FILE_PATH)
        pass

    def test_set_package_repository(self):
        leapp_configs.set_package_repository("some", "alma-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data["packageinfo"][0]["out_packageset"]["package"][0]["repository"], "alma-repo")
            self.assertEqual(json_data["packageinfo"][1]["out_packageset"]["package"][0]["repository"], "other-repo")

    def test_set_unexcited_package(self):
        leapp_configs.set_package_repository("unexsisted", "alma-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH, "r") as f:
            json_data = json.load(f)
            print(json_data)
            print(self.INITIAL_JSON)
            self.assertEqual(json_data, self.INITIAL_JSON)


class SetPackageActionTests(unittest.TestCase):
    INITIAL_JSON = {
        "packageinfo": [
            {
                "id": "1",
                "action": 1,
                "in_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "1",
                },
            },
            {
                "id": "2",
                "action": 4,
                "in_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "2",
                },
            },
            {
                "id": "3",
                "action": 4,
                "in_packageset": None,
            },
        ]
    }

    JSON_FILE_PATH = "leapp_upgrade_repositories.json"
    # Since json could take pretty much symbols remove the restriction
    maxDiff = None

    def setUp(self):
        with open(self.JSON_FILE_PATH, "w") as f:
            f.write(json.dumps(self.INITIAL_JSON, indent=4))

    def tearDown(self):
        if os.path.exists(self.JSON_FILE_PATH):
            os.remove(self.JSON_FILE_PATH)
        pass

    def test_set_package_action(self):
        leapp_configs.set_package_action("some", 3, leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data["packageinfo"][0]["action"], 3)
            self.assertEqual(json_data["packageinfo"][1]["action"], 4)

    def test_set_unexcited_package_action(self):
        leapp_configs.set_package_action("unexsisted", 3, leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH, "r") as f:
            json_data = json.load(f)
            self.assertEqual(json_data, self.INITIAL_JSON)


class TakeFreePackagesetIdTests(unittest.TestCase):
    def test_simple_take(self):
        json_data = {
            "packageinfo": [
                {
                    "action": 1,
                    "id": "1",
                    "in_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "some-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "some-repo",
                            },
                        ],
                        "set_id": "1",
                    },
                    "out_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "other-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "other-repo",
                            },
                        ],
                        "set_id": "2",
                    },
                }
            ]
        }
        self.assertEqual(leapp_configs.take_free_packageset_id(json_data), 3)

    def test_no_data(self):
        json_data = {}
        self.assertEqual(leapp_configs.take_free_packageset_id(json_data), 1)

    def test_empty_packageinfo(self):
        json_data = {"packageinfo": []}
        self.assertEqual(leapp_configs.take_free_packageset_id(json_data), 1)

    def test_reversed_ids(self):
        json_data = {
            "packageinfo": [
                {
                    "action": 1,
                    "id": "1",
                    "in_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "some-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "some-repo",
                            },
                        ],
                        "set_id": "2",
                    },
                    "out_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "other-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "other-repo",
                            },
                        ],
                        "set_id": "1",
                    },
                }
            ]
        }
        self.assertEqual(leapp_configs.take_free_packageset_id(json_data), 3)

    def test_no_in_packageset(self):
        json_data = {
            "packageinfo": [
                {
                    "action": 1,
                    "id": "1",
                    "in_packageset": None,
                    "out_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "other-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "other-repo",
                            },
                        ],
                        "set_id": "2",
                    },
                }
            ]
        }
        self.assertEqual(leapp_configs.take_free_packageset_id(json_data), 3)

    def test_no_out_packageset(self):
        json_data = {
            "packageinfo": [
                {
                    "action": 1,
                    "id": "1",
                    "in_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "other-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "other-repo",
                            },
                        ],
                        "set_id": "1",
                    },
                    "out_packageset": None,
                }
            ]
        }
        self.assertEqual(leapp_configs.take_free_packageset_id(json_data), 2)

    def test_several_packageinfos(self):
        json_data = {
            "packageinfo": [
                {
                    "action": 1,
                    "id": "1",
                    "in_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "some-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "some-repo",
                            },
                        ],
                        "set_id": "1",
                    },
                    "out_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "other-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "other-repo",
                            },
                        ],
                        "set_id": "2",
                    },
                },
                {
                    "action": 1,
                    "id": "2",
                    "in_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "some-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "some-repo",
                            },
                        ],
                        "set_id": "3",
                    },
                    "out_packageset": {
                        "package": [
                            {
                                "name": "some",
                                "repository": "other-repo",
                            },
                            {
                                "name": "some2",
                                "repository": "other-repo",
                            },
                        ],
                        "set_id": "4",
                    },
                }
            ]
        }
        self.assertEqual(leapp_configs.take_free_packageset_id(json_data), 5)


class SetPackageMapptingTests(unittest.TestCase):
    INITIAL_JSON = {
        "packageinfo": [
            {
                "id": "1",
                "action": 1,
                "in_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "1",
                },
            },
            {
                "id": "2",
                "action": 4,
                "in_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "2",
                },
                "out_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "other-repo",
                        },
                    ],
                    "set_id": "3",
                },
            },
            {
                "id": "3",
                "action": 4,
                "in_packageset": {
                    "package": [
                        {
                            "name": "known",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "4",
                },
                "out_packageset": {
                    "package": [
                        {
                            "name": "unknown",
                            "repository": "other-repo",
                        },
                    ],
                    "set_id": "5",
                },
            },
            {
                "id": "4",
                "action": 4,
                "in_packageset": None,
                "out_packageset": None,
            },
        ]
    }

    JSON_FILE_PATH = "leapp_upgrade_repositories.json"

    def setUp(self):
        with open(self.JSON_FILE_PATH, "w") as f:
            f.write(json.dumps(self.INITIAL_JSON, indent=4))

    def tearDown(self):
        if os.path.exists(self.JSON_FILE_PATH):
            os.remove(self.JSON_FILE_PATH)

    def test_add_missing_out_packageset(self):
        leapp_configs.set_package_mapping("some", "some-repo", "some", "right-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data["packageinfo"][0]["out_packageset"]["package"][0]["name"], "some")
            self.assertEqual(json_data["packageinfo"][0]["out_packageset"]["package"][0]["repository"], "right-repo")

    def test_change_existed_out_packageset(self):
        leapp_configs.set_package_mapping("other", "some-repo", "other", "right-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data["packageinfo"][1]["out_packageset"]["package"][0]["name"], "other")
            self.assertEqual(json_data["packageinfo"][1]["out_packageset"]["package"][0]["repository"], "right-repo")

    def test_replace_into_existed_out_packageset(self):
        leapp_configs.set_package_mapping("known", "some-repo", "known", "right-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data["packageinfo"][2]["out_packageset"]["package"][0]["name"], "known")
            self.assertEqual(json_data["packageinfo"][2]["out_packageset"]["package"][0]["repository"], "right-repo")
            self.assertEqual(len(json_data["packageinfo"][2]["out_packageset"]["package"]), 1)

    def test_no_target_package(self):
        leapp_configs.set_package_mapping("no", "some-repo", "other", "right-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data, self.INITIAL_JSON)

    def test_no_target_repo(self):
        leapp_configs.set_package_mapping("some", "unknown-repo", "other", "right-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data, self.INITIAL_JSON)


class RemovePackageActionTests(unittest.TestCase):
    INITIAL_JSON = {
        "packageinfo": [
            {
                "id": "1",
                "action": 1,
                "in_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "1",
                },
            },
            {
                "id": "2",
                "action": 4,
                "in_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "other-repo",
                        },
                    ],
                    "set_id": "3",
                },
            },
            {
                "id": "3",
                "action": 4,
                "in_packageset": {
                    "package": [
                        {
                            "name": "known",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "4",
                },
                "out_packageset": {
                    "package": [
                        {
                            "name": "unknown",
                            "repository": "other-repo",
                        },
                    ],
                    "set_id": "5",
                },
            },
            {
                "id": "4",
                "action": 4,
                "in_packageset": None,
                "out_packageset": None,
            },
            {
                "id": "6",
                "action": 1,
                "in_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "some-repo",
                        },
                    ],
                    "set_id": "1",
                },
            },
        ]
    }

    JSON_FILE_PATH = "leapp_upgrade_repositories.json"

    def setUp(self):
        with open(self.JSON_FILE_PATH, "w") as f:
            f.write(json.dumps(self.INITIAL_JSON, indent=4))

    def tearDown(self):
        if os.path.exists(self.JSON_FILE_PATH):
            os.remove(self.JSON_FILE_PATH)

    def test_remove_single_action(self):
        leapp_configs.remove_package_action("other", "other-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertTrue(all("2" != package["id"] for package in json_data["packageinfo"]))

    def test_remove_multiple_actions(self):
        leapp_configs.remove_package_action("some", "some-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertTrue(all("1" != package["id"] for package in json_data["packageinfo"]))
            self.assertTrue(all("6" != package["id"] for package in json_data["packageinfo"]))

    def test_no_target_package(self):
        leapp_configs.remove_package_action("no", "no-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data, self.INITIAL_JSON)

    def test_empty_json_target_package(self):
        if os.path.exists(self.JSON_FILE_PATH):
            os.remove(self.JSON_FILE_PATH)
        with open(self.JSON_FILE_PATH, "w") as f:
            f.write(json.dumps({}, indent=4))

        leapp_configs.remove_package_action("no", "no-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual({}, json_data)
