# Copyright 2026. WebPros International GmbH. All rights reserved.
import unittest

import src.dnssec as dnssec


class GroupSigningKeysTests(unittest.TestCase):

    CURRENT_KSK = "example.com\tKSK\tcurrent\tKexample.com.+013+48440\tECDSAP256SHA256\t2048"
    CURRENT_ZSK = "example.com\tZSK\tcurrent\tKexample.com.+013+63599\tECDSAP256SHA256\t1024"
    NEXT_KSK = "example.com\tKSK\tnext\tKexample.com.+013+08986\tECDSAP256SHA256\t2048"
    ROWS = [CURRENT_KSK, CURRENT_ZSK, NEXT_KSK]

    def test_complete_zone(self):
        zones = dnssec._group_signing_keys(self.ROWS)
        self.assertEqual(zones.incomplete, [])
        self.assertEqual([zone.fqdn for zone in zones.complete], ["example.com"])
        self.assertEqual(zones.complete[0].dnsmng_sign_args(), [
            "--sign", "example.com",
            "--zsk", "Kexample.com.+013+63599",
            "--ksk1", "Kexample.com.+013+48440",
            "--ksk2", "Kexample.com.+013+08986",
            "--ktype", "ZSK", "--kalg", "ECDSAP256SHA256", "--ksize", "1024",
            "--ktype", "KSK", "--kalg", "ECDSAP256SHA256", "--ksize", "2048",
        ])

    def test_sign_args_take_zsk_props_from_current_zsk_and_ksk_props_from_next_ksk(self):
        rows = [
            "example.com\tKSK\tcurrent\tKexample.com.+008+00001\tRSASHA256\t2048",
            "example.com\tZSK\tcurrent\tKexample.com.+010+00002\tRSASHA512\t1024",
            "example.com\tKSK\tnext\tKexample.com.+014+00003\tECDSAP384SHA384\t4096",
        ]
        zones = dnssec._group_signing_keys(rows)
        self.assertEqual(zones.complete[0].dnsmng_sign_args(), [
            "--sign", "example.com",
            "--zsk", "Kexample.com.+010+00002",
            "--ksk1", "Kexample.com.+008+00001",
            "--ksk2", "Kexample.com.+014+00003",
            "--ktype", "ZSK", "--kalg", "RSASHA512", "--ksize", "1024",
            "--ktype", "KSK", "--kalg", "ECDSAP384SHA384", "--ksize", "4096",
        ])

    def test_zone_missing_any_required_key_is_incomplete(self):
        for missing in self.ROWS:
            with self.subTest(missing=missing):
                zones = dnssec._group_signing_keys([row for row in self.ROWS if row != missing])
                self.assertEqual(zones.complete, [])
                self.assertEqual(zones.incomplete, ["example.com"])

    def test_signed_zone_without_keys(self):
        # LEFT JOIN from the zones table yields NULL key columns
        zones = dnssec._group_signing_keys(["nokeys.com\tNULL\tNULL\tNULL\tNULL\tNULL"])
        self.assertEqual(zones.complete, [])
        self.assertEqual(zones.incomplete, ["nokeys.com"])

    def test_key_type_matched_exactly(self):
        rows = [row.replace("\tKSK\t", "\tksk\t").replace("\tZSK\t", "\tzsk\t") for row in self.ROWS]
        zones = dnssec._group_signing_keys(rows)
        self.assertEqual(zones.complete, [])
        self.assertEqual(zones.incomplete, ["example.com"])

    def test_key_status_matched_exactly(self):
        rows = [row.replace("\tcurrent\t", "\tCurrent\t").replace("\tnext\t", "\tNext\t") for row in self.ROWS]
        zones = dnssec._group_signing_keys(rows)
        self.assertEqual(zones.complete, [])
        self.assertEqual(zones.incomplete, ["example.com"])

    def test_interleaved_zones_grouped_and_sorted(self):
        zone_a = [row.replace("example.com", "a.example.org") for row in self.ROWS]
        zone_b = [row.replace("example.com", "b.example.org") for row in self.ROWS[:2]]
        zone_c = [row.replace("example.com", "c.example.net") for row in self.ROWS]
        # plesk db returns rows without ORDER BY, so keys of different zones may come mixed
        rows = [zone_c[0], zone_a[0], zone_b[0], zone_c[1], zone_a[1], zone_b[1], zone_a[2], zone_c[2]]
        zones = dnssec._group_signing_keys(rows)
        self.assertEqual([zone.fqdn for zone in zones.complete], ["a.example.org", "c.example.net"])
        self.assertEqual(zones.incomplete, ["b.example.org"])

    def test_no_rows(self):
        self.assertEqual(dnssec._group_signing_keys([]), dnssec.SignedZones([], []))
