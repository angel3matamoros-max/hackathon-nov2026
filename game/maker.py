"""Castle Maker: the editor's state (Editor, plain logic with no pygame input), a live preview, and the screens.

Editor is a list of rows. Up/Down (or the stick, or the mouse) picks a row, Left/Right (or the arrows) changes its value, Enter does its
action. The level strip along the top picks a level (click it, or the + tile to add one). The preview on the right shows the selected
level's real background, its platform layout and its waves cycling with their enemies and boss. app.py maps input onto this."""
import pygame

from .config import *
from .gfx import text, title_text, font, fit_lines
from .levels import LEVELS, get_bg
from .sprites import ENEMY
from .enemies import ESTATS
from .bosses import BOSSES
from .castle import build_level
from . import gfx
from . import castle as C

THEME_NAMES = [n for n, _ in C.THEMES]
BOSS_OPTS = [None] + C.BOSS_CHOICES
LAYOUT_OPTS = list(C.LAYOUTS)
MAX_COUNT = 5                                     # enemies per wave entry
CHANGEABLE = ("level", "theme", "layout", "boss", "wave")
ACTIONS = ("test", "save", "play", "back")

# ---------------------------------------------------------------- layout (canvas pixels)
STRIP_Y, TILE_W, TILE_H, TILE_STEP = 32, 38, 16, 42   # level strip (below the title)
PANEL = pygame.Rect(6, 52, 236, 186)
ROW_Y, ROW_H, VISIBLE = 56, 12, 15
ARROW_L, ARROW_R = 200, 226                       # x of the < and > hit zones (each 14 px wide)
PREV = pygame.Rect(250, 52, 224, 126)
INFO = pygame.Rect(250, 182, 224, 60)
MSG_Y, HINT_Y = 246, 258
LIST_Y, LIST_STEP = 52, 15                        # castle list (rows, left side)
WAVE_SECONDS = 1.8                                # how long the preview shows each wave


def boss_name(kind):
    return BOSSES[kind]["name"] if kind in BOSSES else "none"


class Editor:
    def __init__(s, spec=None, path=None):
        s.spec = spec if spec is not None else C.new_castle()
        s.path, s.li, s.row, s.top, s.typing, s.msg = path, 0, 0, 0, False, ""

    # ------------------------------------------------------------ rows
    @property
    def L(s):
        return s.spec["levels"][s.li]

    def rows(s):
        r = [("name",), ("level",), ("theme",), ("layout",), ("boss",)]
        r += [("wave", j) for j in range(len(s.L["waves"]))]
        return r + [("add_wave",), ("del_wave",), ("add_level",), ("del_level",), ("test",), ("save",), ("play",), ("back",)]

    def sel(s):
        return s.rows()[min(s.row, len(s.rows()) - 1)]

    def label(s, row):
        k, L = row[0], s.L
        if k == "name": return f"Name: {s.spec['name']}" + ("_" if s.typing else "")
        if k == "level": return f"Level {s.li + 1} of {len(s.spec['levels'])}"
        if k == "theme": return f"Theme: {THEME_NAMES[L['theme']]}"
        if k == "layout": return f"Platforms: {L.get('layout', 'A')}"
        if k == "boss": return f"Boss: {boss_name(L.get('boss'))}"
        if k == "wave":
            kind, n = L["waves"][row[1]][0]
            return f"Wave {row[1] + 1}: {kind} x{n}"
        return {"add_wave": "+ Add wave", "del_wave": "- Remove last wave", "add_level": "+ Add level", "del_level": "- Delete this level",
                "test": "TEST this level", "save": "SAVE castle", "play": "PLAY castle", "back": "BACK to castles"}[k]

    def move(s, d):
        s.row = (s.row + d) % len(s.rows())

    def change(s, d):
        """Left/Right on the selected row."""
        row, L = s.sel(), s.L
        k = row[0]
        if k == "level": s.pick_level((s.li + d) % len(s.spec["levels"]))
        elif k == "theme": L["theme"] = (L["theme"] + d) % len(THEME_NAMES)
        elif k == "layout": L["layout"] = LAYOUT_OPTS[(LAYOUT_OPTS.index(L.get("layout", "A")) + d) % len(LAYOUT_OPTS)]
        elif k == "boss": L["boss"] = BOSS_OPTS[(BOSS_OPTS.index(L.get("boss")) + d) % len(BOSS_OPTS)]
        elif k == "wave":
            e = L["waves"][row[1]][0]
            e[0] = C.ENEMY_KINDS[(C.ENEMY_KINDS.index(e[0]) + d) % len(C.ENEMY_KINDS)]

    def act(s):
        """Enter on the selected row. Returns 'test', 'save', 'play', 'back' for the app to handle, else None."""
        row = s.sel()
        k = row[0]
        if k == "name": s.typing, s.msg = True, "Type the castle name. Enter when done."
        elif k == "wave":
            e = s.L["waves"][row[1]][0]
            e[1] = e[1] % MAX_COUNT + 1
        elif k == "add_wave": s.add_wave()
        elif k == "del_wave": s.del_wave()
        elif k == "add_level": s.add_level()
        elif k == "del_level": s.del_level()
        elif k in ACTIONS: return k
        return None

    def pick_level(s, i):
        s.li, s.row = i, 1

    # ------------------------------------------------------------ structure edits
    def add_wave(s):
        L = s.L
        if len(L["waves"]) >= C.MAX_WAVES: s.msg = f"A level has at most {C.MAX_WAVES} waves."
        else:
            L["waves"].append([[C.ENEMY_KINDS[0], 2]])
            s.row = 5 + len(L["waves"]) - 1  # the cursor moves to the new wave (wave rows start at 5)

    def del_wave(s):
        if len(s.L["waves"]) > 1:
            s.L["waves"].pop()
            s.row = min(s.row, len(s.rows()) - 1)
        else: s.msg = "A level needs at least one wave."

    def add_level(s):
        if len(s.spec["levels"]) >= C.MAX_LEVELS: s.msg = f"A castle has at most {C.MAX_LEVELS} levels."
        else:
            s.spec["levels"].append(C.default_level(len(s.spec["levels"]) % 6))
            s.pick_level(len(s.spec["levels"]) - 1)

    def del_level(s):
        if len(s.spec["levels"]) > 1:
            s.spec["levels"].pop(s.li)
            s.pick_level(max(0, s.li - 1))
        else: s.msg = "A castle needs at least one level."

    # ------------------------------------------------------------ name typing
    def type(s, ch):
        if ch == "\b": s.spec["name"] = s.spec["name"][:-1]
        elif len(s.spec["name"]) < C.MAX_NAME: s.spec["name"] += ch

    # ------------------------------------------------------------ results
    def check(s, spec=None):
        return C.validate_castle(spec if spec is not None else s.spec)

    def save(s):
        """Save to castles/<name>.json. Returns True on success; otherwise msg says why."""
        errs = s.check()
        if errs:
            s.msg = "Cannot save: " + errs[0]
            return False
        try:
            s.path = C.save_castle(s.spec, C.CASTLE_DIR)
        except (OSError, ValueError) as e:
            s.msg = f"Cannot save: {e}"
            return False
        s.msg = f"Saved: {s.spec['name']}"
        return True

    def test_level(s):
        """The current level as a playable dict, or None (msg says why) if it is not valid on its own."""
        errs = s.check(dict(name=s.spec["name"], levels=[s.L]))
        if errs:
            s.msg = "Cannot test: " + errs[0]
            return None
        return C.build_level(s.L)


def preview_level(L, layout=None):
    """Preview dict from a castle-spec level (plats from its layout name) or from an already built level."""
    plats = L["plats"] if "plats" in L else C.LAYOUTS[layout or L.get("layout", "A")]
    return dict(theme=L["theme"], plats=plats, waves=L["waves"], boss=L.get("boss"))


def level_surface(P, t):
    """The preview picture at canvas size: the theme's background with the platforms, and the current wave's enemies and boss."""
    surf = get_bg(P["theme"], P["plats"]).copy()
    waves = [wv for wv in P["waves"] if wv] or [[]]
    k = int(t / WAVE_SECONDS) % len(waves)
    kinds = [kind for kind, n in waves[k] for _ in range(n)][:10]
    step = 300 / (len(kinds) - 1) if len(kinds) > 1 else 0
    for i, kind in enumerate(kinds):
        frames = ENEMY.get((kind, 0))
        if not frames: continue
        fr = pygame.transform.flip(frames[int(t * 6 + i) % len(frames)], True, False)  # sprites face right; enemies come from the right
        x = 60 + i * step if len(kinds) > 1 else 200
        y = FLOOR - 70 if ESTATS.get(kind, {}).get("fly") else FLOOR
        surf.blit(fr, (int(x - fr.get_width() / 2), int(y - fr.get_height() + 1)))
    if P.get("boss") in ENEMY:
        fr = pygame.transform.flip(ENEMY[(P["boss"], 0)][int(t * 4) % 4], True, False)
        surf.blit(fr, (int(W - 60 - fr.get_width() / 2), int(FLOOR - fr.get_height() + 1)))
    return surf, k, len(waves)


def thumb(surf):
    return pygame.transform.scale(surf, (PREV.w, PREV.h))


def _frame(rect):
    pygame.draw.rect(gfx.canvas, (30, 24, 44), rect)
    pygame.draw.rect(gfx.canvas, (96, 82, 130), rect, 1)


def _tag(x, y, s):
    """A small label on top of the preview picture."""
    w = font.size(s)[0] + 6
    pygame.draw.rect(gfx.canvas, INK, (x, y, w, 11))
    text(s, x + 3, y + 1, STEEL, font)


def _strip_colour(theme):
    return gfx.lerp(LEVELS[theme]["top"], (40, 30, 56), 0.35)


# ---------------------------------------------------------------- hit testing (mouse)
def tile_rect(i):
    return pygame.Rect(6 + i * TILE_STEP, STRIP_Y, TILE_W, TILE_H)


def row_rect(i, top):
    return pygame.Rect(PANEL.x + 2, ROW_Y + (i - top) * ROW_H - 1, PANEL.w - 4, ROW_H)


def editor_hit(ed, pos):
    """What a click at `pos` means: ('level', i), ('addlevel',), ('arrow', row, -1|1), ('row', row) or None."""
    n = len(ed.spec["levels"])
    for i in range(n):
        if tile_rect(i).collidepoint(pos): return ("level", i)
    if n < C.MAX_LEVELS and tile_rect(n).collidepoint(pos): return ("addlevel",)
    if PANEL.collidepoint(pos):
        rows = ed.rows()
        for i in range(ed.top, min(len(rows), ed.top + VISIBLE)):
            r = row_rect(i, ed.top)
            if not r.collidepoint(pos): continue
            if rows[i][0] in CHANGEABLE:
                if pygame.Rect(ARROW_L, r.y, 14, r.h).collidepoint(pos): return ("arrow", i, -1)
                if pygame.Rect(ARROW_R, r.y, 14, r.h).collidepoint(pos): return ("arrow", i, 1)
            return ("row", i)
    return None


def castle_hit(pos, n_castles):
    """Index of the castle-list row under `pos` (castles first, then NEW, then BACK), or None."""
    if not (6 <= pos[0] < 240) or pos[1] < LIST_Y - 3: return None
    i = (pos[1] - (LIST_Y - 3)) // LIST_STEP
    return i if i < n_castles + 2 else None


# ---------------------------------------------------------------- drawing
def _scroll(ed):
    rows = ed.rows()
    sel = min(ed.row, len(rows) - 1)
    if sel < ed.top: ed.top = sel
    if sel >= ed.top + VISIBLE: ed.top = sel - VISIBLE + 1
    ed.top = max(0, min(ed.top, max(0, len(rows) - VISIBLE)))


def draw_editor(ed, t=0.0):
    c = gfx.canvas
    c.fill((24, 18, 36))
    title_text("CASTLE MAKER", W // 2, 0, GOLD, 2)
    text(ed.spec["name"][:24] or "(unnamed)", W - 6, 4, STEEL, font, right=True)
    n = len(ed.spec["levels"])
    # level strip: one tile per level in its theme's colour, the selected one outlined
    for i, L in enumerate(ed.spec["levels"]):
        r = tile_rect(i)
        pygame.draw.rect(c, _strip_colour(L["theme"]), r)
        pygame.draw.rect(c, GOLD if i == ed.li else INK, r, 2 if i == ed.li else 1)
        text(str(i + 1), r.centerx, r.y + 3, WHITE if i == ed.li else STEEL, font, True)
    if n < C.MAX_LEVELS:
        r = tile_rect(n)
        pygame.draw.rect(c, (40, 34, 56), r); pygame.draw.rect(c, CYAN, r, 1)
        text("+", r.centerx, r.y + 3, CYAN, font, True)
    # rows panel
    _frame(PANEL)
    _scroll(ed)
    rows = ed.rows()
    sel = min(ed.row, len(rows) - 1)
    for i in range(ed.top, min(len(rows), ed.top + VISIBLE)):
        r, row = row_rect(i, ed.top), rows[i]
        on = i == sel
        if on: pygame.draw.rect(c, (70, 52, 22) if not ed.typing else (40, 90, 110), r)
        k = row[0]
        col = GOLD if on else (CYAN if k in ACTIONS else (STEEL if k.startswith(("add", "del")) else WHITE))
        text(("> " if on else "  ") + ed.label(row), PANEL.x + 6, r.y + 2, col, font)
        if k in CHANGEABLE:
            text("<", ARROW_L + 4, r.y + 2, GOLD if on else STEEL_D, font)
            text(">", ARROW_R + 4, r.y + 2, GOLD if on else STEEL_D, font)
    if len(rows) > VISIBLE:  # a scroll hint on the panel edge
        text("more" if ed.top + VISIBLE < len(rows) else "", PANEL.right - 4, PANEL.bottom - 10, STEEL_D, font, right=True)
    # preview
    L = ed.L
    surf, k, nw = level_surface(preview_level(L), t)
    c.blit(thumb(surf), PREV.topleft)
    pygame.draw.rect(c, GOLD, PREV, 1)
    _tag(PREV.x + 4, PREV.y + 4, f"PREVIEW  wave {k + 1}/{nw}" if any(L["waves"]) else "PREVIEW  (no waves)")
    # info (every line is wrapped to the box, so nothing runs off the edge)
    _frame(INFO)
    total = sum(cnt for wv in L["waves"] for _, cnt in wv)
    tier = C.tier_for(ed.li, len(ed.spec["levels"]))
    take, deal = difficulty(tier)
    lines = [(f"{THEME_NAMES[L['theme']]}, platforms {L.get('layout', 'A')}, {total} foes", WHITE),
             (f"Boss: {boss_name(L.get('boss'))}", GOLD if L.get("boss") else STEEL),
             (f"Tier {tier}: foes take x{take:.2f}, deal x{deal:.2f}", (255, 150, 70))]
    for j, (ln, col) in enumerate(lines): text(fit_lines(ln, INFO.w - 10, 1)[0], INFO.x + 5, INFO.y + 4 + j * 13, col, font)
    where = ed.path.split("/")[-1] if ed.path else "not saved yet"
    text(fit_lines(f"Level {ed.li + 1} of {n}  |  {where}", INFO.w - 10, 1)[0], INFO.x + 5, INFO.y + 44, STEEL, font)
    # messages and keys
    if ed.msg: text(ed.msg[:72], W // 2, MSG_Y, RED if ed.msg.startswith("Cannot") else GOLD, font, True)
    hint = "Type the name.  Enter: done" if ed.typing else "Click or W/S: pick   A/D or < >: change   Enter: act   Esc: castles"
    text(hint, W // 2, HINT_Y, STEEL, font, True)


def draw_castles(entries, sel, msg, t=0.0, spec=None, errs=()):
    """entries: (name, n_levels, errors) per saved castle. spec / errs: the selected castle, for the preview."""
    c = gfx.canvas
    c.fill((24, 18, 36))
    title_text("CASTLE MAKER", W // 2, 0, GOLD, 2)
    _frame(pygame.Rect(6, 26, 232, 216))
    y = LIST_Y
    rows = [(n, k, e) for n, k, e in entries] + [("+ NEW CASTLE", None, []), ("BACK", None, [])]
    for i, (name, k, e) in enumerate(rows):
        on = i == sel
        if on: pygame.draw.rect(c, (70, 52, 22), (8, y - 3, 228, LIST_STEP - 1))
        col = RED if e else (GOLD if on else (CYAN if k is None else WHITE))
        label = name if k is None else f"{name[:22]}  {k} lvl{'s' if k != 1 else ''}" + ("  INVALID" if e else "")
        text(("> " if on else "  ") + label, 12, y, col, font)
        y += LIST_STEP
    # preview of the selected castle: its first level
    if sel < len(entries) and spec is not None and not errs:
        L = build_level(spec["levels"][0])
        surf, k, nw = level_surface(preview_level(L, spec["levels"][0].get("layout", "A")), t)
        c.blit(thumb(surf), PREV.topleft)
        pygame.draw.rect(c, GOLD, PREV, 1)
        _frame(INFO)
        bosses = [boss_name(lv.get("boss")).split()[-1] for lv in spec["levels"] if lv.get("boss")]  # short: "Gravekeeper", "Beastlord"...
        text(fit_lines(f"{spec['name']}: {len(spec['levels'])} level{'s' if len(spec['levels']) != 1 else ''}", INFO.w - 10, 1)[0], INFO.x + 5, INFO.y + 4, WHITE, font)
        text(fit_lines(f"First level: {THEME_NAMES[L['theme']]} theme", INFO.w - 10, 1)[0], INFO.x + 5, INFO.y + 18, STEEL, font)
        text(fit_lines(("Bosses: " + ", ".join(bosses)) if bosses else "No bosses in this castle", INFO.w - 10, 1)[0], INFO.x + 5, INFO.y + 32, GOLD, font)
    elif sel < len(entries) and errs:
        _frame(INFO)
        text("This castle has errors:", INFO.x + 5, INFO.y + 4, RED, font)
        text(fit_lines(errs[0], INFO.w - 10, 1)[0], INFO.x + 5, INFO.y + 18, WHITE, font)
        text(fit_lines("Fix the file, or start a NEW castle.", INFO.w - 10, 1)[0], INFO.x + 5, INFO.y + 32, STEEL, font)
    else:
        _frame(PREV)
        text("Build a castle from 1 to 10 levels.", PREV.centerx, PREV.centery - 10, WHITE, font, True)
        text("Themes, platforms, bosses and waves.", PREV.centerx, PREV.centery + 4, STEEL, font, True)
    if msg: text(msg[:72], W // 2, MSG_Y, RED if msg.startswith(("Cannot", "This")) else GOLD, font, True)
    text("Click or W/S: pick   Enter: play   E: edit   Esc: back", W // 2, HINT_Y, STEEL, font, True)
