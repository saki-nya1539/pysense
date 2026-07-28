from core.sample_data import generate_sample_transactions


def test_generate_sample_transactions_has_expected_columns():
    df = generate_sample_transactions(n_days=90, seed=1)
    assert list(df.columns) == ["date", "category", "amount", "description"]
    assert len(df) > 0


def test_generate_sample_transactions_is_deterministic_with_seed():
    df1 = generate_sample_transactions(n_days=90, seed=1)
    df2 = generate_sample_transactions(n_days=90, seed=1)
    assert df1.equals(df2)


def test_generate_sample_transactions_amounts_are_positive():
    df = generate_sample_transactions(n_days=90, seed=1)
    assert (df["amount"] > 0).all()


def test_generate_sample_transactions_respects_anomaly_count():
    df_with = generate_sample_transactions(n_days=180, seed=7, anomaly_count=6)
    assert (df_with["description"].str.contains("臨時")).sum() == 6

    df_without = generate_sample_transactions(n_days=180, seed=7, anomaly_count=0)
    assert (df_without["description"].str.contains("臨時")).sum() == 0
