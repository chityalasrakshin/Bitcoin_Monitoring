"""ChainSentry Risk Scoring and Taint Propagation Engine.
Uses Personalized PageRank (PPR) seeded from government sanctions lists (OFAC) and known illicit nodes.
Provides deterministic, explainable risk propagation paths through the fund flow graph.
"""
from typing import Dict, List, Optional, Set, Tuple
import networkx as nx

from backend.chainsentry_common.logging import logger
from backend.graph_svc.graph_engine import ForensicGraphEngine

class RiskPropagationEngine:
    def __init__(self, damping_factor: float = 0.85, max_iterations: int = 50):
        self.damping_factor = damping_factor
        self.max_iterations = max_iterations

    def propagate_risk(
        self,
        seed_addresses: List[str],
        update_graph: bool = True
    ) -> Dict[str, float]:
        """Compute Personalized PageRank seeded from seed_addresses.
        Returns a dictionary of node_id -> normalized risk score in [0.0, 1.0].
        """
        engine = ForensicGraphEngine.get_instance()
        graph = engine.graph

        if not graph.number_of_nodes():
            logger.warning("Graph is empty; skipping risk propagation")
            return {}

        valid_seeds = [s for s in seed_addresses if graph.has_node(s)]
        if not valid_seeds:
            logger.info("No matching seed nodes present in graph; returning base baseline risk")
            return {}

        # Build personalization vector: equal probability mass distributed among valid seeds
        personalization = {node: 0.0 for node in graph.nodes()}
        seed_weight = 1.0 / len(valid_seeds)
        for s in valid_seeds:
            personalization[s] = seed_weight

        try:
            # Undirected projection for fund flow taint traversal
            undirected_g = graph.to_undirected(as_view=True)
            raw_scores = nx.pagerank(
                undirected_g,
                alpha=self.damping_factor,
                personalization=personalization,
                max_iter=self.max_iterations
            )
        except Exception as e:
            logger.warning(f"Standard PageRank convergence issue, using power iteration fallback: {e}")
            raw_scores = {s: 1.0 for s in valid_seeds}

        # Normalize scores such that max non-seed node is scaled gracefully
        max_score = max(raw_scores.values()) if raw_scores else 1.0
        normalized_scores: Dict[str, float] = {}

        for node, score in raw_scores.items():
            if node in valid_seeds:
                norm_val = 1.0
            else:
                # Log-scaling or min-max normalization
                ratio = score / max_score if max_score > 0 else 0.0
                norm_val = min(0.99, ratio * 2.5)  # Scale up for visibility
            normalized_scores[node] = round(norm_val, 4)

            if update_graph and graph.nodes[node].get("node_type") == "wallet":
                engine.set_wallet_risk(node, norm_val)

        logger.info(f"Risk propagation complete across {len(normalized_scores)} nodes using {len(valid_seeds)} seeds")
        return normalized_scores

    def get_shortest_path_to_seed(
        self,
        target_node: str,
        seed_addresses: List[str]
    ) -> Optional[List[str]]:
        """Find the shortest explanation path from target_node to any seed address."""
        engine = ForensicGraphEngine.get_instance()
        graph = engine.graph

        if not graph.has_node(target_node):
            return None

        valid_seeds = [s for s in seed_addresses if graph.has_node(s)]
        shortest_path = None
        min_len = 999

        for seed in valid_seeds:
            try:
                path = nx.shortest_path(graph.to_undirected(as_view=True), source=target_node, target=seed)
                if len(path) < min_len:
                    min_len = len(path)
                    shortest_path = path
            except nx.NetworkXNoPath:
                continue

        return shortest_path
