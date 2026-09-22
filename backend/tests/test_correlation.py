import pytest
from backend.chainsentry_common.config import settings
from backend.ingestion_svc.parsers.csv_parser import parse_transactions_csv, parse_network_observations_csv
from backend.ingestion_svc.correlation import CorrelationEngine

def test_correlation_engine():
    tx_file = settings.SAMPLE_DATA_DIR / "transactions.csv"
    net_file = settings.SAMPLE_DATA_DIR / "network_observations.csv"

    with open(tx_file, "r", encoding="utf-8") as f:
        txs = parse_transactions_csv(f.read())
    with open(net_file, "r", encoding="utf-8") as f:
        obs = parse_network_observations_csv(f.read())

    correlator = CorrelationEngine()
    results = correlator.correlate(txs, obs)

    assert len(results) > 0
    # Every matched result must have valid relay_ip, latency_ms >= 0, confidence > 0
    sample_res = next(iter(results.values()))
    assert sample_res.relay_ip
    assert sample_res.confidence >= 0.5
    assert sample_res.latency_ms >= 0.0
