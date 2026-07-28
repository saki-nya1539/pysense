"""core/data_ingest.py

CSVの取込・列の自動推定・バリデーションを行う。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

DATE_CANDIDATES = ["date", "取引日", "日付", "利用日"]
CATEGORY_CANDIDATES = ["category", "カテゴリ", "費目", "分類"]
AMOUNT_CANDIDATES = ["amount", "金額", "支出額", "price"]


def read_transactions_csv(path_or_buffer) -> pd.DataFrame:
    """CSVを読み込む。UTF-8で失敗した場合はShift-JIS(CP932)を試す。"""
    try:
        df = pd.read_csv(path_or_buffer, encoding="utf-8-sig")
    except UnicodeDecodeError:
        path_or_buffer.seek(0) if hasattr(path_or_buffer, "seek") else None
        df = pd.read_csv(path_or_buffer, encoding="cp932")

    # 文字化け(U+FFFD)が列名に含まれる場合はCP932で読み直す
    if any("�" in str(c) for c in df.columns) and hasattr(path_or_buffer, "seek"):
        path_or_buffer.seek(0)
        df = pd.read_csv(path_or_buffer, encoding="cp932")

    return df


def _find_by_name(columns, candidates):
    lower_map = {str(c).strip().lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    # 部分一致
    for cand in candidates:
        for col in columns:
            if cand.lower() in str(col).lower():
                return col
    return None


@dataclass
class ColumnGuess:
    date_col: str | None = None
    category_col: str | None = None
    amount_col: str | None = None
    warnings: list[str] = field(default_factory=list)


def guess_columns(df: pd.DataFrame) -> ColumnGuess:
    guess = ColumnGuess()
    guess.date_col = _find_by_name(df.columns, DATE_CANDIDATES)
    guess.category_col = _find_by_name(df.columns, CATEGORY_CANDIDATES)
    guess.amount_col = _find_by_name(df.columns, AMOUNT_CANDIDATES)

    if guess.date_col is None:
        guess.warnings.append("日付列を自動判定できませんでした。手動で選択してください。")
    if guess.category_col is None:
        guess.warnings.append("カテゴリ列を自動判定できませんでした。手動で選択してください。")
    if guess.amount_col is None:
        guess.warnings.append("金額列を自動判定できませんでした。手動で選択してください。")

    return guess


def validate_and_prepare(
    df: pd.DataFrame, date_col: str, category_col: str, amount_col: str
) -> pd.DataFrame:
    """指定された列を使って date/category/amount の3列に正規化する。"""
    missing = [c for c in (date_col, category_col, amount_col) if c not in df.columns]
    if missing:
        raise ValueError(f"指定された列が見つかりません: {missing}")

    out = df[[date_col, category_col, amount_col]].copy()
    out.columns = ["date", "category", "amount"]

    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce")

    n_before = len(out)
    out = out.dropna(subset=["date", "amount"])
    n_dropped = n_before - len(out)

    out["category"] = out["category"].fillna("未分類").astype(str)
    out = out.sort_values("date").reset_index(drop=True)

    if n_dropped > 0:
        out.attrs["n_dropped"] = n_dropped

    return out
