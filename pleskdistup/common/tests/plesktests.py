# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import unittest

from src import dist, plesk, version


class TestProductsFileParser(unittest.TestCase):

    def test_simple_parce(self):
        simple_data = """
<vendors>
    <vendor id="swsoft">
    <products>
        <product id="plesk" name="Plesk" reference="pool/PSA_18.0.60_14244/release.inf3" release-key="plesk-18.0.60"/>
        <addon id="wpb-18.0.59" name="WPB 18.0.59" reference="pool/WPB_18.0.59_77/release.inf3"/>
        <product id="plesk" name="Plesk" reference="pool/PSA_18.0.59_14022/release.inf3" release-key="plesk-18.0.59"/>
        <product id="plesk" name="Plesk" reference="pool/PSA_18.0.58_13749/release.inf3" release-key="plesk-18.0.58"/>
        <addon id="php83" name="PHP v 8.3" reference="PHP83_17/release.inf3"/>
        <product id="plesk" name="Plesk" reference="pool/PSA_18.0.57_13503/release.inf3" release-key="plesk-18.0.57"/>
        <product id="plesk" name="Plesk" reference="pool/PSA_18.0.56_13177/release.inf3" release-key="plesk-18.0.56"/>
        <addon id="wpb-18.0.55" name="WPB 18.0.55" reference="pool/WPB_18.0.55_74/release.inf3"/>
        <product id="plesk" name="Plesk" reference="pool/PSA_18.0.55_12738/release.inf3" release-key="plesk-18.0.55"/>
        <addon id="wpb-18.0.51" name="WPB 18.0.51" reference="pool/WPB_18.0.51_64/release.inf3"/>
        <addon id="php82" name="PHP v 8.2" reference="PHP82_17/release.inf3"/>
        <addon id="php82" name="PHP v 8.2 (EOL OSes)" reference="php82.inf3"/>
        <addon id="php81" name="PHP v 8.1" reference="PHP81_17/release.inf3"/>
        <addon id="php81" name="PHP v 8.1 (EOL OSes)" reference="php81.inf3"/>
        <addon id="php80" name="PHP v 8.0" reference="PHP80_17/release.inf3"/>
        <addon id="php80" name="PHP v 8.0 (EOL OSes)" reference="php80.inf3"/>
        <addon id="php72" name="PHP v 72 (EOL)" reference="php72.inf3"/>
        <addon id="php74" name="PHP v 7.4" reference="PHP74_17/release.inf3"/>
        <addon id="php74" name="PHP v 7.4 (EOL OSes)" reference="php74.inf3"/>
        <addon id="php73" name="PHP v 73 (EOL)" reference="php73.inf3"/>
        <addon id="php71" name="PHP v 71 (EOL)" reference="php71.inf3"/>
        <product id="plesk" name="Plesk" reference="plesk.inf3"/>
        <product id="sitebuilder" name="Sitebuilder 4.5 and earlier versions (for Plesk 9 and earlier)" reference="sitebuilder.inf3"/>
        <addon id="setemplates" name="SiteEditor templates" reference="setemplates.inf3"/>
        <addon id="pp-sitebuilder" name="Sitebuilder" reference="pp-sitebuilder.inf3"/>
        <addon id="billing" name="Paralllels billing" reference="billing.inf3"/>
        <lazy_addon id="mysql5.1" name="MySQL v 5.1" reference="mysql.inf3"/>
        <lazy_addon id="apache" name="Apache with SNI support" reference="apache.inf3"/>
        <lazy_addon id="nginx" name="NGINX reverse proxy server" reference="nginx.inf3"/>
        <addon id="php70" name="PHP v 7.0" reference="php70.inf3"/>
        <addon id="php56" name="PHP v 5.6" reference="php56.inf3"/>
        <addon id="php55" name="PHP v 5.5" reference="php55.inf3"/>
        <addon id="php54" name="PHP v 5.4" reference="php54.inf3"/>
        <addon id="php53" name="PHP v 5.3" reference="php53.inf3"/>
        <addon id="php52" name="PHP v 5.2" reference="php52.inf3"/>
        <addon id="pmm" name="Panel migrator" reference="pmm.inf3"/>
    </products>
    </vendor>
</vendors>
"""
        expected_versions = [version.PleskVersion(ver) for ver in ["18.0.55", "18.0.56", "18.0.57", "18.0.58", "18.0.59", "18.0.60"]]
        self.assertEqual(expected_versions, sorted(plesk.extract_plesk_versions(simple_data)))

    def test_empty_data(self):
        self.assertEqual([], plesk.extract_plesk_versions(""))

    def test_no_plesk_prudict(self):
        data = """
<vendors>
    <vendor id="swsoft">
    <products>
        <addon id="php70" name="PHP v 7.0" reference="php70.inf3"/>
        <addon id="php56" name="PHP v 5.6" reference="php56.inf3"/>
        <addon id="php55" name="PHP v 5.5" reference="php55.inf3"/>
        <addon id="php54" name="PHP v 5.4" reference="php54.inf3"/>
        <addon id="php53" name="PHP v 5.3" reference="php53.inf3"/>
        <addon id="php52" name="PHP v 5.2" reference="php52.inf3"/>
        <addon id="pmm" name="Panel migrator" reference="pmm.inf3"/>
    </products>
    </vendor>
</vendors>
"""

        self.assertEqual([], plesk.extract_plesk_versions(data))

    def test_only_plesk_without_release_key(self):
        data = """
<vendors>
    <vendor id="swsoft">
    <products>
        <product id="plesk" name="Plesk" reference="plesk.inf3"/>
    </products>
    </vendor>
</vendors>
"""

        self.assertEqual([], plesk.extract_plesk_versions(data))


class TestGetRepositoryByOsFromInf3(unittest.TestCase):
    DEFAULT_TEST_DATA = """
<addon id="php73" name="PHP v 7.3">
<release id="PHP_7_3" name="PHP v 7.3" version="7.3.33">
<compatibility_info>
<compatible product_id="plesk" from_version="17.8.11" to_version="18.0.99"/>
</compatibility_info>
<build os_name="Linux" os_vendor="Debian" os_version="11.0" os_arch="x86_64" config="pool/PHP_7.3.33_13/php73-deb11.0-x86_64.inf3"/>
<build os_name="Linux" os_vendor="Ubuntu" os_version="22.04" os_arch="x86_64" config="pool/PHP_7.3.33_13/php73-ubt22.04-x86_64.inf3"/>
</release>
<release id="PHP73_17" name="PHP v 7.3" version="7.3">
<compatibility_info>
<compatible product_id="plesk" from_version="17.8.11" to_version="18.0.99"/>
</compatibility_info>
<build os_name="Linux" os_vendor="AlmaLinux" os_version="8" os_arch="x86_64" config="pool/PHP_7.3.33_248/php73-cos8-x86_64.inf3"/>
<build os_name="Linux" os_vendor="CentOS" os_version="7" os_arch="x86_64" config="pool/PHP_7.3.33_248/php73-cos7-x86_64.inf3"/>
<build os_name="Linux" os_vendor="CentOS" os_version="8" os_arch="x86_64" config="pool/PHP_7.3.33_248/php73-cos8-x86_64.inf3"/>
<build os_name="Linux" os_vendor="Ubuntu" os_version="20.04" os_arch="x86_64" config="pool/PHP_7.3.33_248/php73-ubt20.04-x86_64.inf3"/>
</release>
</addon>
"""

    def test_first_release_parsing(self):
        self.assertEqual("pool/PHP_7.3.33_13", plesk.get_repository_by_os_from_inf3(self.DEFAULT_TEST_DATA, dist.Ubuntu("22")))

    def test_second_release_parsing(self):
        self.assertEqual("pool/PHP_7.3.33_248", plesk.get_repository_by_os_from_inf3(self.DEFAULT_TEST_DATA, dist.Ubuntu("20")))

    def test_first_release_from_xml_object(self):
        import xml.etree.ElementTree as ElementTree
        root = ElementTree.fromstring(self.DEFAULT_TEST_DATA)
        self.assertEqual("pool/PHP_7.3.33_13", plesk.get_repository_by_os_from_inf3(root, dist.Ubuntu("22")))

    def test_no_such_release(self):
        self.assertEqual(None, plesk.get_repository_by_os_from_inf3(self.DEFAULT_TEST_DATA, dist.Ubuntu("21")))

    def test_empty_xml(self):
        self.assertEqual(None, plesk.get_repository_by_os_from_inf3("", dist.Ubuntu("22")))
