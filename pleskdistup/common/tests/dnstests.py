# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import shutil
import os
import unittest

import src.dns as dns


class TestGetIncludeFromBindConfiguration(unittest.TestCase):

    def tearDown(self):
        if os.path.exists("test.conf"):
            os.remove("test.conf")

        if os.path.exists("chroot"):
            shutil.rmtree("chroot")

    def test_no_config_file(self):
        with open("test.conf", "w") as test_bind_config:
            test_bind_config.write('''
options {
    allow-recursion {
        localnets;
    };
    directory "/var";
    pid-file "/var/run/named/named.pid";
};
''')
        self.assertEqual(dns.get_all_includes_from_bind_config("nonexistent.conf"), [])

    def test_one_include(self):
        with open("test.conf", "w") as test_file:
            test_file.write('''
options {
    include "/included.conf";
    allow-recursion {
        localnets;
    };
    directory "/var";
    pid-file "/var/run/named/named.pid";
};
''')

        self.assertEqual(dns.get_all_includes_from_bind_config("test.conf"), ["/included.conf"])

    def test_include_with_spaces(self):
        with open("test.conf", "w") as test_file:
            test_file.write('''
options {
    include    "/included   .conf"  ;  # comment
    allow-recursion {
        localnets;
    };
    directory "/var";
    pid-file "/var/run/named/named.pid";
};
''')
        self.assertEqual(dns.get_all_includes_from_bind_config("test.conf"), ["/included   .conf"])

    def test_include_with_tabs(self):
        with open("test.conf", "w") as test_file:
            test_file.write('''
options {
    include	"/included	.conf"	;
    allow-recursion {
        localnets;
    };
    directory "/var";
    pid-file "/var/run/named/named.pid";
};
''')
        self.assertEqual(dns.get_all_includes_from_bind_config("test.conf"), ["/included	.conf"])

    def test_multiple_includes(self):
        with open("test.conf", "w") as test_file:
            test_file.write('''
options {
    include "/included1.conf";
    include "/included2.conf";
    allow-recursion {
        localnets;
    };
    directory "/var";
    pid-file "/var/run/named/named.pid";
};
''')

        self.assertEqual(dns.get_all_includes_from_bind_config("test.conf"), ["/included1.conf", "/included2.conf"])

    def test_nested_includes(self):
        current_dir = os.getcwd()
        with open("test.conf", "w") as test_file:
            test_file.write(f'''
options {{
    include "{current_dir}/included1.conf";
    include "{current_dir}/included2.conf";
    allow-recursion {{
        localnets;
    }};
    directory "/var";
    pid-file "/var/run/named/named.pid";
}};
''')

        with open("included1.conf", "w") as test_file:
            test_file.write(f'include "{current_dir}/included3.conf";\n')

        with open("included2.conf", "w") as test_file:
            test_file.write(f'include "{current_dir}/included4.conf";\n')

        self.assertEqual(dns.get_all_includes_from_bind_config("test.conf"), [f"{current_dir}/included1.conf",
                                                                              f"{current_dir}/included2.conf",
                                                                              f"{current_dir}/included3.conf",
                                                                              f"{current_dir}/included4.conf"])

        os.remove("included1.conf")
        os.remove("included2.conf")

    def test_chroot_with_absolute_path(self):
        os.makedirs("chroot", exist_ok=True)

        with open("chroot/test.conf", "w") as test_file:
            test_file.write('''
options {
    include "/included.conf";
    allow-recursion {
        localnets;
    };
    directory "/var";
    pid-file "/var/run/named/named.pid";
};
''')
        self.assertEqual(dns.get_all_includes_from_bind_config("/test.conf", chroot_dir="chroot"), ["chroot/included.conf"])

    def test_nested_includes_with_chroot(self):
        os.makedirs("chroot", exist_ok=True)

        with open("chroot/test.conf", "w") as test_file:
            test_file.write('''
options {
    include "/included1.conf";
    include "/included2.conf";
    allow-recursion {
        localnets;
    };
    directory "/var";
    pid-file "/var/run/named/named.pid";
};
''')

        with open("chroot/included1.conf", "w") as test_file:
            test_file.write('include "/subdir/included3.conf";\n')

        with open("chroot/included2.conf", "w") as test_file:
            test_file.write('include "/subdir/included4.conf";\n')

        self.assertEqual(dns.get_all_includes_from_bind_config("test.conf", chroot_dir="chroot"), [
            "chroot/included1.conf",
            "chroot/included2.conf",
            "chroot/subdir/included3.conf",
            "chroot/subdir/included4.conf"
        ])
