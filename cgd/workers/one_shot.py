"""Local one-shot entrypoints (no Celery)."""


def run_evaluate() -> None:
    from cgd.engine.runner import run_tier1_evaluation

    print(run_tier1_evaluation())


def run_ingest_defillama() -> None:
    from cgd.collectors.defillama import ingest_defillama_snapshot

    print({"rows": ingest_defillama_snapshot()})


def run_ingest_ccxt() -> None:
    from cgd.collectors.ccxt_collector import ingest_ccxt_snapshot

    print({"rows": ingest_ccxt_snapshot()})
