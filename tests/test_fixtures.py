import json
from pathlib import Path


def test_defillama_fixture_loads():
    p = Path(__file__).parent / "fixtures" / "defillama" / "protocol_sample.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("tvl") is not None
    assert "fdv" in data
