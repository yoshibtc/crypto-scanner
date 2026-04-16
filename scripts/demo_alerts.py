"""Print sample Telegram bodies (same template as production). Run: python scripts/demo_alerts.py"""
from __future__ import annotations

from types import SimpleNamespace

from cgd.alerts.renderers import render_gap_alert

# render_gap_alert only reads these attributes
Entity = SimpleNamespace
Gap = SimpleNamespace


def main() -> None:
    demos: list[tuple[str, object, object]] = [
        (
            "P7 - leverage / positioning stress",
            Entity(slug="btc-binance-perp", display_name="BTC perp (Binance pilot)"),
            Gap(
                pattern_id="P7",
                status="ESCALATED",
                payload_json={
                    "oi_change_pct": 31.4159,
                    "funding_rate": -0.0008,
                    "price_change_pct_24h": 0.12,
                    "venue": "binance",
                    "framing": "positioning_leverage_stress",
                },
                supporting_observation_refs={
                    "old_fact_ts": "2026-04-10T12:00:00+00:00",
                    "new_fact_ts": "2026-04-16T12:00:00+00:00",
                },
            ),
        ),
        (
            "P10 - CEX peg drift leg",
            Entity(slug="stable-usdt", display_name="USDT peg watch"),
            Gap(
                pattern_id="P10",
                status="ESCALATED",
                payload_json={"leg": "CEX", "hours": 4, "peg_drift": 0.005},
                supporting_observation_refs={"last_ts": "2026-04-16T11:00:00+00:00"},
            ),
        ),
        (
            "P10 - DEX pool skew leg",
            Entity(slug="stable-usdt", display_name="USDT peg watch"),
            Gap(
                pattern_id="P10",
                status="ESCALATED",
                payload_json={"leg": "DEX", "major_share": 0.78},
                supporting_observation_refs={"source_ts": "2026-04-16T10:30:00+00:00"},
            ),
        ),
        (
            "P6 - FDV up vs fees down",
            Entity(slug="llama-aave", display_name="Aave (Llama pilot)"),
            Gap(
                pattern_id="P6",
                status="ESCALATED",
                payload_json={"fdv_wow_pct": 28.5, "fee_wow_pct": -18.2},
                supporting_observation_refs={
                    "old_ts": "2026-04-01T00:00:00+00:00",
                    "new_ts": "2026-04-16T00:00:00+00:00",
                },
            ),
        ),
        (
            "P2 - TVL up vs native inflow share",
            Entity(slug="llama-aave", display_name="Aave (Llama pilot)"),
            Gap(
                pattern_id="P2",
                status="ESCALATED",
                payload_json={"tvl_wow_pct": 22.0, "native_share": 0.88},
                supporting_observation_refs={"composition_ts": "2026-04-15T18:00:00+00:00"},
            ),
        ),
        (
            "P1 - unlock pressure vs liquidity",
            Entity(slug="demo-unlock", display_name="Demo unlock entity"),
            Gap(
                pattern_id="P1",
                status="ESCALATED",
                payload_json={
                    "unlock_pct_circ": 0.08,
                    "unlock_fiat": 42_000_000.0,
                    "adv_14d": 9_500_000.0,
                },
                supporting_observation_refs={
                    "vesting_adapter": "stub_adapter",
                    "source_ts": "2026-04-16T08:00:00+00:00",
                },
            ),
        ),
    ]

    for title, ent, gap in demos:
        print("=" * 60)
        print(title)
        print("=" * 60)
        print(render_gap_alert(ent, gap))
        print()


if __name__ == "__main__":
    main()
