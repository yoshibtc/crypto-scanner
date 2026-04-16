from cgd.config.ccxt_matrix_loader import iter_enabled_ccxt_source_keys, load_matrix


def test_load_matrix_has_venues():
    data = load_matrix()
    assert "venues" in data


def test_iter_enabled_keys_respects_yaml():
    keys = iter_enabled_ccxt_source_keys()
    assert isinstance(keys, list)
    assert all(k.startswith("ccxt:") for k in keys)
    assert "ccxt:binance" in keys
    assert "ccxt:coinbase" not in keys
