"""core/sample_data.py

サンプルの家計簿データ（取引履歴）を生成する。
実際のCSVがなくてもアプリの動作を確認できるようにするためのモジュール。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES = ["食費", "交通費", "娯楽", "住居費", "光熱費", "通信費", "日用品", "医療費"]

# カテゴリごとのだいたいの1回あたり支出額（平均, 標準偏差）
CATEGORY_PROFILE = {
    "食費": (1800, 700),
    "交通費": (600, 300),
    "娯楽": (2500, 1500),
    "住居費": (55000, 2000),
    "光熱費": (8000, 1500),
    "通信費": (4500, 500),
    "日用品": (1200, 600),
    "医療費": (2000, 1800),
}

# 月に何回くらい発生するか（住居費・通信費・光熱費は月1回想定）
CATEGORY_FREQ_PER_MONTH = {
    "食費": 26,
    "交通費": 20,
    "娯楽": 6,
    "住居費": 1,
    "光熱費": 1,
    "通信費": 1,
    "日用品": 8,
    "医療費": 2,
}


def generate_sample_transactions(
    n_days: int = 180, seed: int = 42, anomaly_count: int = 6
) -> pd.DataFrame:
    """n_days日分のサンプル取引データを生成する。

    いくつかの取引には意図的に大きな異常値（通常の3〜6倍程度）を混ぜ込み、
    異常検知ロジックの動作確認に使えるようにしている。
    """
    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=n_days)

    rows = []
    for category in CATEGORIES:
        mean, sd = CATEGORY_PROFILE[category]
        freq_per_month = CATEGORY_FREQ_PER_MONTH[category]
        n_months = max(1, n_days // 30)
        n_events = max(1, int(freq_per_month * n_months))

        offsets = rng.integers(0, n_days, size=n_events)
        amounts = rng.normal(loc=mean, scale=sd, size=n_events)
        amounts = np.clip(amounts, a_min=mean * 0.2, a_max=None)

        for offset, amount in zip(offsets, amounts):
            rows.append(
                {
                    "date": start_date + pd.Timedelta(days=int(offset)),
                    "category": category,
                    "amount": round(float(amount)),
                    "description": f"{category}の支払い",
                }
            )

    df = pd.DataFrame(rows)
    df = df.sort_values("date").reset_index(drop=True)

    # 異常値を意図的に混入させる（既存の行の金額を大きく引き上げる）
    if anomaly_count > 0 and len(df) > 0:
        anomaly_idx = rng.choice(len(df), size=min(anomaly_count, len(df)), replace=False)
        multipliers = rng.uniform(3.5, 6.0, size=len(anomaly_idx))
        df.loc[anomaly_idx, "amount"] = (df.loc[anomaly_idx, "amount"] * multipliers).round()
        df.loc[anomaly_idx, "description"] = df.loc[anomaly_idx, "description"] + "（臨時）"

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.reset_index(drop=True)
