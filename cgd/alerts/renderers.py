from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cgd.db.models import Entity, Gap


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def render_gap_alert(entity: Entity, gap: Gap) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_templates_dir())),
        autoescape=select_autoescape(enabled_extensions=()),
    )
    env.filters["tojson"] = lambda o: json.dumps(o, indent=2, default=str)
    tpl = env.get_template("tier1_alert.txt")
    text = tpl.render(
        entity_slug=entity.slug,
        entity_name=entity.display_name,
        pattern_id=gap.pattern_id,
        status=gap.status,
        payload=gap.payload_json,
        refs=gap.supporting_observation_refs,
    )
    max_len = 3900
    if len(text) > max_len:
        text = text[: max_len - 20] + "\n...[truncated]"
    return text
