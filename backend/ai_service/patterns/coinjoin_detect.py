"""ChainSentry CoinJoin and Mixer Detection Engine.
Identifies collaborative mixing transactions (Wasabi, Whirlpool, JoinMarket)
based on equal-output denominations, input multiplicity, and fee distribution.
"""
from typing import Dict, List, Optional, Set
from collections import defaultdict

from backend.chainsentry_common.schemas import NormalizedTxRecord, FiredPattern
from backend.chainsentry_common.logging import logger

class CoinJoinDetector:
    def __init__(self, min_equal_outputs: int = 3):
        self.min_equal_outputs = min_equal_outputs

    def detect(self, transactions: List[NormalizedTxRecord]) -> List[FiredPattern]:
        """Detect CoinJoin mixing patterns."""
        patterns: List[FiredPattern] = []

        for tx in transactions:
            if len(tx.input_addresses) < 2 or len(tx.output_amounts) < 2:
                continue

            # Group output amounts
            amount_counts: Dict[float, int] = defaultdict(int)
            for amt in tx.output_amounts:
                amount_counts[round(amt, 6)] += 1

            if not amount_counts:
                continue

            most_common_amt, max_count = max(amount_counts.items(), key=lambda x: x[1])

            # Identification heuristic:
            # At least min_equal_outputs of identical value, and at least 3 participants/inputs
            if max_count >= self.min_equal_outputs and len(tx.input_addresses) >= 3:
                # Determine flavor
                flavor = "Generic CoinJoin"
                if len(tx.input_addresses) == 5 and max_count == 5:
                    flavor = "Whirlpool (5x5 Pool)"
                elif len(tx.input_addresses) >= 10 and max_count >= 8:
                    flavor = "Wasabi / WabiSabi Coordinator"
                elif max_count >= 3:
                    flavor = "JoinMarket / Equal-Output Mix"

                confidence = min(0.99, 0.70 + (max_count * 0.04))

                patterns.append(
                    FiredPattern(
                        pattern="coinjoin_mixing",
                        confidence=round(confidence, 3),
                        description=(
                            f"Mixer transaction identified ({flavor}). "
                            f"{max_count} equal outputs of {most_common_amt:.6f} BTC from "
                            f"{len(tx.input_addresses)} inputs."
                        ),
                        tx_chain=[tx.txid],
                        involved_addresses=list(set(tx.input_addresses + tx.output_addresses)),
                        metrics={
                            "equal_output_count": max_count,
                            "denomination_btc": most_common_amt,
                            "input_count": len(tx.input_addresses),
                            "total_output_count": len(tx.output_addresses),
                            "flavor": flavor
                        }
                    )
                )

        logger.info(f"CoinJoin detector flagged {len(patterns)} mixing transactions")
        return patterns
