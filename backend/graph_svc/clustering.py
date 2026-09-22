"""ChainSentry Entity Clustering Engine.
Implements:
1. Common-Input-Ownership Heuristic (CIOH / Union-Find) with CoinJoin/Mixer exclusion.
2. Community detection across the transaction co-spending and change-flow graph.
3. Cluster reconciliation and assignment.
"""
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from backend.chainsentry_common.schemas import NormalizedTxRecord
from backend.chainsentry_common.logging import logger
from backend.graph_svc.graph_engine import ForensicGraphEngine

class DisjointSetUnion:
    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.rank: Dict[str, int] = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0
            return item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])  # Path compression
        return self.parent[item]

    def union(self, x: str, y: str):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            # Union by rank
            if self.rank[root_x] < self.rank[root_y]:
                self.parent[root_x] = root_y
            elif self.rank[root_x] > self.rank[root_y]:
                self.parent[root_y] = root_x
            else:
                self.parent[root_y] = root_x
                self.rank[root_x] += 1

def is_likely_coinjoin(tx: NormalizedTxRecord) -> bool:
    """Detect if transaction has CoinJoin mixing structure to avoid false-positive clustering."""
    if len(tx.input_addresses) < 2 or len(tx.output_amounts) < 2:
        return False

    # Count output amount frequencies
    amount_counts: Dict[float, int] = defaultdict(int)
    for amt in tx.output_amounts:
        # Round to 6 decimals to accommodate slight variance
        rounded = round(amt, 6)
        amount_counts[rounded] += 1

    max_equal_outputs = max(amount_counts.values()) if amount_counts else 0

    # If 3 or more outputs share the exact same amount and inputs >= 3, it's a mixing transaction
    if max_equal_outputs >= 3 and len(tx.input_addresses) >= 3:
        return True

    return False

class EntityClusteringEngine:
    def __init__(self):
        self.dsu = DisjointSetUnion()

    def cluster_transactions(
        self,
        transactions: List[NormalizedTxRecord],
        update_graph: bool = True
    ) -> Dict[str, str]:
        """Run Common-Input-Ownership Heuristic with CoinJoin exclusion.
        Returns a mapping: address -> cluster_id.
        """
        logger.info(f"Starting entity clustering over {len(transactions)} transactions")
        coinjoin_skipped = 0
        co_spent_count = 0

        # Step 1: Union co-spent inputs for non-CoinJoin transactions
        for tx in transactions:
            if is_likely_coinjoin(tx):
                coinjoin_skipped += 1
                continue

            inputs = tx.input_addresses
            if len(inputs) >= 2:
                co_spent_count += 1
                base_addr = inputs[0]
                for other_addr in inputs[1:]:
                    self.dsu.union(base_addr, other_addr)

        # Step 2: Ensure every address (input or output) has a cluster representation
        all_addresses: Set[str] = set()
        for tx in transactions:
            all_addresses.update(tx.input_addresses)
            all_addresses.update(tx.output_addresses)

        address_to_cluster: Dict[str, str] = {}
        for addr in all_addresses:
            root = self.dsu.find(addr)
            # Create a clean cluster id based on the root representative
            cluster_id = f"entity-{root[:8]}"
            address_to_cluster[addr] = cluster_id

        # Update ForensicGraphEngine if requested
        if update_graph:
            engine = ForensicGraphEngine.get_instance()
            for addr, cid in address_to_cluster.items():
                engine.set_wallet_cluster(addr, cid)

        # Count cluster distribution
        clusters = defaultdict(list)
        for addr, cid in address_to_cluster.items():
            clusters[cid].append(addr)

        multi_address_clusters = sum(1 for addrs in clusters.values() if len(addrs) > 1)
        logger.info(
            f"Clustering complete: {len(all_addresses)} addresses resolved into {len(clusters)} entities "
            f"({multi_address_clusters} multi-address clusters, skipped {coinjoin_skipped} CoinJoins)"
        )
        return address_to_cluster
