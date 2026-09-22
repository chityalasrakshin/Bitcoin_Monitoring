import pytest
from datetime import datetime, timezone
from backend.chainsentry_common.schemas import NormalizedTxRecord
from backend.graph_svc.clustering import EntityClusteringEngine, is_likely_coinjoin

def test_common_input_clustering():
    tx1 = NormalizedTxRecord(
        txid="a" * 64,
        timestamp=datetime.now(timezone.utc),
        input_addresses=["addr_1", "addr_2"],
        output_addresses=["addr_3"],
        input_amounts=[1.0, 1.0],
        output_amounts=[1.99],
        source="synthetic"
    )
    tx2 = NormalizedTxRecord(
        txid="b" * 64,
        timestamp=datetime.now(timezone.utc),
        input_addresses=["addr_2", "addr_4"],
        output_addresses=["addr_5"],
        input_amounts=[1.0, 1.0],
        output_amounts=[1.99],
        source="synthetic"
    )

    engine = EntityClusteringEngine()
    clusters = engine.cluster_transactions([tx1, tx2], update_graph=False)

    # addr_1, addr_2, addr_4 must share the exact same cluster_id
    assert clusters["addr_1"] == clusters["addr_2"]
    assert clusters["addr_2"] == clusters["addr_4"]

def test_coinjoin_exclusion():
    # 5 inputs, 5 equal outputs -> should be flagged as CoinJoin and NOT merged
    cj_tx = NormalizedTxRecord(
        txid="c" * 64,
        timestamp=datetime.now(timezone.utc),
        input_addresses=["user_a", "user_b", "user_c", "user_d", "user_e"],
        output_addresses=["out_1", "out_2", "out_3", "out_4", "out_5"],
        input_amounts=[0.05, 0.05, 0.05, 0.05, 0.05],
        output_amounts=[0.05, 0.05, 0.05, 0.05, 0.05],
        source="synthetic"
    )
    assert is_likely_coinjoin(cj_tx) is True
