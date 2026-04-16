from cgd.collectors.defillama import extract_protocol_snapshot


def test_extract_top_level():
    data = {"tvl": 1.0, "fdv": 2.0, "fees": 3.0, "revenue": 4.0}
    p = extract_protocol_snapshot(data, "x")
    assert p["tvl"] == 1.0 and p["fees"] == 3.0


def test_extract_metrics_nested():
    data = {
        "tvl": 100,
        "metrics": {"fees": {"total7d": 50}, "revenue": 10, "mcap": 999},
    }
    p = extract_protocol_snapshot(data, "y")
    assert p["tvl"] == 100
    assert p["fees"] == 50
    assert p["revenue"] == 10
    assert p["fdv"] == 999
