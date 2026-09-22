"""ChainSentry Alert Ranking and Multi-Signal Fusion Service.
Combines statistical anomaly scores, graph pattern confidences, and propagated risk scores
into transparent, explainable forensic leads.
"""
from typing import Dict, List, Optional
import pandas as pd

from backend.chainsentry_common.schemas import (
    NormalizedTxRecord, FiredPattern, AlertCreate, EntityType, AlertStatus
)
from backend.chainsentry_common.logging import logger
from backend.ai_service.models.ensemble import AnomalyEnsemble
from backend.ai_service.explain.shap_explainer import ForensicsExplainer
from backend.ai_service.patterns.pattern_registry import PatternRegistry

class AlertRankingService:
    def __init__(
        self,
        weight_anomaly: float = 0.35,
        weight_pattern: float = 0.35,
        weight_risk: float = 0.30,
        min_lead_confidence: float = 0.50
    ):
        self.w_anomaly = weight_anomaly
        self.w_pattern = weight_pattern
        self.w_risk = weight_risk
        self.min_lead_confidence = min_lead_confidence

    def rank_leads(
        self,
        transactions: List[NormalizedTxRecord],
        feature_df: pd.DataFrame,
        anomaly_scores: List[float],
        explainer: ForensicsExplainer,
        patterns: List[FiredPattern],
        wallet_risks: Dict[str, float]
    ) -> List[AlertCreate]:
        """Synthesize all detection signals into ranked AlertCreate objects."""
        logger.info(f"Fusing signals across {len(transactions)} transactions")

        # Map patterns by txid
        patterns_by_tx: Dict[str, List[FiredPattern]] = {}
        for p in patterns:
            for txid in p.tx_chain:
                if txid not in patterns_by_tx:
                    patterns_by_tx[txid] = []
                patterns_by_tx[txid].append(p)

        alerts: List[AlertCreate] = []

        for idx, tx in enumerate(transactions):
            txid = tx.txid
            a_score = float(anomaly_scores[idx]) if idx < len(anomaly_scores) else 0.0

            # Pattern confidence for this transaction
            tx_patterns = patterns_by_tx.get(txid, [])
            p_score = max([p.confidence for p in tx_patterns]) if tx_patterns else 0.0

            # Risk score: max risk among inputs and outputs
            all_addrs = tx.input_addresses + tx.output_addresses
            r_score = max([wallet_risks.get(a, 0.0) for a in all_addrs]) if all_addrs else 0.0

            # Combined confidence calculation
            combined = (
                self.w_anomaly * a_score +
                self.w_pattern * p_score +
                self.w_risk * r_score
            )

            # Heuristic boost: if confirmed pattern fired, guarantee elevated visibility
            if p_score >= 0.80:
                combined = max(combined, p_score * 0.90)

            combined = min(0.99, max(0.0, combined))

            # Only generate leads that cross threshold or have active patterns
            if combined >= self.min_lead_confidence or tx_patterns:
                # Generate SHAP explanation
                feat_row = feature_df.iloc[idx]
                shap_exp = explainer.explain(feat_row, a_score)

                # Generate plain narrative
                narrative_parts = []
                if tx_patterns:
                    for pat in tx_patterns:
                        narrative_parts.append(pat.description)
                if r_score > 0.4:
                    narrative_parts.append(f"Involves addresses with elevated taint risk ({r_score:.2f}).")
                if shap_exp.summary:
                    narrative_parts.append(shap_exp.summary)

                narrative_text = " ".join(narrative_parts)

                alerts.append(
                    AlertCreate(
                        entity_type=EntityType.TRANSACTION,
                        entity_ref=txid,
                        anomaly_score=round(a_score, 4),
                        risk_score=round(r_score, 4),
                        combined_confidence=round(combined, 4),
                        fired_patterns=tx_patterns,
                        shap_explanation=shap_exp,
                        status=AlertStatus.NEW,
                        narrative=narrative_text
                    )
                )

        # Sort descending by combined confidence
        alerts.sort(key=lambda a: a.combined_confidence, reverse=True)
        logger.info(f"Alert ranking complete: generated {len(alerts)} prioritized investigative leads")
        return alerts
