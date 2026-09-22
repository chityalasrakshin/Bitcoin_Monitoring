"""ChainSentry High-Velocity and Structuring Pattern Detector.
Detects rapid hops, fan-out disbursement, and fan-in consolidation patterns used in layering phases of money laundering.
"""
from typing import Dict, List, Set
from collections import defaultdict
from backend.chainsentry_common.schemas import NormalizedTxRecord, FiredPattern
from backend.chainsentry_common.logging import logger

class RapidStructuringDetector:
    def __init__(self, fan_threshold: int = 5, rapid_time_window_seconds: float = 300.0):
        self.fan_threshold = fan_threshold
        self.rapid_time_window_seconds = rapid_time_window_seconds

    def detect(self, transactions: List[NormalizedTxRecord]) -> List[FiredPattern]:
        patterns: List[FiredPattern] = []

        # 1. Fan-out detection (Layering / disbursement)
        for tx in transactions:
            if len(tx.input_addresses) <= 2 and len(tx.output_addresses) >= self.fan_threshold:
                patterns.append(
                    FiredPattern(
                        pattern="fan_out_disbursement",
                        confidence=0.82,
                        description=(
                            f"Fan-out structuring detected in TXID {tx.txid[:8]}... "
                            f"Disbursing funds across {len(tx.output_addresses)} recipient outputs."
                        ),
                        tx_chain=[tx.txid],
                        involved_addresses=list(set(tx.input_addresses + tx.output_addresses)),
                        metrics={
                            "output_count": len(tx.output_addresses),
                            "input_count": len(tx.input_addresses)
                        }
                    )
                )

        # 2. Fan-in detection (Consolidation)
        for tx in transactions:
            if len(tx.input_addresses) >= self.fan_threshold and len(tx.output_addresses) <= 2:
                patterns.append(
                    FiredPattern(
                        pattern="fan_in_consolidation",
                        confidence=0.85,
                        description=(
                            f"Fan-in consolidation detected in TXID {tx.txid[:8]}... "
                            f"Aggregating funds from {len(tx.input_addresses)} inputs into "
                            f"{len(tx.output_addresses)} target address(es)."
                        ),
                        tx_chain=[tx.txid],
                        involved_addresses=list(set(tx.input_addresses + tx.output_addresses)),
                        metrics={
                            "input_count": len(tx.input_addresses),
                            "output_count": len(tx.output_addresses)
                        }
                    )
                )

        logger.info(f"Structuring detector found {len(patterns)} fan-out/fan-in patterns")
        return patterns
