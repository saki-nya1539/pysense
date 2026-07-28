"""core/anomaly.py

支出の異常検知ロジック。
2つの手法を提供する:
  - z-score法（カテゴリ内の平均・標準偏差からの乖離、説明しやすい）
  - Isolation Forest（scikit-learn、より柔軟だが説明性は低い）
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

Z_SCORE_THRESHOLD = 2.5


def detect_anomalies_zscore(df: pd.DataFrame, threshold: float = Z_SCORE_THRESHOLD) -> pd.DataFrame:
    """カテゴリごとにamountのz-scoreを計算し、閾値を超えるものを異常として返す。

    各カテゴリのデータが2件未満の場合はz-scoreを計算できないため、
    そのカテゴリの行は非異常（is_anomaly=False, z_score=NaN）として扱う。
    """
    out = df.copy()
    out["z_score"] = np.nan
    out["is_anomaly"] = False

    for category, group in out.groupby("category"):
        if len(group) < 2:
            continue
        mean = group["amount"].mean()
        sd = group["amount"].std(ddof=0)
        if sd == 0 or np.isnan(sd):
            continue
        z = (group["amount"] - mean) / sd
        out.loc[group.index, "z_score"] = z
        out.loc[group.index, "is_anomaly"] = z.abs() >= threshold

    return out


def detect_anomalies_isolation_forest(
    df: pd.DataFrame, contamination: float = 0.05, random_state: int = 42
) -> pd.DataFrame:
    """Isolation Forestによる異常検知。

    amountとカテゴリ内での相対的な大きさ（category_amount_ratio）を特徴量として使う。
    データが少なすぎる場合（5件未満）はすべて非異常として返す。
    """
    out = df.copy()
    out["is_anomaly"] = False
    out["anomaly_score"] = np.nan

    if len(out) < 5:
        return out

    category_mean = out.groupby("category")["amount"].transform("mean")
    category_mean = category_mean.replace(0, np.nan)
    ratio = (out["amount"] / category_mean).fillna(1.0)

    features = np.column_stack([out["amount"].values, ratio.values])

    model = IsolationForest(contamination=contamination, random_state=random_state)
    predictions = model.fit_predict(features)
    scores = model.decision_function(features)

    out["is_anomaly"] = predictions == -1
    out["anomaly_score"] = scores

    return out
