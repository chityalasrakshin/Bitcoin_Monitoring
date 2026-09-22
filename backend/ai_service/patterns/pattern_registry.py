"""ChainSentry Pattern Registry.
Orchestrates peeling chain, CoinJoin, and structuring pattern miners.
"""
from typing import Dict, List
from backend.chainsentry_common.schemas import NormalizedTxRecord, FiredPattern
from backend.chainsentry_common.logging import logger
from .peeling_chain import PeelingChainDetector
from .coinjoin_detect import CoinJoinDetector
from .rapid_hops import RapidStructuringDetector

class PatternRegistry:
    def __init__(self):
        self.peeling_detector = PeelingChainDetector()
        self.coinjoin_detector = CoinJoinDetector()
        self.structuring_detector = RapidStructuringDetector()

    def run_all(self, transactions: List[NormalizedTxRecord]) -> List[FiredPattern]:
        results: List[FiredPattern] = []
        try:
            results.extend(self.peeling_detector.detect(transactions))
        except Exception as e:
            logger.error(f"Error in peeling chain detection: {e}")

        try:
            results.extend(self.coinjoin_detector.detect(transactions))
        except Exception as e:
            logger.error(f"Error in CoinJoin detection: {e}")

        try:
            results.extend(self.structuring_detector.detect(transactions))
        except Exception as e:
            logger.error(f"Error in structuring detection: {e}")

        return results
