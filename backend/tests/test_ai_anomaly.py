import pytest
from backend.chainsentry_common.config import settings
from backend.ingestion_svc.parsers.csv_parser import parse_transactions_csv
from backend.ai_service.features.engineer import build_feature_dataframe
from backend.ai_service.models.ensemble import AnomalyEnsemble
from backend.ai_service.explain.shap_explainer import ForensicsExplainer

def test_feature_engineering_and_anomaly_scoring():
    tx_file = settings.SAMPLE_DATA_DIR / "transactions.csv"
    with open(tx_file, "r", encoding="utf-8") as f:
        txs = parse_transactions_csv(f.read())

    feature_df, txids = build_feature_dataframe(txs)
    assert len(feature_df) == len(txs)
    assert feature_df.shape[1] == 14

    ensemble = AnomalyEnsemble()
    scores = ensemble.predict_anomaly_scores(feature_df)
    assert len(scores) == len(txs)
    assert all(0.0 <= s <= 1.0 for s in scores)

    explainer = ForensicsExplainer(ensemble)
    exp = explainer.explain(feature_df.iloc[0], float(scores[0]))
    assert exp.anomaly_score >= 0.0
    assert len(exp.top_features) > 0
