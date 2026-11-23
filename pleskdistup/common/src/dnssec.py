# Copyright 2026. WebPros International GmbH. All rights reserved.
"""Zones signed by the Plesk DNSSEC extension and their signing keys."""
import subprocess
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from . import log, plesk


class SigningKey(NamedTuple):
    name: str
    algorithm: str
    size: str


class ZoneKeys(NamedTuple):
    fqdn: str
    zsk: SigningKey
    ksk: SigningKey
    next_ksk: SigningKey

    def dnsmng_sign_args(self) -> List[str]:
        # Re-sign the same way the DNSSEC extension does it.
        # We have to do a full re-signing with full arguments to avoid key re-creation,
        # which will be triggered if we use `plesk ext dnssec sign`.
        return [
            "--sign", self.fqdn,
            "--zsk", self.zsk.name,
            "--ksk1", self.ksk.name,
            "--ksk2", self.next_ksk.name,
            "--ktype", "ZSK", "--kalg", self.zsk.algorithm, "--ksize", self.zsk.size,
            "--ktype", "KSK", "--kalg", self.next_ksk.algorithm, "--ksize", self.next_ksk.size,
        ]


class SignedZones(NamedTuple):
    # Zones with the complete key set (current ZSK, current KSK and next KSK), sorted by name
    complete: List[ZoneKeys]
    # Names of signed zones where the key set is incomplete, sorted
    incomplete: List[str]


def _group_signing_keys(rows: Iterable[str]) -> SignedZones:
    """Group signing keys of the Plesk DNSSEC extension by zone.

    Each row is a tab separated line: fqdn, key type (KSK/ZSK), key status (current/next), key name,
    algorithm, size. A signed zone without keys comes as a row with NULL key columns.
    """
    found: Dict[str, Dict[Tuple[str, str], SigningKey]] = {}
    for row in rows:
        fqdn, key_type, status, name, algorithm, size = row.split("\t")
        found.setdefault(fqdn, {})[(key_type, status)] = SigningKey(name, algorithm, size)

    complete: List[ZoneKeys] = []
    incomplete: List[str] = []
    for fqdn, keys in sorted(found.items()):
        zsk = keys.get(("ZSK", "current"))
        ksk = keys.get(("KSK", "current"))
        next_ksk = keys.get(("KSK", "next"))
        if zsk is None or ksk is None or next_ksk is None:
            log.warn(f"DNSSEC signing keys for zone {fqdn!r} are incomplete")
            incomplete.append(fqdn)
            continue
        complete.append(ZoneKeys(fqdn, zsk, ksk, next_ksk))

    return SignedZones(complete, incomplete)


def get_signed_zones() -> Optional[SignedZones]:
    """Return zones the Plesk DNSSEC extension marks as signed, or None if they can't be retrieved."""
    try:
        rows = plesk.get_from_plesk_database(
            "SELECT z.fqdn, k.type, k.status, k.name, k.encryptAlgorithm, k.size "
            "FROM module_dnssec_dnsZone z "
            "LEFT JOIN module_dnssec_signingKey k "
            "ON k.dnsZoneFqdn = z.fqdn AND k.status IN ('current', 'next') "
            "WHERE z.status = 'signed'"
        )
    except subprocess.CalledProcessError as ex:
        log.warn(f"Unable to get DNS zones signed by the DNSSEC extension: {ex}")
        return None

    if rows is None:
        return None
    return _group_signing_keys(rows)
