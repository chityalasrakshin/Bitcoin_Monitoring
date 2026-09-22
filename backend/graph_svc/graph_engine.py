"""ChainSentry Forensic Graph Engine.
Maintains a high-performance in-memory property graph (NetworkX) with optional Neo4j synchronization.
Exposes Cytoscape.js compatible graph serialization, neighborhood traversal, and structural queries.
"""
from typing import Any, Dict, List, Optional, Set, Tuple
import threading
import networkx as nx

from backend.chainsentry_common.schemas import (
    NormalizedTxRecord, CorrelationResult, GraphData, CytoscapeNode, CytoscapeNodeData,
    CytoscapeEdge, CytoscapeEdgeData
)
from backend.chainsentry_common.logging import logger

class ForensicGraphEngine:
    _instance: Optional["ForensicGraphEngine"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.wallet_clusters: Dict[str, str] = {}
        self.wallet_risks: Dict[str, float] = {}
        self.wallet_tags: Dict[str, List[str]] = {}

    @classmethod
    def get_instance(cls) -> "ForensicGraphEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ForensicGraphEngine()
            return cls._instance

    def clear(self):
        with self._lock:
            self.graph.clear()
            self.wallet_clusters.clear()
            self.wallet_risks.clear()
            self.wallet_tags.clear()

    def add_transaction(
        self,
        tx: NormalizedTxRecord,
        correlation: Optional[CorrelationResult] = None
    ):
        """Add transaction, inputs, outputs, and relay network observation to the forensic graph."""
        with self._lock:
            tx_id = tx.txid
            in_sum = sum(tx.input_amounts) if tx.input_amounts else 0.0
            out_sum = sum(tx.output_amounts) if tx.output_amounts else 0.0

            # 1. Add Transaction Node
            self.graph.add_node(
                tx_id,
                node_type="transaction",
                label=f"TX: {tx_id[:8]}...",
                txid=tx_id,
                timestamp=tx.timestamp.isoformat(),
                fee=tx.fee or 0.0,
                total_value=max(in_sum, out_sum),
                script_type=tx.script_type,
                risk_score=0.0
            )

            # 2. Add Input Wallets and Edges
            for idx, addr in enumerate(tx.input_addresses):
                amt = tx.input_amounts[idx] if idx < len(tx.input_amounts) else 0.0
                if not self.graph.has_node(addr):
                    self.graph.add_node(
                        addr,
                        node_type="wallet",
                        label=f"{addr[:6]}...{addr[-4:]}",
                        address=addr,
                        risk_score=self.wallet_risks.get(addr, 0.0),
                        cluster_id=self.wallet_clusters.get(addr, None),
                        tags=self.wallet_tags.get(addr, [])
                    )
                self.graph.add_edge(
                    addr,
                    tx_id,
                    key=f"in_{idx}_{tx_id}",
                    edge_type="INPUT_TO",
                    amount=amt,
                    label="INPUT_TO"
                )

            # 3. Add Output Wallets and Edges
            for idx, addr in enumerate(tx.output_addresses):
                amt = tx.output_amounts[idx] if idx < len(tx.output_amounts) else 0.0
                if not self.graph.has_node(addr):
                    self.graph.add_node(
                        addr,
                        node_type="wallet",
                        label=f"{addr[:6]}...{addr[-4:]}",
                        address=addr,
                        risk_score=self.wallet_risks.get(addr, 0.0),
                        cluster_id=self.wallet_clusters.get(addr, None),
                        tags=self.wallet_tags.get(addr, [])
                    )
                self.graph.add_edge(
                    tx_id,
                    addr,
                    key=f"out_{idx}_{tx_id}",
                    edge_type="OUTPUT_TO",
                    amount=amt,
                    vout=idx,
                    label="OUTPUT_TO"
                )

            # 4. Add Relay Network Observation Node and FIRST_RELAYED_BY Edge
            relay_ip = correlation.relay_ip if correlation else tx.src_ip
            if relay_ip:
                ip_node_id = f"ip:{relay_ip}"
                country = correlation.geo_country if correlation else tx.geo_country
                asn = correlation.asn if correlation else tx.asn
                latency_ms = correlation.latency_ms if correlation else 0.0

                if not self.graph.has_node(ip_node_id):
                    self.graph.add_node(
                        ip_node_id,
                        node_type="ip",
                        label=f"Peer: {relay_ip}",
                        ip=relay_ip,
                        geo_country=country,
                        asn=asn,
                        risk_score=0.0
                    )
                self.graph.add_edge(
                    tx_id,
                    ip_node_id,
                    key=f"relay_{tx_id}",
                    edge_type="FIRST_RELAYED_BY",
                    latency_ms=latency_ms,
                    label="FIRST_RELAYED_BY"
                )

    def set_wallet_cluster(self, address: str, cluster_id: str):
        with self._lock:
            self.wallet_clusters[address] = cluster_id
            if self.graph.has_node(address):
                self.graph.nodes[address]["cluster_id"] = cluster_id

    def set_wallet_risk(self, address: str, risk_score: float):
        with self._lock:
            self.wallet_risks[address] = risk_score
            if self.graph.has_node(address):
                self.graph.nodes[address]["risk_score"] = risk_score

    def add_wallet_tag(self, address: str, tag: str):
        with self._lock:
            if address not in self.wallet_tags:
                self.wallet_tags[address] = []
            if tag not in self.wallet_tags[address]:
                self.wallet_tags[address].append(tag)
            if self.graph.has_node(address):
                self.graph.nodes[address]["tags"] = self.wallet_tags[address]

    def get_neighborhood(self, entity_id: str, depth: int = 2, max_nodes: int = 150) -> GraphData:
        """Extract k-hop ego subgraph centered at entity_id, formatted for Cytoscape.js."""
        with self._lock:
            if not self.graph.has_node(entity_id):
                return GraphData(nodes=[], edges=[])

            # BFS expansion up to depth hops
            visited_nodes: Set[str] = {entity_id}
            frontier: Set[str] = {entity_id}

            for _ in range(depth):
                next_frontier: Set[str] = set()
                for node in frontier:
                    neighbors = set(self.graph.successors(node)) | set(self.graph.predecessors(node))
                    for nbr in neighbors:
                        if nbr not in visited_nodes:
                            visited_nodes.add(nbr)
                            next_frontier.add(nbr)
                            if len(visited_nodes) >= max_nodes:
                                break
                    if len(visited_nodes) >= max_nodes:
                        break
                frontier = next_frontier
                if len(visited_nodes) >= max_nodes or not frontier:
                    break

            # Build Cytoscape elements
            cy_nodes: List[CytoscapeNode] = []
            for nid in visited_nodes:
                attrs = self.graph.nodes[nid]
                node_type = attrs.get("node_type", "wallet")
                cy_nodes.append(
                    CytoscapeNode(
                        data=CytoscapeNodeData(
                            id=nid,
                            label=attrs.get("label", nid),
                            type=node_type,
                            risk_score=float(attrs.get("risk_score", 0.0)),
                            cluster_id=attrs.get("cluster_id"),
                            tags=attrs.get("tags", []),
                            extra={
                                k: v for k, v in attrs.items()
                                if k not in ("node_type", "label", "risk_score", "cluster_id", "tags")
                            }
                        )
                    )
                )

            cy_edges: List[CytoscapeEdge] = []
            subgraph = self.graph.subgraph(visited_nodes)
            for u, v, k, eattrs in subgraph.edges(keys=True, data=True):
                cy_edges.append(
                    CytoscapeEdge(
                        data=CytoscapeEdgeData(
                            id=f"{u}_{v}_{k}",
                            source=u,
                            target=v,
                            label=eattrs.get("label", "CONNECTS"),
                            amount=eattrs.get("amount"),
                            latency_ms=eattrs.get("latency_ms"),
                            confidence=eattrs.get("confidence")
                        )
                    )
                )

            return GraphData(nodes=cy_nodes, edges=cy_edges)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            wallets = sum(1 for _, d in self.graph.nodes(data=True) if d.get("node_type") == "wallet")
            txs = sum(1 for _, d in self.graph.nodes(data=True) if d.get("node_type") == "transaction")
            ips = sum(1 for _, d in self.graph.nodes(data=True) if d.get("node_type") == "ip")
            return {
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
                "wallets_count": wallets,
                "transactions_count": txs,
                "ips_count": ips,
                "clusters_count": len(set(self.wallet_clusters.values()))
            }

    def get_wallets_paginated(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        sort_by: str = "risk"
    ) -> Dict[str, Any]:
        """Return paginated list of wallet entities with risk scores and clusters."""
        with self._lock:
            wallets = []
            search_clean = search.strip().lower() if search else None

            for node_id, attrs in self.graph.nodes(data=True):
                if attrs.get("node_type") != "wallet":
                    continue
                if search_clean and search_clean not in node_id.lower():
                    continue

                wallets.append({
                    "address": node_id,
                    "risk_score": float(attrs.get("risk_score", 0.0)),
                    "cluster_id": attrs.get("cluster_id"),
                    "tags": attrs.get("tags", [])
                })

            if sort_by == "risk":
                wallets.sort(key=lambda w: w["risk_score"], reverse=True)
            elif sort_by == "address":
                wallets.sort(key=lambda w: w["address"])

            total = len(wallets)
            items = wallets[skip : skip + limit]
            return {"items": items, "total": total, "skip": skip, "limit": limit}

    def get_transactions_paginated(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        sort_by: str = "time"
    ) -> Dict[str, Any]:
        """Return paginated list of transaction entities with values, fees, and timestamps."""
        with self._lock:
            txs = []
            search_clean = search.strip().lower() if search else None

            for node_id, attrs in self.graph.nodes(data=True):
                if attrs.get("node_type") != "transaction":
                    continue
                if search_clean and search_clean not in node_id.lower():
                    continue

                txs.append({
                    "txid": node_id,
                    "total_value": float(attrs.get("total_value", 0.0)),
                    "fee": float(attrs.get("fee", 0.0)),
                    "timestamp": attrs.get("timestamp"),
                    "script_type": attrs.get("script_type", "UNKNOWN")
                })

            if sort_by == "value":
                txs.sort(key=lambda t: t["total_value"], reverse=True)
            else:
                txs.sort(key=lambda t: str(t.get("timestamp", "")), reverse=True)

            total = len(txs)
            items = txs[skip : skip + limit]
            return {"items": items, "total": total, "skip": skip, "limit": limit}

