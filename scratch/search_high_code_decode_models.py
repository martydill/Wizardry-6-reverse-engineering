from __future__ import annotations

import argparse
import json
from pathlib import Path

import importlib.util


def load_renderer_module():
    p = Path("scratch/render_map_3d_owner_prototype.py")
    spec = importlib.util.spec_from_file_location("render_map_3d_owner_prototype", p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to import {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def orient_score(cx: float, expected: str) -> float:
    if expected == "center":
        d = abs(cx - 88.0)
        return max(0.0, 1.0 - d / 60.0)
    if expected == "left":
        return max(0.0, min(1.0, (90.0 - cx) / 90.0))
    if expected == "right":
        return max(0.0, min(1.0, (cx - 86.0) / 90.0))
    return 0.0


def model_to_owner(code: int, model: str, k: int) -> int | None:
    if 0 <= code <= 152:
        return code
    if not (153 <= code <= 180):
        return None
    if model == "minus_k":
        o = code - k
    elif model == "and_7f":
        o = code & 0x7F
    elif model == "minus_128":
        o = code - 128
    elif model == "identity":
        o = code
    else:
        return None
    return o if 0 <= o <= 152 else None


def score_set(codes12: list[int], owner_metric: dict[int, dict[str, float]], model: str, k: int):
    exp = [
        ("center", 1),
        ("left", 1),
        ("right", 1),
        ("center", 2),
        ("left", 2),
        ("right", 2),
        ("center", 3),
        ("left", 3),
        ("right", 3),
        ("center", 4),
        ("left", 4),
        ("right", 4),
    ]
    orient_acc = 0.0
    warm_acc = 0.0
    warm_n = 0
    by_orient = {"center": [], "left": [], "right": []}
    valid_n = 0
    high_mapped_n = 0
    high_total_n = sum(1 for c in codes12 if c > 152)
    for i, code in enumerate(codes12[:12]):
        owner = model_to_owner(code, model, k)
        if owner is None:
            continue
        if code > 152:
            high_mapped_n += 1
        m = owner_metric.get(owner)
        if not m:
            continue
        eo, _ = exp[i]
        orient_acc += orient_score(m["cx"], eo)
        by_orient[eo].append(m["area"])
        warm_acc += m["warm_ratio"]
        warm_n += 1
        valid_n += 1

    mono = 0.0
    mono_n = 0
    for eo in ("center", "left", "right"):
        arr = by_orient[eo]
        if len(arr) >= 2:
            for i in range(1, len(arr)):
                mono += 1.0 if arr[i - 1] >= arr[i] else 0.0
                mono_n += 1
    mono_score = (mono / mono_n) if mono_n else 0.0
    warm = (warm_acc / warm_n) if warm_n else 0.0

    # Similar to existing structural prior, with strong penalty if high codes fail to map.
    structural = orient_acc + 4.0 * mono_score - 2.5 * warm
    if high_total_n:
        structural += 3.0 * (high_mapped_n / high_total_n)
    return {
        "score": structural,
        "valid_n": valid_n,
        "high_total_n": high_total_n,
        "high_mapped_n": high_mapped_n,
    }


def slot_order() -> list[str]:
    return [
        "center_d1",
        "left_d1",
        "right_d1",
        "center_d2",
        "left_d2",
        "right_d2",
        "center_d3",
        "left_d3",
        "right_d3",
        "center_d4",
        "left_d4",
        "right_d4",
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description="Rank high-code decode formulas by structural plausibility.")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument("--maps", default="11,12")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("scratch/map_owner_streams/high_decode_model_search.json"),
    )
    args = ap.parse_args()

    mod = load_renderer_module()
    db = (args.gamedata / "NEWGAME.DBS").read_bytes()
    mpath = args.gamedata / "MAZEDATA.EGA"
    sprites = mod.decode_mazedata_tiles(mpath)
    recs = mod.parse_display_records(mpath)
    by_owner = {}
    for r in recs:
        by_owner.setdefault(r["owner_id"], []).append(r)
    owner_img = {oid: mod.render_owner(rs, sprites) for oid, rs in by_owner.items()}
    owner_metric = {oid: mod.owner_metrics(im) for oid, im in owner_img.items()}

    map_ids = [int(x.strip(), 0) for x in args.maps.split(",") if x.strip()]
    offsets = {1: 0x24, 2: 0x00, 3: 0x48}
    slots = slot_order()

    # Build slot priors from low-code observations over all maps.
    slot_prior_vals: dict[tuple[int, str], list[int]] = {}
    for map_id in range(16):
        for wv in (1, 2, 3):
            s = mod.extract_map_stream_at_offset(db, map_id, offsets[wv])
            sets = mod.stream_sets_from_codes(s)
            if not sets:
                sets = mod.stream_sets_from_codes(mod.extract_primary_map_stream(db, map_id))
            if not sets:
                continue
            codes12 = sets[0]
            for i, code in enumerate(codes12[:12]):
                if code > 152:
                    continue
                sk = slots[i]
                slot_prior_vals.setdefault((wv, sk), []).append(code)
    slot_prior_mean: dict[tuple[int, str], float] = {}
    for kps, arr in slot_prior_vals.items():
        if arr:
            slot_prior_mean[kps] = sum(arr) / len(arr)

    models = []
    for k in range(1, 96):
        models.append(("minus_k", k, f"minus_{k}"))
    models.extend(
        [
            ("and_7f", 0, "and_7f"),
            ("minus_128", 0, "minus_128"),
            ("identity", 0, "identity"),
        ]
    )

    per_model = {}
    for model, k, tag in models:
        total = 0.0
        terms = 0
        details = []
        for map_id in map_ids:
            for wv in (1, 2, 3):
                s = mod.extract_map_stream_at_offset(db, map_id, offsets[wv])
                sets = mod.stream_sets_from_codes(s)
                if not sets:
                    sets = mod.stream_sets_from_codes(mod.extract_primary_map_stream(db, map_id))
                if not sets:
                    continue
                codes12 = sets[0]
                sc = score_set(codes12, owner_metric, model, k)
                # Prior term: mapped high-code owner should be near low-code owner range
                # typically observed for this wall/slot family.
                prior_acc = 0.0
                prior_n = 0
                for i, code in enumerate(codes12[:12]):
                    if code <= 152:
                        continue
                    sk = slots[i]
                    mu = slot_prior_mean.get((wv, sk))
                    owner = model_to_owner(code, model, k)
                    if mu is None or owner is None:
                        continue
                    prior_acc += abs(owner - mu)
                    prior_n += 1
                prior_penalty = (prior_acc / prior_n) if prior_n else 0.0
                # Keep structural signal dominant but suppress implausible owner bands.
                combined = sc["score"] - 0.12 * prior_penalty
                total += sc["score"]
                terms += 1
                details.append(
                    {
                        "map": map_id,
                        "wall_value": wv,
                        "combined_score": combined,
                        "prior_penalty": prior_penalty,
                        **sc,
                    }
                )
                total += (combined - sc["score"])
        avg = (total / terms) if terms else -1e9
        per_model[tag] = {"avg_score": avg, "terms": terms, "details": details}

    ranked = sorted(per_model.items(), key=lambda kv: kv[1]["avg_score"], reverse=True)
    out = {
        "maps": map_ids,
        "top": [{"model": k, **v} for k, v in ranked[:25]],
        "best": {"model": ranked[0][0], **ranked[0][1]} if ranked else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}")
    if ranked:
        print("Top 10:")
        for k, v in ranked[:10]:
            print(f"  {k}: {v['avg_score']:.4f}")


if __name__ == "__main__":
    main()
