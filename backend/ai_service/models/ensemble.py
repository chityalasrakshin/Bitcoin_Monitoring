"""ChainSentry Anomaly Detection Ensemble.
Uses a multi-detector PyOD ensemble (Isolation Forest + ECOD + KNN) to compute
robust statistical anomaly scores across high-dimensional forensic features.
"""
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from pyod.models.iforest import IForest
from pyod.models.ecod import ECOD
from pyod.models.knn import KNN
from sklearn.preprocessing import RobustScaler

from backend.chainsentry_common.logging import logger
from backend.ai_service.features.engineer import FEATURE_NAMES

class AnomalyEnsemble:
    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.scaler = RobustScaler()
        self.iforest = IForest(contamination=contamination, random_state=42, n_estimators=100)
        self.ecod = ECOD(contamination=contamination)
        self.knn = KNN(contamination=contamination, n_neighbors=5)
        self.is_fitted = False

    def fit(self, X: pd.DataFrame) -> "AnomalyEnsemble":
        """Fit ensemble detectors on feature matrix."""
        logger.info(f"Fitting AnomalyEnsemble on {len(X)} samples with {X.shape[1]} features")
        # Ensure column alignment
        X_aligned = X[FEATURE_NAMES].fillna(0.0)
        X_scaled = self.scaler.fit_transform(X_aligned)

        self.iforest.fit(X_scaled)
        self.ecod.fit(X_scaled)
        self.knn.fit(X_scaled)
        self.is_fitted = True
        logger.info("AnomalyEnsemble fit complete")
        return self

    def predict_anomaly_scores(self, X: pd.DataFrame) -> np.ndarray:
        """Compute normalized anomaly scores in [0.0, 1.0] for each row."""
        if not self.is_fitted:
            # Fit on input data if not previously trained (unsupervised online adaptation)
            self.fit(X)

        X_aligned = X[FEATURE_NAMES].fillna(0.0)
        X_scaled = self.scaler.transform(X_aligned)

        # Decision functions return continuous outlier scores
        score_iforest = self.iforest.decision_function(X_scaled)
        score_ecod = self.ecod.decision_function(X_scaled)
        score_knn = self.knn.decision_function(X_scaled)

        def _minmax(s: np.ndarray) -> np.ndarray:
            s_min, s_max = np.min(s), np.max(s)
            if s_max - s_min < 1e-6:
                return np.zeros_like(s)
            return (s - s_min) / (s_max - s_min)

        norm_if = _minmax(score_iforest)
        norm_ec = _minmax(score_ecod)
        norm_kn = _minmax(score_knn)

        # Weighted combination: 40% IForest, 35% ECOD, 25% KNN
        combined = 0.40 * norm_if + 0.35 * norm_ec + 0.25 * norm_kn
        return np.clip(combined, 0.0, 1.0)
