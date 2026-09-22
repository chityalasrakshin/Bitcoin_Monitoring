import pytest
from datetime import datetime, timezone
from backend.chainsentry_common.schemas import NormalizedTxRecord
from backend.ai_service.patterns.peeling_chain import PeelingChainDetector
from backend.ai_service.patterns.coinjoin_detect import CoinJoinDetector

def test_peeling_chain_detection():
    # Construct 3-hop peeling chain:
    # tx1: in=[addr_0], out=[peel_1, change_1], amounts=[0.1, 0.9]
    # tx2: in=[change_1], out=[peel_2, change_2], amounts=[0.1, 0.79]
    # tx3: in=[change_2], out=[peel_3, change_3], amounts=[0.1, 0.68]
    tx1 = NormalizedTxRecord(
        txid="1" * 64,
        timestamp=datetime.now(timezone.utc),
        input_addresses=["addr_0"],
        output_addresses=["peel_1", "change_1"],
        input_amounts=[1.0],
        output_amounts=[0.1, 0.9],
        source="synthetic"
    )
    tx2 = NormalizedTxRecord(
        txid="2" * 64,
        timestamp=datetime.now(timezone.utc),
        input_addresses=["change_1"],
        output_addresses=["peel_2", "change_2"],
        input_amounts=[0.9],
        output_amounts=[0.1, 0.79],
        source="synthetic"
    )
    tx3 = NormalizedTxRecord(
        txid="3" * 64,
        timestamp=datetime.now(timezone.utc),
        input_addresses=["change_2"],
        output_addresses=["peel_3", "change_3"],
        input_amounts=[0.79],
        output_amounts=[0.1, 0.68],
        source="synthetic"
    )

    detector = PeelingChainDetector(min_hops=3)
    patterns = detector.detect([tx1, tx2, tx3])
    assert len(patterns) == 1
    p = patterns[0]
    assert p.pattern == "peeling_chain"
    assert len(p.tx_chain) == 3
    assert p.confidence >= 0.7

def test_coinjoin_detector():
    cj_tx = NormalizedTxRecord(
        txid="4" * 64,
        timestamp=datetime.now(timezone.utc),
        input_addresses=["in_a", "in_b", "in_c"],
        output_addresses=["mix_1", "mix_2", "mix_3"],
        input_amounts=[0.01, 0.01, 0.01],
        output_amounts=[0.01, 0.01, 0.01],
        source="synthetic"
    )
    detector = CoinJoinDetector(min_equal_outputs=3)
    patterns = detector.detect([cj_tx])
    assert len(patterns) == 1
    assert patterns[0].pattern == "coinjoin_mixing"
