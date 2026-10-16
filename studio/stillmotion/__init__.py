"""stillmotion — small, free, local animation for still pictures (AI paintings, illustrations, ink drawings).

    from stillmotion import Clip, render
    render("s020.png", "s020.mp4", seconds=7, spec={"camera": {"move": "in", "parallax": 0.6},
                                                      "fx": [{"type": "sway", "box": [0, .6, 1, 1]}]})

No video or audio is generated from scratch: the picture stays the picture; parts of it move.
"""
from .engine import Clip, encode, render
from .presets import PRESETS, auto_spec
from .spec import Spec, parse

__all__ = ["Clip", "render", "encode", "parse", "Spec", "PRESETS", "auto_spec"]
__version__ = "1.0.0"
