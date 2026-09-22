"""ChainSentry Network-to-Blockchain Correlation Engine.
Correlates peer-to-peer network-layer telemetry (IP/port/timing) with on-chain transaction data.
Identifies the originating or earliest relaying peer IP (FIRST_RELAYED_BY) and calculates propagation latency.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from backend.chainsentry_common.schemas import NormalizedTxRecord, NetworkObservationRecord, CorrelationResult
from backend.chainsentry_common.logging import logger
from backend.ingestion_svc.connectors.geoip import resolve_ip

class CorrelationEngine:
    def __init__(self, max_latency_window_seconds: float = 86400.0):
        self.max_latency_window_seconds = max_latency_window_seconds

    def correlate(
        self,
        transactions: List[NormalizedTxRecord],
        observations: List[NetworkObservationRecord]
    ) -> Dict[str, CorrelationResult]:
        """Correlate transactions with network observations by TXID.
        Returns a mapping of txid -> CorrelationResult.
        """
        logger.info(f"Starting correlation over {len(transactions)} txs and {len(observations)} observations")

        # Group observations by txid
        obs_by_txid: Dict[str, List[NetworkObservationRecord]] = defaultdict(list)
        for obs in observations:
            obs_by_txid[obs.txid].append(obs)

        results: Dict[str, CorrelationResult] = {}

        for tx in transactions:
            tx_obs = obs_by_txid.get(tx.txid)
            if not tx_obs:
                # If transaction already had src_ip attached directly, build result from it
                if tx.src_ip:
                    country = tx.geo_country
                    asn = tx.asn
                    if not country or not asn:
                        c, a = resolve_ip(tx.src_ip)
                        country = country or c
                        asn = asn or a
                    results[tx.txid] = CorrelationResult(
                        txid=tx.txid,
                        relay_ip=tx.src_ip,
                        dst_ip=tx.dst_ip,
                        src_port=tx.src_port,
                        dst_port=tx.dst_port,
                        geo_country=country,
                        asn=asn,
                        first_seen_timestamp=tx.timestamp,
                        blockchain_timestamp=tx.timestamp,
                        latency_ms=0.0,
                        confidence=0.75,
                        observation_count=1
                    )
                continue

            # Sort observations by timestamp to find the earliest relay observation
            sorted_obs = sorted(tx_obs, key=lambda o: o.timestamp)
            first_obs = sorted_obs[0]

            # Calculate propagation latency
            # Typically network observation occurs BEFORE or simultaneously with block timestamp
            dt_seconds = (tx.timestamp - first_obs.timestamp).total_seconds()
            latency_ms = max(0.0, dt_seconds * 1000.0)

            # Confidence calculation:
            # - Temporal sanity: network timestamp before or very close to blockchain timestamp
            # - More observations corroborating the same relay peer increases confidence
            obs_count = len(sorted_obs)
            if dt_seconds >= 0 and dt_seconds <= self.max_latency_window_seconds:
                temporal_score = 0.95 if dt_seconds > 0 else 0.85
            else:
                # Discrepancy or delayed observation
                temporal_score = 0.60

            # Corroboration boost (up to +0.05 for multiple observations)
            corroboration_bonus = min(0.05, (obs_count - 1) * 0.01)
            confidence = min(0.99, temporal_score + corroboration_bonus)

            country = first_obs.geo_country
            asn = first_obs.asn
            if not country or not asn:
                c, a = resolve_ip(first_obs.src_ip)
                country = country or c
                asn = asn or a

            results[tx.txid] = CorrelationResult(
                txid=tx.txid,
                relay_ip=first_obs.src_ip,
                dst_ip=first_obs.dst_ip,
                src_port=first_obs.src_port,
                dst_port=first_obs.dst_port,
                geo_country=country,
                asn=asn,
                first_seen_timestamp=first_obs.timestamp,
                blockchain_timestamp=tx.timestamp,
                latency_ms=round(latency_ms, 2),
                confidence=round(confidence, 4),
                observation_count=obs_count
            )

        logger.info(f"Correlation completed: {len(results)} transactions matched with relay network telemetry")
        return results
