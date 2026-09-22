"""XML Parser for ChainSentry.
Parses XML files with <transaction> or <network_observation> nodes.
"""
import xml.etree.ElementTree as ET
from typing import List, Union
from backend.chainsentry_common.schemas import NormalizedTxRecord, NetworkObservationRecord
from backend.chainsentry_common.logging import logger
from backend.ingestion_svc.connectors.geoip import resolve_ip
from backend.ingestion_svc.parsers.csv_parser import _parse_datetime

def parse_transactions_xml(content: Union[str, bytes]) -> List[NormalizedTxRecord]:
    if isinstance(content, str):
        content = content.encode("utf-8")

    root = ET.fromstring(content)
    records: List[NormalizedTxRecord] = []

    for elem in root.findall(".//transaction"):
        try:
            txid = elem.findtext("txid") or elem.findtext("tx_id")
            if not txid:
                continue

            ts = _parse_datetime(elem.findtext("timestamp") or elem.findtext("ts"))
            in_addrs = [e.text for e in elem.findall(".//input_address") if e.text]
            out_addrs = [e.text for e in elem.findall(".//output_address") if e.text]
            in_amounts = [float(e.text) for e in elem.findall(".//input_amount") if e.text]
            out_amounts = [float(e.text) for e in elem.findall(".//output_amount") if e.text]

            fee_text = elem.findtext("fee")
            fee = float(fee_text) if fee_text else None
            script_type = elem.findtext("script_type") or "UNKNOWN"
            src_ip = elem.findtext("src_ip")
            dst_ip = elem.findtext("dst_ip")

            country, asn = resolve_ip(src_ip)

            rec = NormalizedTxRecord(
                txid=txid.strip(),
                timestamp=ts,
                input_addresses=in_addrs,
                output_addresses=out_addrs,
                input_amounts=in_amounts,
                output_amounts=out_amounts,
                fee=fee,
                script_type=script_type,
                src_ip=src_ip,
                dst_ip=dst_ip,
                geo_country=country,
                asn=asn,
                source="manual_upload"
            )
            records.append(rec)
        except Exception as e:
            logger.warning(f"Error parsing XML transaction element: {e}")
            continue

    logger.info(f"Successfully parsed {len(records)} transactions from XML")
    return records
