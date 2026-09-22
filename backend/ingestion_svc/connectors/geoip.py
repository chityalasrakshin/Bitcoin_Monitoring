"""ChainSentry GeoIP Connector.
Provides offline IP geolocation and ASN resolution using local fixtures and MaxMind GeoLite2 databases.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from backend.chainsentry_common.config import settings
from backend.chainsentry_common.logging import logger

class GeoIPResolver:
    _instance: Optional["GeoIPResolver"] = None
    _fixture_cache: Dict[str, Dict[str, str]] = {}
    _reader_city = None
    _reader_asn = None

    def __init__(self):
        self._load_fixture()
        self._load_mmdb()

    @classmethod
    def get_instance(cls) -> "GeoIPResolver":
        if cls._instance is None:
            cls._instance = GeoIPResolver()
        return cls._instance

    def _load_fixture(self):
        fixture_path = settings.GEOIP_DATA_DIR / "geoip_fixture.json"
        if not fixture_path.exists():
            fixture_path = settings.REFERENCE_DATA_DIR / "geoip_fixture.json"

        if fixture_path.exists():
            try:
                with open(fixture_path, "r", encoding="utf-8") as f:
                    self._fixture_cache = json.load(f)
                logger.info(f"Loaded {len(self._fixture_cache)} GeoIP fixture entries from {fixture_path.name}")
            except Exception as e:
                logger.warning(f"Could not load GeoIP fixture: {e}")

    def _load_mmdb(self):
        city_mmdb = settings.GEOIP_DATA_DIR / "GeoLite2-City.mmdb"
        asn_mmdb = settings.GEOIP_DATA_DIR / "GeoLite2-ASN.mmdb"
        try:
            import geoip2.database
            if city_mmdb.exists():
                self._reader_city = geoip2.database.Reader(str(city_mmdb))
            if asn_mmdb.exists():
                self._reader_asn = geoip2.database.Reader(str(asn_mmdb))
        except Exception:
            pass

    def lookup(self, ip: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Resolve IP address to (geo_country, asn). Returns (None, None) if unresolved."""
        if not ip:
            return None, None

        ip = ip.strip()

        # 1. Check offline fixture cache
        if ip in self._fixture_cache:
            entry = self._fixture_cache[ip]
            return entry.get("geo_country"), entry.get("asn")

        # 2. Check MMDB reader if available
        country = None
        asn = None
        if self._reader_city:
            try:
                resp = self._reader_city.city(ip)
                country = resp.country.iso_code
            except Exception:
                pass

        if self._reader_asn:
            try:
                resp = self._reader_asn.asn(ip)
                asn = f"AS{resp.autonomous_system_number}"
            except Exception:
                pass

        if country or asn:
            return country, asn

        # Default fallback for private / testnet IPs
        if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16."):
            return "INTERNAL", "AS-PRIVATE"

        return "XX", "AS-UNKNOWN"

def resolve_ip(ip: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    return GeoIPResolver.get_instance().lookup(ip)
