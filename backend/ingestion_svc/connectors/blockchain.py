"""ChainSentry Live Blockchain Connector.
Queries public Bitcoin block explorers (mempool.space and blockstream.info)
to dynamically fetch real-time on-chain transactions and UTXO metadata for any
address or transaction hash without requiring an API key.
"""
from datetime import datetime, timezone
import time
from typing import List, Optional
import httpx

from backend.chainsentry_common.schemas import NormalizedTxRecord, ScriptType, SourceEnum
from backend.chainsentry_common.logging import logger

API_ENDPOINTS = [
    "https://mempool.space/api",
    "https://blockstream.info/api"
]

class LiveBlockchainConnector:
    """Connects to live Bitcoin explorer REST APIs for dynamic transaction retrieval."""

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    def _determine_script_type(self, address: str) -> str:
        """Infer Bitcoin script type from address encoding."""
        if not address:
            return ScriptType.UNKNOWN.value
        if address.startswith("bc1q") and len(address) == 42:
            return ScriptType.P2WPKH.value
        if address.startswith("bc1q") and len(address) == 62:
            return ScriptType.P2WSH.value
        if address.startswith("bc1p"):
            return ScriptType.P2TR.value
        if address.startswith("1"):
            return ScriptType.P2PKH.value
        if address.startswith("3"):
            return ScriptType.P2SH.value
        return ScriptType.UNKNOWN.value

    def _parse_mempool_tx(self, raw_tx: dict) -> NormalizedTxRecord:
        """Parse mempool.space / blockstream.info JSON format into NormalizedTxRecord."""
        txid = raw_tx.get("txid", "")
        status = raw_tx.get("status", {})
        block_time = status.get("block_time")
        if block_time:
            ts = datetime.fromtimestamp(block_time, tz=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        input_addresses: List[str] = []
        input_amounts: List[float] = []
        for vin in raw_tx.get("vin", []):
            prevout = vin.get("prevout")
            if prevout:
                addr = prevout.get("scriptpubkey_address")
                val_sat = prevout.get("value", 0)
                if addr:
                    input_addresses.append(addr)
                    input_amounts.append(round(val_sat / 1e8, 8))
            elif vin.get("is_coinbase"):
                input_addresses.append("coinbase")
                input_amounts.append(0.0)

        output_addresses: List[str] = []
        output_amounts: List[float] = []
        for vout in raw_tx.get("vout", []):
            addr = vout.get("scriptpubkey_address")
            val_sat = vout.get("value", 0)
            if addr:
                output_addresses.append(addr)
                output_amounts.append(round(val_sat / 1e8, 8))

        fee_sat = raw_tx.get("fee", 0)
        fee_btc = round(fee_sat / 1e8, 8) if fee_sat else 0.0

        sample_addr = (output_addresses[0] if output_addresses else
                       (input_addresses[0] if input_addresses else ""))
        script_type = self._determine_script_type(sample_addr)

        return NormalizedTxRecord(
            txid=txid,
            timestamp=ts,
            input_addresses=input_addresses,
            output_addresses=output_addresses,
            input_amounts=input_amounts,
            output_amounts=output_amounts,
            fee=fee_btc,
            script_type=script_type,
            source=SourceEnum.ESPLORA.value,
            provenance="mempool.space live on-chain lookup"
        )

    def fetch_transaction(self, txid: str) -> Optional[NormalizedTxRecord]:
        """Fetch a single on-chain transaction by its TXID."""
        txid_clean = txid.strip().lower()
        if len(txid_clean) != 64:
            return None

        for base_url in API_ENDPOINTS:
            url = f"{base_url}/tx/{txid_clean}"
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        return self._parse_mempool_tx(resp.json())
                    elif resp.status_code == 404:
                        continue
            except Exception as err:
                logger.warning(f"Failed querying {url}: {err}")
                continue

        return None

    def fetch_address_transactions(self, address: str, limit: int = 15) -> List[NormalizedTxRecord]:
        """Fetch recent transactions involving a given Bitcoin address."""
        addr_clean = address.strip()
        records: List[NormalizedTxRecord] = []

        for base_url in API_ENDPOINTS:
            url = f"{base_url}/address/{addr_clean}/txs"
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        for raw_tx in data[:limit]:
                            records.append(self._parse_mempool_tx(raw_tx))
                        if records:
                            return records
            except Exception as err:
                logger.warning(f"Failed querying {url}: {err}")
                continue

        return records
