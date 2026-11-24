# Copyright 2026. WebPros International GmbH. All rights reserved.
import os
import stat
import tempfile
import unittest

import src.mailman as mailman


class MailmanWebAccountMiddlewareTests(unittest.TestCase):

    # The form the Plesk bootstrapper writes into /etc/mailman3/mailman-web.py on Debian 12
    PLESK_CONFIG = """\
SECRET_KEY = 'secret'

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django_mailman3.middleware.TimezoneMiddleware',
    'postorius.middleware.PostoriusMiddleware',
    'plesk_django_overrides.PleskMiddleware',
)

USE_X_FORWARDED_HOST = True
"""

    FIXED_PLESK_CONFIG = PLESK_CONFIG.replace(
        "MIDDLEWARE = (\n",
        "MIDDLEWARE = (\n    'allauth.account.middleware.AccountMiddleware',\n",
    )

    ONE_LINE_CONFIG = "MIDDLEWARE = ('django.middleware.common.CommonMiddleware', 'plesk_django_overrides.PleskMiddleware')\n"

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.config = os.path.join(self.tmp_dir.name, "mailman-web.py")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def lacks(self, content):
        with open(self.config, "w") as f:
            f.write(content)
        return mailman.config_lacks_middleware(mailman.ALLAUTH_ACCOUNT_MIDDLEWARE, self.config)

    def add(self, content):
        with open(self.config, "w") as f:
            f.write(content)
        mailman.add_middleware(mailman.ALLAUTH_ACCOUNT_MIDDLEWARE, self.config)
        with open(self.config) as f:
            return f.read()

    def test_missing_config_is_not_reported(self):
        self.assertFalse(mailman.config_lacks_middleware(mailman.ALLAUTH_ACCOUNT_MIDDLEWARE, self.config))

    def test_plesk_tuple_without_account_middleware(self):
        self.assertTrue(self.lacks(self.PLESK_CONFIG))

    def test_plesk_tuple_with_account_middleware(self):
        self.assertFalse(self.lacks(self.FIXED_PLESK_CONFIG))

    def test_list_without_account_middleware(self):
        content = self.PLESK_CONFIG.replace("MIDDLEWARE = (", "MIDDLEWARE = [").replace("\n)\n", "\n]\n")
        self.assertTrue(self.lacks(content))

    def test_config_without_middleware_is_not_reported(self):
        self.assertFalse(self.lacks("SECRET_KEY = 'secret'\nUSE_X_FORWARDED_HOST = True\n"))

    def test_one_line_assignment_is_not_reported(self):
        self.assertFalse(self.lacks(self.ONE_LINE_CONFIG))

    def test_extending_assignment_is_not_reported(self):
        content = "MIDDLEWARE += (\n    'plesk_django_overrides.PleskMiddleware',\n)\n"
        self.assertFalse(self.lacks(content))

    def test_commented_out_middleware_is_not_reported(self):
        self.assertFalse(self.lacks("# MIDDLEWARE = (\n#     'plesk_django_overrides.PleskMiddleware',\n# )\n"))

    def test_add_to_plesk_tuple(self):
        self.assertEqual(self.add(self.PLESK_CONFIG), self.FIXED_PLESK_CONFIG)

    def test_add_to_list(self):
        content = "MIDDLEWARE = [\n    'plesk_django_overrides.PleskMiddleware',\n]\n"
        self.assertEqual(
            self.add(content),
            "MIDDLEWARE = [\n    'allauth.account.middleware.AccountMiddleware',\n    'plesk_django_overrides.PleskMiddleware',\n]\n",
        )

    def test_other_middleware_is_reported_and_added(self):
        other = "example.middleware.OtherMiddleware"
        with open(self.config, "w") as f:
            f.write(self.FIXED_PLESK_CONFIG)

        self.assertTrue(mailman.config_lacks_middleware(other, self.config))
        mailman.add_middleware(other, self.config)

        with open(self.config) as f:
            self.assertEqual(f.read(), self.FIXED_PLESK_CONFIG.replace("MIDDLEWARE = (\n", f"MIDDLEWARE = (\n    '{other}',\n"))

    def test_add_to_one_line_assignment_keeps_config(self):
        self.assertEqual(self.add(self.ONE_LINE_CONFIG), self.ONE_LINE_CONFIG)

    def test_add_keeps_file_and_mode(self):
        # The config holds the secret key and is readable by the web server group only
        with open(self.config, "w") as f:
            f.write(self.PLESK_CONFIG)
        os.chmod(self.config, 0o640)
        inode = os.stat(self.config).st_ino

        mailman.add_middleware(mailman.ALLAUTH_ACCOUNT_MIDDLEWARE, self.config)

        st = os.stat(self.config)
        self.assertEqual(st.st_ino, inode)
        self.assertEqual(stat.S_IMODE(st.st_mode), 0o640)
