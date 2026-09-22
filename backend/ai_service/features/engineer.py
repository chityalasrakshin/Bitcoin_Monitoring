"""ChainSentry Feature Engineering Engine.
Extracts transaction-level, network-telemetry, and graph-structural features
mirroring Elliptic++ and forensic typologies.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from backend.chainsentry_common.schemas import NormalizedTxRecord, CorrelationResult
from backend.chainsentry_common.logging import logger
from backend.graph_svc.graph_engine import ForensicGraphEngine

FEATURE_NAMES = [
    "input_count",
    "output_count",
    "total_value_btc",
    "fee_btc",
    "fee_rate_ratio",
    "output_amount_std",
    "equal_output_ratio",
    "value_roundness_score",
    "hour_of_day",
    "is_segwit",
    "has_relay_telemetry",
    "relay_latency_seconds",
    "max_input_risk",
    "max_output_risk"
]

def _is_round_number(val: float) -> bool:
    """Check if BTC amount is round (e.g. 0.1, 0.5, 1.0, 5.0, 10.0)."""
    for scale in [1.0, 0.1, 0.05, 0.01]:
        remainder = val % scale
        if remainder < 1e-6 or (scale - remainder) < 1e-6:
            return True
    return False

def extract_transaction_features(
    tx: NormalizedTxRecord,
    correlation: Optional[CorrelationResult] = None,
    graph_engine: Optional[ForensicGraphEngine] = None
) -> Dict[str, float]:
    """Extract a 14-dimensional feature dictionary for a single transaction."""
    in_count = float(len(tx.input_addresses))
    out_count = float(len(tx.output_addresses))

    in_sum = sum(tx.input_amounts) if tx.input_amounts else 0.0
    out_sum = sum(tx.output_amounts) if tx.output_amounts else 0.0
    total_val = max(in_sum, out_sum)

    fee = tx.fee if tx.fee is not None else 0.0
    fee_rate_ratio = fee / total_val if total_val > 1e-8 else 0.0

    # Output amount std and equal output ratio
    if tx.output_amounts and len(tx.output_amounts) > 1:
        out_std = float(np.std(tx.output_amounts))
        # Check equal outputs
        rounded = [round(a, 6) for a in tx.output_amounts]
        max_freq = max([rounded.count(x) for x in set(rounded)])
        equal_ratio = max_freq / len(tx.output_amounts)
    else:
        out_std = 0.0
        equal_ratio = 1.0 if tx.output_amounts else 0.0

    # Roundness score
    round_count = sum(1 for a in tx.output_amounts if _is_round_number(a))
    round_score = round_count / len(tx.output_amounts) if tx.output_amounts else 0.0

    # Timing
    hour = float(tx.timestamp.hour)

    # Script type
    st = str(tx.script_type).upper()
    is_segwit = 1.0 if any(k in st for k in ("P2WPKH", "P2WSH", "P2TR")) else 0.0

    # Network telemetry
    has_relay = 1.0 if (correlation or tx.src_ip) else 0.0
    relay_latency = (correlation.latency_ms / 1000.0) if correlation else 0.0

    # Graph risk lookups
    max_in_risk = 0.0
    max_out_risk = 0.0
    if graph_engine:
        for addr in tx.input_addresses:
            max_in_risk = max(max_in_risk, graph_engine.wallet_risks.get(addr, 0.0))
        for addr in tx.output_addresses:
            max_out_risk = max(max_out_risk, graph_engine.wallet_risks.get(addr, 0.0))

    return {
        "input_count": in_count,
        "output_count": out_count,
        "total_value_btc": float(total_val),
        "fee_btc": float(fee),
        "fee_rate_ratio": float(fee_rate_ratio),
        "output_amount_std": float(out_std),
        "equal_output_ratio": float(equal_ratio),
        "value_roundness_score": float(round_score),
        "hour_of_day": hour,
        "is_segwit": is_segwit,
        "has_relay_telemetry": has_relay,
        "relay_latency_seconds": float(relay_latency),
        "max_input_risk": float(max_in_risk),
        "max_output_risk": float(max_out_risk)
    }

def build_feature_dataframe(
    transactions: List[NormalizedTxRecord],
    correlations: Optional[Dict[str, CorrelationResult]] = None
) -> Tuple[pd.DataFrame, List[str]]:
    """Build feature matrix for a batch of transactions.
    Returns (DataFrame, list of txids).
    """
    graph_engine = ForensicGraphEngine.get_instance()
    rows = []
    txids = []

    for tx in transactions:
        corr = correlations.get(tx.txid) if correlations else None
        feat_dict = extract_transaction_features(tx, correlation=corr, graph_engine=graph_engine)
        rows.append(feat_dict)
        txids.append(tx.txid)

    df = pd.DataFrame(rows, columns=FEATURE_NAMES)
    return df, txids
