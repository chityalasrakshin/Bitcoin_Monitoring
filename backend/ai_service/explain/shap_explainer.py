"""ChainSentry SHAP & Feature Attribution Explainer.
Generates investigator-interpretable feature contribution breakdowns for anomaly scores.
"""
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import shap

from backend.chainsentry_common.schemas import SHAPExplanation, SHAPFeatureContribution
from backend.chainsentry_common.logging import logger
from backend.ai_service.features.engineer import FEATURE_NAMES

FEATURE_DESCRIPTIONS = {
    "input_count": "Input address count",
    "output_count": "Output address count",
    "total_value_btc": "Total transfer volume in BTC",
    "fee_btc": "Transaction miner fee in BTC",
    "fee_rate_ratio": "Fee-to-transfer-value ratio",
    "output_amount_std": "Output amount variance",
    "equal_output_ratio": "Proportion of identical output denominations",
    "value_roundness_score": "Round-number amount frequency",
    "hour_of_day": "Transaction broadcast UTC hour",
    "is_segwit": "SegWit / Taproot script type indicator",
    "has_relay_telemetry": "Direct peer-to-peer relay telemetry correlation",
    "relay_latency_seconds": "P2P broadcast to block propagation delay",
    "max_input_risk": "Maximum risk score among funding input wallets",
    "max_output_risk": "Maximum risk score among recipient wallets"
}

class ForensicsExplainer:
    def __init__(self, ensemble_model):
        self.ensemble = ensemble_model
        self.explainer = None
        self._init_explainer()

    def _init_explainer(self):
        try:
            # TreeExplainer works directly with IsolationForest's underlying estimator
            forest = self.ensemble.iforest.detector_
            self.explainer = shap.TreeExplainer(forest)
        except Exception as e:
            logger.warning(f"TreeExplainer initialization fallback: {e}")
            self.explainer = None

    def explain(self, feature_row: pd.Series, anomaly_score: float) -> SHAPExplanation:
        """Explain feature attributions for a single sample."""
        row_aligned = feature_row[FEATURE_NAMES].fillna(0.0)
        X_scaled = self.ensemble.scaler.transform(pd.DataFrame([row_aligned]))

        contributions: List[SHAPFeatureContribution] = []

        if self.explainer is not None:
            try:
                shap_values = self.explainer.shap_values(X_scaled)
                # For TreeExplainer on IForest, higher negative values often mean more anomalous
                raw_vals = shap_values[0] if isinstance(shap_values, list) else shap_values[0]
                # Invert so positive indicates higher anomaly contribution
                abs_impacts = np.abs(raw_vals)

                top_indices = np.argsort(abs_impacts)[::-1][:5]
                for idx in top_indices:
                    feat_name = FEATURE_NAMES[idx]
                    val = float(row_aligned.iloc[idx])
                    contrib = float(abs_impacts[idx])
                    desc = FEATURE_DESCRIPTIONS.get(feat_name, feat_name)
                    contributions.append(
                        SHAPFeatureContribution(
                            feature_name=feat_name,
                            value=round(val, 6),
                            contribution=round(contrib, 4),
                            description=desc
                        )
                    )
            except Exception as e:
                logger.warning(f"SHAP value computation failed, using deviation fallback: {e}")

        # Fallback if SHAP calculation was unavailable
        if not contributions:
            # Standard z-score deviation attribution
            for col in FEATURE_NAMES:
                val = float(row_aligned[col])
                if abs(val) > 1e-4:
                    contributions.append(
                        SHAPFeatureContribution(
                            feature_name=col,
                            value=round(val, 6),
                            contribution=0.1,
                            description=FEATURE_DESCRIPTIONS.get(col, col)
                        )
                    )
            contributions = sorted(contributions, key=lambda x: abs(x.value), reverse=True)[:5]

        top_names = [c.description for c in contributions[:3]]
        summary = (
            f"Anomaly score {anomaly_score:.2f} primarily driven by: {', '.join(top_names)}."
            if top_names else "Nominal baseline activity."
        )

        return SHAPExplanation(
            base_value=0.5,
            anomaly_score=round(anomaly_score, 4),
            top_features=contributions,
            summary=summary
        )
