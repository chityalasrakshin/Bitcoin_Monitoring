"""CSV Parser for ChainSentry.
Parses blockchain transaction records and network observation records from CSV files or raw strings.
Enriches IP addresses with GeoIP and ASN metadata.
"""
import csv
import io
import json
import ast
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple, Union

from backend.chainsentry_common.schemas import NormalizedTxRecord, NetworkObservationRecord
from backend.chainsentry_common.logging import logger
from backend.ingestion_svc.connectors.geoip import resolve_ip

def _parse_list_field(val: Any) -> List[Any]:
    if not val:
        return []
    if isinstance(val, list):
        return val
    s = str(val).strip()
    if not s:
        return []
    # Try json parse
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    # Try ast.literal_eval
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    # Fallback to semicolon or comma split
    if ";" in s:
        return [item.strip().strip("'\"") for item in s.split(";") if item.strip()]
    if "," in s and not s.startswith("["):
        return [item.strip().strip("'\"") for item in s.split(",") if item.strip()]
    return [s.strip("[]'\"")]

def _parse_float_list(val: Any) -> List[float]:
    raw_list = _parse_list_field(val)
    res = []
    for x in raw_list:
        try:
            res.append(float(x))
        except (ValueError, TypeError):
            pass
    return res

def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    s = str(val).strip()
    # Normalize Z to +00:00
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return datetime.now(timezone.utc)

def parse_transactions_csv(content: Union[str, bytes]) -> List[NormalizedTxRecord]:
    """Parse transaction CSV into list of NormalizedTxRecord objects."""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(content))
    records: List[NormalizedTxRecord] = []

    for row_idx, row in enumerate(reader):
        try:
            txid = row.get("txid") or row.get("tx_id") or row.get("hash")
            if not txid:
                continue
            txid = txid.strip()

            ts = _parse_datetime(row.get("timestamp") or row.get("ts") or row.get("time"))
            input_addrs = [str(a) for a in _parse_list_field(row.get("input_addresses") or row.get("inputs"))]
            output_addrs = [str(a) for a in _parse_list_field(row.get("output_addresses") or row.get("outputs"))]
            input_amounts = _parse_float_list(row.get("input_amounts") or row.get("in_amounts"))
            output_amounts = _parse_float_list(row.get("output_amounts") or row.get("out_amounts"))

            fee = None
            raw_fee = row.get("fee")
            if raw_fee not in (None, "", "null"):
                try:
                    fee = float(raw_fee)
                except (ValueError, TypeError):
                    pass

            src_ip = row.get("src_ip")
            if src_ip:
                src_ip = src_ip.strip()
            dst_ip = row.get("dst_ip")
            if dst_ip:
                dst_ip = dst_ip.strip()

            src_port = None
            if row.get("src_port"):
                try:
                    src_port = int(row.get("src_port"))
                except ValueError:
                    pass

            dst_port = None
            if row.get("dst_port"):
                try:
                    dst_port = int(row.get("dst_port"))
                except ValueError:
                    pass

            geo_country = row.get("geo_country")
            asn = row.get("asn")
            if src_ip and (not geo_country or not asn):
                res_country, res_asn = resolve_ip(src_ip)
                geo_country = geo_country or res_country
                asn = asn or res_asn

            rec = NormalizedTxRecord(
                txid=txid,
                timestamp=ts,
                input_addresses=input_addrs,
                output_addresses=output_addrs,
                input_amounts=input_amounts,
                output_amounts=output_amounts,
                fee=fee,
                script_type=row.get("script_type") or "UNKNOWN",
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                geo_country=geo_country,
                asn=asn,
                source=row.get("source") or "synthetic",
                provenance=row.get("provenance"),
                dataset_id=row.get("dataset_id")
            )
            records.append(rec)
        except Exception as e:
            logger.warning(f"Error parsing transaction CSV row {row_idx}: {e}")
            continue

    logger.info(f"Successfully parsed {len(records)} transactions from CSV")
    return records

def parse_network_observations_csv(content: Union[str, bytes]) -> List[NetworkObservationRecord]:
    """Parse network observations CSV into list of NetworkObservationRecord objects."""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(content))
    records: List[NetworkObservationRecord] = []

    for row_idx, row in enumerate(reader):
        try:
            obs_id = row.get("observation_id") or row.get("obs_id") or f"obs-{row_idx}"
            txid = row.get("txid") or row.get("tx_id")
            src_ip = row.get("src_ip") or row.get("peer_ip") or row.get("ip")
            if not txid or not src_ip:
                continue

            ts = _parse_datetime(row.get("timestamp") or row.get("ts"))
            dst_ip = row.get("dst_ip")

            src_port = None
            if row.get("src_port"):
                try:
                    src_port = int(row.get("src_port"))
                except ValueError:
                    pass

            dst_port = None
            if row.get("dst_port"):
                try:
                    dst_port = int(row.get("dst_port"))
                except ValueError:
                    pass

            country, asn = resolve_ip(src_ip)

            rec = NetworkObservationRecord(
                observation_id=obs_id,
                timestamp=ts,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                txid=txid,
                provenance=row.get("provenance"),
                dataset_id=row.get("dataset_id"),
                geo_country=row.get("geo_country") or country,
                asn=row.get("asn") or asn
            )
            records.append(rec)
        except Exception as e:
            logger.warning(f"Error parsing network observation CSV row {row_idx}: {e}")
            continue

    logger.info(f"Successfully parsed {len(records)} network observations from CSV")
    return records
