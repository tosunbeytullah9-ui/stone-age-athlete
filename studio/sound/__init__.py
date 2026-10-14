"""Sound design: ambience beds + spot effects layered under the narration (docs/SOUND.md).

  synth.py     built-in sounds made by code (no licence, no download)
  catalog.py   sound ids → audio (built-in or library/sounds/catalog.yaml files, licence-checked)
  designer.py  which bed under which scene, which effect on which word (automatic + storyboard overrides)
  mixdown.py   plan → ambience.wav + effects.wav stems, levelled against the voice

The render step calls `design_stems`; `python -m studio sound <slug>` writes the plan without rendering, and
`python -m studio sounds-demo` renders every sound into one file to listen to.
"""
from __future__ import annotations

import json
from pathlib import Path


def brand_of(cfg) -> dict:
    return dict(cfg.get_path("channel.sound") or {})


def make_plan(project, cfg, lang: str, groups: list[list[dict]], timing: list[dict], end: float | None = None) -> dict:
    from .designer import plan, summary
    p = plan(groups, timing, brand_of(cfg), bool(cfg.get_path("audio.ambience", True)),
             bool(cfg.get_path("audio.effects", True)), end)
    p["summary"] = summary(p, len(groups))
    out = project.lang_dir(lang) / "sound_plan.json"
    out.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding="utf-8")
    return p


def design_stems(project, cfg, lang: str, groups, timing, total: float, work: Path) -> list[Path]:
    from .mixdown import build_stems
    p = make_plan(project, cfg, lang, groups, timing, end=total)
    stems = build_stems(p, project.audio_dir(lang) / "narration.wav", total, work, cfg)
    s = p["summary"]
    print(f"  ses: {len(s['amb_kinds'])} çeşit ortam sesi (%{s['amb_coverage'] * 100:.0f} kapsama), "
          f"{s['sfx_count']} efekt ({s['sfx_per_min']:.1f}/dk)")
    return list(stems.values())


def demo(out: Path, gap: float = 0.6, amb_seconds: float = 6.0) -> Path:
    """Every sound back to back (ambience: 6 s each) with a short beep before each, plus a text index."""
    import numpy as np
    from . import catalog, synth
    ids = catalog.all_ids()
    parts, index, t = [], [], 0.0
    beep = synth.pan(synth.tone(1000, 0.08) * 0.1, 0)
    for kind in ("amb", "sfx"):
        for sid in ids[kind]:
            try:
                x = catalog.get(sid)
            except Exception as e:                       # noqa: BLE001
                index.append(f"{sid}: HATA {e}")
                continue
            if kind == "amb":
                x = x[: int(amb_seconds * catalog.SR)]
            peak = float(np.abs(x).max()) or 1.0
            x = x / peak * 0.5
            index.append(f"{t:7.1f} s  [{kind}] {sid}")
            seg = np.concatenate([beep, np.zeros((int(0.3 * catalog.SR), 2), "float32"), synth.fade(x, 0.01, 0.2),
                                  np.zeros((int(gap * catalog.SR), 2), "float32")])
            parts.append(seg)
            t += len(seg) / catalog.SR
    catalog.write_wav(out, np.concatenate(parts))
    out.with_suffix(".txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    return out
