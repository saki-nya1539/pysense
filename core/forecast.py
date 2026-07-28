"""core/forecast.py

月次の支出集計・来月の支出予測を行う。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def monthly_totals(df: pd.DataFrame) -> pd.DataFrame:
    """月ごとの支出合計を集計する。列: month(Timestamp, 月初), total"""
    out = df.copy()
    out["month"] = out["date"].dt.to_period("M").dt.to_timestamp()
    monthly = out.groupby("month", as_index=False)["amount"].sum()
    monthly = monthly.rename(columns={"amount": "total"})
    return monthly.sort_values("month").reset_index(drop=True)


def monthly_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """月×カテゴリの支出合計を集計する。"""
    out = df.copy()
    out["month"] = out["date"].dt.to_period("M").dt.to_timestamp()
    pivot = out.groupby(["month", "category"], as_index=False)["amount"].sum()
    return pivot.sort_values(["month", "category"]).reset_index(drop=True)


@dataclass
class ForecastResult:
    model: object | None
    slope: float
    intercept: float
    r_squared: float
    next_month: pd.Timestamp | None
    predicted_total: float
    lower: float
    upper: float


def forecast_next_month(monthly: pd.DataFrame, level: float = 0.95) -> ForecastResult:
    """月次合計の推移から線形回帰で来月の支出合計を予測する。

    月データが2件未満の場合は予測不能として扱う。
    """
    na_result = ForecastResult(
        model=None, slope=float("nan"), intercept=float("nan"), r_squared=float("nan"),
        next_month=None, predicted_total=float("nan"), lower=float("nan"), upper=float("nan"),
    )

    if len(monthly) < 2:
        return na_result

    x = np.arange(len(monthly)).reshape(-1, 1)
    y = monthly["total"].values

    model = LinearRegression()
    model.fit(x, y)

    y_pred = model.predict(x)
    residuals = y - y_pred
    r_squared = model.score(x, y)

    next_x = np.array([[len(monthly)]])
    predicted = float(model.predict(next_x)[0])

    # 予測区間: 残差の標準偏差を使った簡易的な区間（正規分布近似）
    resid_sd = float(np.std(residuals, ddof=min(2, len(residuals) - 1) if len(residuals) > 2 else 0))
    # 95%であればおよそ1.96 SD、水準に応じて簡易調整
    z_value = 1.96 if level >= 0.95 else 1.64
    margin = z_value * resid_sd

    last_month = monthly["month"].iloc[-1]
    next_month = (last_month + pd.offsets.MonthBegin(1))

    return ForecastResult(
        model=model,
        slope=float(model.coef_[0]),
        intercept=float(model.intercept_),
        r_squared=float(r_squared),
        next_month=next_month,
        predicted_total=predicted,
        lower=predicted - margin,
        upper=predicted + margin,
    )
