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
    out: dict = {
        "t_lower": cfg["t_lower"],
        "t_upper": cfg["t_upper"],
        "canonical_scores": {
            cat: list(score) if score is not None else [1, 0]
            for cat, score in cfg["canonical_scores"].items()
        },
    }
    if "d_threshold" in cfg:
        out["d_threshold"] = cfg["d_threshold"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def is_v3(cfg: dict) -> bool:
    return "d_threshold" in cfg
