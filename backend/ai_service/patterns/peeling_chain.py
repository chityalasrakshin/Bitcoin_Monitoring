"""ChainSentry Peeling Chain Detector.
Detects laundering behavior where funds are methodically peeled off across a long sequential chain
of 2-output transactions (one peel payment, one return change).
"""
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from backend.chainsentry_common.schemas import NormalizedTxRecord, FiredPattern
from backend.chainsentry_common.logging import logger

class PeelingChainDetector:
    def __init__(self, min_hops: int = 3, max_decay_ratio: float = 0.95):
        self.min_hops = min_hops
        self.max_decay_ratio = max_decay_ratio

    def detect(self, transactions: List[NormalizedTxRecord]) -> List[FiredPattern]:
        """Detect peeling chains in transaction set."""
        tx_by_id = {tx.txid: tx for tx in transactions}

        # Build address to spend-tx index
        # address -> list of txids where address is an input
        spent_by: Dict[str, List[str]] = defaultdict(list)
        for tx in transactions:
            for in_addr in tx.input_addresses:
                spent_by[in_addr].append(tx.txid)

        visited_txs: Set[str] = set()
        detected_patterns: List[FiredPattern] = []

        # Find starting candidate transactions (2 outputs, 1 or 2 inputs)
        candidate_starts = [
            tx for tx in transactions
            if len(tx.output_addresses) == 2 and len(tx.output_amounts) == 2
        ]

        for start_tx in candidate_starts:
            if start_tx.txid in visited_txs:
                continue

            current_tx = start_tx
            chain = [current_tx.txid]
            addresses_in_chain = list(current_tx.input_addresses)

            while True:
                # Look at outputs of current_tx
                out_addrs = current_tx.output_addresses
                out_amts = current_tx.output_amounts

                if len(out_addrs) != 2 or len(out_amts) != 2:
                    break

                # The change address is typically the larger amount or the one immediately re-spent
                next_tx = None
                # Check which output address was spent next
                for idx, out_addr in enumerate(out_addrs):
                    next_spends = spent_by.get(out_addr, [])
                    # Filter for unvisited 2-output txs
                    valid_spends = [txid for txid in next_spends if txid in tx_by_id and txid not in chain]
                    if valid_spends:
                        candidate_next = tx_by_id[valid_spends[0]]
                        if len(candidate_next.output_addresses) == 2:
                            next_tx = candidate_next
                            addresses_in_chain.append(out_addr)
                            break

                if next_tx:
                    chain.append(next_tx.txid)
                    current_tx = next_tx
                else:
                    break

            if len(chain) >= self.min_hops:
                for txid in chain:
                    visited_txs.add(txid)

                # Confidence scales with chain length (3 hops: 0.70, 5+ hops: 0.90+)
                confidence = min(0.98, 0.60 + (len(chain) * 0.06))

                detected_patterns.append(
                    FiredPattern(
                        pattern="peeling_chain",
                        confidence=round(confidence, 3),
                        description=(
                            f"Peeling chain detected spanning {len(chain)} sequential transactions. "
                            f"Systematic value peel-off with recurring change output re-spends."
                        ),
                        tx_chain=chain,
                        involved_addresses=list(set(addresses_in_chain)),
                        metrics={
                            "hops": len(chain),
                            "initial_tx": chain[0],
                            "terminal_tx": chain[-1]
                        }
                    )
                )

        logger.info(f"Peeling chain detector found {len(detected_patterns)} chains")
        return detected_patterns
