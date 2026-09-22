"""JSON Parser for ChainSentry.
Parses JSON arrays and ndjson streams of transactions or network observations.
"""
import json
from typing import Any, List, Union
from backend.chainsentry_common.schemas import NormalizedTxRecord, NetworkObservationRecord
from backend.chainsentry_common.logging import logger
from backend.ingestion_svc.connectors.geoip import resolve_ip
from backend.ingestion_svc.parsers.csv_parser import _parse_datetime

def parse_transactions_json(content: Union[str, bytes]) -> List[NormalizedTxRecord]:
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try ndjson
        data = [json.loads(line) for line in content.splitlines() if line.strip()]

    if isinstance(data, dict) and "transactions" in data:
        data = data["transactions"]
    elif isinstance(data, dict):
        data = [data]

    records: List[NormalizedTxRecord] = []
    for item in data:
        try:
            txid = item.get("txid") or item.get("tx_id")
            if not txid:
                continue
            src_ip = item.get("src_ip")
            country = item.get("geo_country")
            asn = item.get("asn")
            if src_ip and (not country or not asn):
                res_c, res_a = resolve_ip(src_ip)
                country = country or res_c
                asn = asn or res_a

            rec = NormalizedTxRecord(
                txid=txid,
                timestamp=_parse_datetime(item.get("timestamp")),
                input_addresses=item.get("input_addresses") or [],
                output_addresses=item.get("output_addresses") or [],
                input_amounts=[float(x) for x in item.get("input_amounts", [])],
                output_amounts=[float(x) for x in item.get("output_amounts", [])],
                fee=float(item["fee"]) if item.get("fee") is not None else None,
                script_type=item.get("script_type") or "UNKNOWN",
                src_ip=src_ip,
                dst_ip=item.get("dst_ip"),
                src_port=item.get("src_port"),
                dst_port=item.get("dst_port"),
                geo_country=country,
                asn=asn,
                source=item.get("source") or "synthetic",
                provenance=item.get("provenance"),
                dataset_id=item.get("dataset_id")
            )
            records.append(rec)
        except Exception as e:
            logger.warning(f"Error parsing transaction JSON item: {e}")
            continue

    logger.info(f"Successfully parsed {len(records)} transactions from JSON")
    return records

def parse_network_observations_json(content: Union[str, bytes]) -> List[NetworkObservationRecord]:
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in content.splitlines() if line.strip()]

    if isinstance(data, dict) and "observations" in data:
        data = data["observations"]
    elif isinstance(data, dict):
        data = [data]

    records: List[NetworkObservationRecord] = []
    for idx, item in enumerate(data):
        try:
            obs_id = item.get("observation_id") or f"obs-{idx}"
            txid = item.get("txid")
            src_ip = item.get("src_ip")
            if not txid or not src_ip:
                continue

            country, asn = resolve_ip(src_ip)
            rec = NetworkObservationRecord(
                observation_id=obs_id,
                timestamp=_parse_datetime(item.get("timestamp")),
                src_ip=src_ip,
                dst_ip=item.get("dst_ip"),
                src_port=item.get("src_port"),
                dst_port=item.get("dst_port"),
                txid=txid,
                provenance=item.get("provenance"),
                dataset_id=item.get("dataset_id"),
                geo_country=item.get("geo_country") or country,
                asn=item.get("asn") or asn
            )
            records.append(rec)
        except Exception as e:
            logger.warning(f"Error parsing network observation JSON item: {e}")
            continue

    logger.info(f"Successfully parsed {len(records)} network observations from JSON")
    return records
