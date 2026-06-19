from __future__ import annotations
import json
from pathlib import Path


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["canonical_scores"] = {
        cat: tuple(score) for cat, score in cfg["canonical_scores"].items()
    }
    return cfg


def save(cfg: dict, path: str) -> None:
    out = {
        "t_lower": cfg["t_lower"],
        "t_upper": cfg["t_upper"],
        "canonical_scores": {
            cat: list(score) for cat, score in cfg["canonical_scores"].items()
        },
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
