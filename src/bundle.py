"""데모 번들 읽기 (엔진은 실행하지 않음). 번들은 scripts/build_demo_bundle.py가 만든다."""
import json
from pathlib import Path

import pandas as pd


def bundle_ok(d: Path) -> bool:
    return (d / "index.json").exists()


def load_index(d: Path) -> dict:
    return json.load(open(d / "index.json", encoding="utf-8"))


def load_mol(d: Path, mid: str) -> dict:
    return json.load(open(d / f"mol_{mid}.json", encoding="utf-8"))


def load_cands(d: Path, mid: str) -> pd.DataFrame:
    return pd.read_parquet(d / f"cands_{mid}.parquet")


def label(m: dict) -> str:
    """목록·사이드바에 쓰는 짧은 이름 (정답 구조는 드러내지 않음)."""
    return f"[{m['scenario']}] {m['mid']} · {m['formula']} · {m['mass']:.4f} Da"


def perf_table(mols: list) -> pd.DataFrame:
    """C1/C2/C3별 Top-1/Top-5/Top-25/MRR (정답 순위는 metric key 기준, 25위 밖은 0점)."""
    rows = []
    for scen in ("C1", "C2", "C3", "전체"):
        ms = [m for m in mols if m["scenario"] in ("C1", "C2", "C3") and (scen == "전체" or m["scenario"] == scen)]
        r = [m["truth_rank"] for m in ms]
        rr = [1.0 / x if x and x <= 25 else 0.0 for x in r]
        rows.append({"시나리오": scen, "분자 수": len(ms),
                     "Top-1": sum(1 for x in r if x == 1), "Top-5": sum(1 for x in r if x and x <= 5),
                     "Top-25": sum(1 for x in r if x and x <= 25),
                     "후보 포함": sum(1 for m in ms if m["in_candidates"]),
                     "MRR": sum(rr) / max(len(rr), 1)})
    return pd.DataFrame(rows)
