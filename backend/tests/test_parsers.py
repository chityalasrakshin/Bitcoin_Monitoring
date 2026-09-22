import pytest
from backend.chainsentry_common.config import settings
from backend.ingestion_svc.parsers.csv_parser import parse_transactions_csv, parse_network_observations_csv

def test_parse_transactions_csv():
    tx_file = settings.SAMPLE_DATA_DIR / "transactions.csv"
    assert tx_file.exists()
    with open(tx_file, "r", encoding="utf-8") as f:
        records = parse_transactions_csv(f.read())

    assert len(records) > 0
    tx = records[0]
    assert len(tx.txid) == 64
    assert len(tx.input_addresses) > 0
    assert len(tx.output_addresses) > 0
    assert len(tx.input_amounts) > 0

def test_parse_network_observations_csv():
    net_file = settings.SAMPLE_DATA_DIR / "network_observations.csv"
    assert net_file.exists()
    with open(net_file, "r", encoding="utf-8") as f:
        records = parse_network_observations_csv(f.read())

    assert len(records) > 0
    obs = records[0]
    assert obs.observation_id
    assert obs.src_ip
    assert len(obs.txid) == 64
    assert obs.geo_country is not None
