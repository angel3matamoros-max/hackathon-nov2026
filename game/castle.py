"""Castle Maker data. A castle is up to 10 levels; each level picks a premade background theme, a platform layout, waves and a boss.

A castle is plain JSON (saved in the `castles/` folder):
  {"name": "My Castle", "levels": [{"theme": 0-5, "layout": "A|B|C|none", "style": "wave", "waves": [[["zombie", 3]], ...],
                                    "boss": "gravekeeper" | null, "name": "optional level title"}]}
build_level() turns a level spec into the same dict shape the arena already plays (see levels.LEVELS)."""
import json
import os
import re
from .config import *
from .levels import LEVELS
from .enemies import ESTATS
from .bosses import BOSSES

CASTLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "castles")
MAX_LEVELS, MAX_WAVES, MAX_PER_WAVE, MAX_NAME = 10, 8, 14, 24
THEMES = [("Basement", 0), ("Jungle", 1), ("Cathedral", 2), ("Necropolis", 3), ("Penthouse", 4), ("Observatory", 5)]
LAYOUTS = {  # platform presets for one-screen (wave) levels: (x, y, width)
    "A": [(70, 176, 96), (310, 170, 96), (190, 128, 100)],
    "B": [(40, 172, 90), (350, 172, 90), (150, 138, 80), (250, 138, 80)],
    "C": [(48, 174, 84), (348, 174, 84), (130, 132, 76), (274, 132, 76), (200, 94, 80)],
    "none": [],
}
ENEMY_KINDS = [k for k in ESTATS if k not in BOSSES and k != "dummy"]
BOSS_CHOICES = list(BOSSES)


def default_level(theme=0):
    t = LEVELS[theme]
    return dict(theme=theme, layout="A", style="wave", boss=t["boss"], waves=[[list(w) for w in wv] for wv in _template_waves(t)])


def _template_waves(t):
    from .levels import waves_of
    return waves_of(t)


def new_castle(name="My Castle"):
    return dict(name=name, levels=[default_level(0)])


def tier_for(i, n):
    """Difficulty tier of level i in a castle of n levels. The main campaign is tier = level; a long custom castle is spread over tiers 0..5
    (so a 10-level castle does not reach the 0.75**9 / 1.25**9 extremes)."""
    return i if n <= 6 else int(round(i * 5 / (n - 1)))


def validate_castle(spec):
    """List of human-readable problems (empty = valid)."""
    errs = []
    if not isinstance(spec, dict): return ["castle is not a JSON object"]
    if not isinstance(spec.get("name"), str) or not spec["name"].strip(): errs.append("castle needs a name")
    elif len(spec["name"]) > MAX_NAME: errs.append(f"castle name longer than {MAX_NAME} characters")
    lv = spec.get("levels")
    if not isinstance(lv, list) or not lv: return errs + ["castle needs at least 1 level"]
    if len(lv) > MAX_LEVELS: errs.append(f"too many levels ({len(lv)} > {MAX_LEVELS})")
    for i, L in enumerate(lv):
        tag = f"level {i + 1}"
        if not isinstance(L, dict): errs.append(f"{tag}: not an object"); continue
        if L.get("theme") not in range(len(THEMES)): errs.append(f"{tag}: unknown theme {L.get('theme')!r}")
        if L.get("layout", "A") not in LAYOUTS: errs.append(f"{tag}: unknown layout {L.get('layout')!r}")
        if L.get("style", "wave") != "wave": errs.append(f"{tag}: unknown style {L.get('style')!r}")
        if L.get("boss") is not None and L.get("boss") not in BOSSES: errs.append(f"{tag}: unknown boss {L.get('boss')!r}")
        ws = L.get("waves")
        if not isinstance(ws, list) or not ws: errs.append(f"{tag}: needs at least 1 wave"); continue
        if len(ws) > MAX_WAVES: errs.append(f"{tag}: too many waves ({len(ws)} > {MAX_WAVES})")
        for j, wv in enumerate(ws):
            if not isinstance(wv, list) or not wv: errs.append(f"{tag} wave {j + 1}: empty"); continue
            total = 0
            for ent in wv:
                if not (isinstance(ent, (list, tuple)) and len(ent) == 2 and ent[0] in ENEMY_KINDS and isinstance(ent[1], int) and not isinstance(ent[1], bool) and ent[1] >= 1):
                    errs.append(f"{tag} wave {j + 1}: bad entry {ent!r}"); continue
                total += ent[1]
            if total > MAX_PER_WAVE: errs.append(f"{tag} wave {j + 1}: {total} enemies (max {MAX_PER_WAVE})")
    return errs


def build_level(spec):
    """A playable level dict (same keys as levels.LEVELS entries) from one level spec."""
    t = dict(LEVELS[spec["theme"]], theme=spec["theme"])
    t.update(plats=list(LAYOUTS[spec.get("layout", "A")]), waves=[[tuple(e) for e in wv] for wv in spec["waves"]], boss=spec.get("boss"),
             style="wave", hint=False, chest=bool(spec.get("boss") == "paladin"))
    for k in ("spawns", "chests", "pits", "length"): t.pop(k, None)
    if spec.get("name"): t["name"] = str(spec["name"])[:MAX_NAME]
    return t


def castle_levels(spec):
    return [build_level(L) for L in spec["levels"]]


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "castle"


def save_castle(spec, directory=None):
    """Write the castle to castles/<slug>.json (validated first). Returns the path. Raises ValueError on an invalid castle."""
    errs = validate_castle(spec)
    if errs: raise ValueError("; ".join(errs))
    directory = directory or CASTLE_DIR
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, slug(spec["name"]) + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f: json.dump(spec, f, indent=1)
    os.replace(tmp, path)  # never leave a half-written file behind
    return path


def load_castle(path):
    """(spec, errors). A broken or invalid file gives (None, [reason]) instead of raising."""
    try:
        with open(path) as f: spec = json.load(f)
    except Exception as e:
        return None, [f"cannot read: {e.__class__.__name__}"]
    errs = validate_castle(spec)
    return (None if errs else spec), errs


def list_castles(directory=None):
    """[(path, name, n_levels, errors)] for every *.json in the castles folder (examples/ included), sorted by name."""
    directory = directory or CASTLE_DIR
    out = []
    for root, _, files in os.walk(directory):
        for fn in sorted(files):
            if fn.endswith(".json"):
                path = os.path.join(root, fn)
                spec, errs = load_castle(path)
                out.append((path, spec["name"] if spec else fn, len(spec["levels"]) if spec else 0, errs))
    return sorted(out, key=lambda r: r[1].lower())
