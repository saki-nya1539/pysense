import io

import pandas as pd
import pytest

from core.data_ingest import guess_columns, read_transactions_csv, validate_and_prepare


def test_guess_columns_finds_standard_names():
    df = pd.DataFrame({"date": [], "category": [], "amount": []})
    guess = guess_columns(df)
    assert guess.date_col == "date"
    assert guess.category_col == "category"
    assert guess.amount_col == "amount"
    assert guess.warnings == []


def test_guess_columns_finds_japanese_names():
    df = pd.DataFrame({"取引日": [], "費目": [], "金額": []})
    guess = guess_columns(df)
    assert guess.date_col == "取引日"
    assert guess.category_col == "費目"
    assert guess.amount_col == "金額"


def test_guess_columns_warns_when_not_found():
    df = pd.DataFrame({"foo": [], "bar": []})
    guess = guess_columns(df)
    assert guess.date_col is None
    assert len(guess.warnings) == 3


def test_read_transactions_csv_utf8():
    csv_text = "date,category,amount\n2026-01-01,食費,1000\n"
    buf = io.BytesIO(csv_text.encode("utf-8"))
    df = read_transactions_csv(buf)
    assert len(df) == 1
    assert df.iloc[0]["amount"] == 1000


def test_validate_and_prepare_normalizes_columns():
    df = pd.DataFrame(
        {
            "取引日": ["2026-01-01", "2026-01-02", "invalid-date"],
            "費目": ["食費", "交通費", "娯楽"],
            "金額": ["1000", "not-a-number", "500"],
        }
    )
    out = validate_and_prepare(df, "取引日", "費目", "金額")
    assert list(out.columns) == ["date", "category", "amount"]
    # 日付か金額が不正な行は落ちる（2行落ちて1行だけ残る）
    assert len(out) == 1
    assert out.iloc[0]["category"] == "食費"


def test_validate_and_prepare_raises_on_missing_column():
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    with pytest.raises(ValueError):
        validate_and_prepare(df, "a", "b", "missing_col")
