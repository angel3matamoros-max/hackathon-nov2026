"""Screens and the main loop."""
import sys
import pygame
from . import gfx, sound
from .config import *
from .gfx import text, title_text, wrap, use, main_cv, VIGNETTE, blit_ent, font, mid, big
from .classes import CLASS_NAMES, CLASSES
from .sprites import HERO
from .items import SLOTS, SLOT_NAMES, tier_color
from .levels import LEVELS, NUM_LEVELS, get_bg, draw_torches
from .inputs import make_motions
from .player import Player
from .arena import Arena, SKIP_RECT, SKIP_STATE
from .cutscenes import IntroCard, AscendCutscene, Ending
from .devmode import Dev
from .ally import Ally, AllyMotion, COMPLEMENT
from .castle import list_castles, load_castle, castle_levels, tier_for
from .maker import Editor, draw_editor, draw_castles, editor_hit, castle_hit

screen, FAST = None, True
clock = pygame.time.Clock()


def init_display():
    global screen, FAST
    try:
        screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        FAST = True
    except Exception:
        screen = pygame.display.set_mode((W * 3, H * 3))
        FAST = False
    pygame.display.set_caption("Rogue Loot")


def present():
    if FAST: screen.blit(main_cv, (0, 0))
    else: pygame.transform.scale(main_cv, screen.get_size(), screen)
    pygame.display.flip()


def hint(keyboard, pad):
    """Footer text: button glyphs while a PS2 pad is the controller in use (player 1), keyboard keys otherwise."""
    return pad if (PAD[0] and PAD[0].get("_name") == "PS2") else keyboard


def draw_menu(sel, t, items=("START", "TUTORIAL", "SETTINGS", "EXIT")):
    gfx.canvas.blit(get_bg(0), (0, 0)); draw_torches(t)
    gfx.canvas.blit(VIGNETTE, (0, 0))
    title_text("ROGUE LOOT", W // 2, 22, GOLD)
    text("2-PLAYER CO-OP ADVENTURE", W // 2, 76, STEEL, font, True)
    for i, it in enumerate(items):
        text(f"> {it} <" if i == sel else it, W // 2, 104 + i * 22, GOLD if i == sel else WHITE, mid, True)
    for k, cls in enumerate(("Knight", "Mage")):
        blit_ent(HERO[cls][1][int(t * 10) % 8], (t * 40 + k * 120) % (W + 60) - 30, FLOOR)
    text(hint("W/S or Up/Down: move    Enter/Space: select" + ("" if SET["tutorial_done"] else "    (First launch runs Tutorial)"), "{up} {down} Move    {cross} Select    {start} Start" + ("" if SET["tutorial_done"] else "    (First launch runs Tutorial)")), W // 2, 252, STEEL, font, True)


def draw_players(sel, t):
    gfx.canvas.blit(get_bg(0), (0, 0)); draw_torches(t)
    gfx.canvas.blit(VIGNETTE, (0, 0))
    title_text("HOW MANY PLAYERS?", W // 2, 20, GOLD, 2)
    opts = [("1 PLAYER", "You + a CPU ally fighting at your side", 1), ("2 PLAYERS", "Local co-op: two heroes, two keyboards", 2)]
    for i, (name, sub, n) in enumerate(opts):
        cx = 130 + i * 220
        on = i == sel
        pygame.draw.rect(gfx.canvas, INK, (cx - 92, 78, 184, 110)); pygame.draw.rect(gfx.canvas, GOLD if on else STEEL_D, (cx - 92, 78, 184, 110), 2 if on else 1)
        text(f"> {name} <" if on else name, cx, 86, GOLD if on else WHITE, mid, True)
        for k in range(n):
            blit_ent(HERO[("Knight", "Mage")[k]][1][int(t * 10) % 8], cx + (k - (n - 1) / 2) * 34, 150)
        for k, ln in enumerate(wrap(sub, 28)): text(ln, cx, 160 + k * 11, STEEL, font, True)
    text(hint("A/D or Left/Right: choose    Enter/Space: confirm    Esc: back", "{left} {right} Choose    {cross} Confirm    {circle} Back"), W // 2, 252, STEEL, font, True)


def draw_select(sel, ready, t, solo=False):
    gfx.canvas.fill((24, 18, 36))
    title_text("CHOOSE YOUR CLASS", W // 2, 4, GOLD, 2)
    pygame.draw.rect(gfx.canvas, (70, 60, 100), (W // 2 - 1, 28, 2, H - 30))
    for p in range(2):
        cx, name = 120 + p * 240, CLASS_NAMES[sel[p]]
        d = CLASSES[name]
        text(("CPU ALLY" if (solo and p) else f"P{p + 1}") + f" - {d['role']}", cx, 28, P_COL[p], font, True)
        pygame.draw.ellipse(gfx.canvas, (12, 8, 20), (cx - 16, 82, 32, 6))
        gfx.canvas.blit(pygame.transform.scale(HERO[name][1][int(t * 10) % 8], (48, 52)), (cx - 24, 34))
        if not ready[p]:
            text("<", cx - 54, 52, WHITE, big); text(">", cx + 42, 52, WHITE, big)
        text(f"{name.upper()}  (HP {d['hp']} / ATK {d['atk']} / DEF {d['df']})", cx, 90, WHITE, font, True)
        y = 104
        text(f"[{kn(p, 'cast')}] SKILL 1: {d['skill']} ({d['cd']}s)", cx, y, CYAN, font, True); y += 12
        for ln in wrap(d["sdesc"], 35): text(ln, cx, y, WHITE, font, True); y += 11
        text(f"[{kn(p, 'cast2')}] SKILL 2: {d['skill2']} ({d['cd2']}s)", cx, y + 2, GOLD, font, True); y += 14
        for ln in wrap(d["s2desc"], 35): text(ln, cx, y, WHITE, font, True); y += 11
        for ln in wrap(d["pdesc"], 35): text(ln, cx, y + 2, GREEN, font, True); y += 11
        if ready[p]: text("READY!", cx, 246, GREEN, mid, True)
        elif solo and p: text(f"P1 picks the ally: [{kn(0, 'left')}]/[{kn(0, 'right')}]  Ready [{kn(0, 'slash')}]", cx, 250, P_COL[p], font, True)
        else: text(f"Swap: [{kn(p, 'left')}]/[{kn(p, 'right')}]   Ready: [{kn(p, 'slash')}]", cx, 250, P_COL[p], font, True)


def draw_settings(s_tab, s_row, listening):
    n = len(ACTIONS) + 2
    gfx.canvas.fill((24, 18, 36))
    title_text("KEY BINDINGS", W // 2, 6, GOLD, 2)
    for i in range(2):
        text(f"PLAYER {i + 1}", 150 + i * 180, 36, P_COL[i] if s_tab == i else STEEL_D, mid, True)
    pygame.draw.rect(gfx.canvas, P_COL[s_tab], (90 + s_tab * 180, 54, 120, 2))
    for r in range(n):
        y, sel_row = 62 + r * 15, r == s_row
        if r < len(ACTIONS):
            val = "press a key..." if (listening and sel_row) else kn(s_tab, ACTIONS[r])
            text(LABEL[ACTIONS[r]], 100, y, GOLD if sel_row else WHITE)
            text(val, 380, y, CYAN if listening and sel_row else (GOLD if sel_row else STEEL), font, right=True)
        else:
            text("RESET TO DEFAULTS" if r == len(ACTIONS) else "BACK", W // 2, y + 4, GOLD if sel_row else WHITE, font, True)
    text(hint("W/S: move   A/D or Left/Right: switch player   Enter: rebind   Esc: back", "{up} {down} Move    {left} {right} Player    {cross} Rebind    {circle} Back"), W // 2, 253, STEEL, font, True)


def draw_victory(heroes, inv, gear):
    gfx.canvas.fill((24, 18, 36))
    title_text("VICTORY!", W // 2, 8, GOLD)
    for p in range(2):
        cx = 120 + p * 240
        text(f"P{p + 1} {heroes[p]} - {len(inv[p])} items found", cx, 56, P_COL[p], mid, True)
        y = 76
        for sl in SLOTS:
            it = gear[p].get(sl)
            text(f"{SLOT_NAMES[sl]}: {it['name'][:26]}" if it else f"{SLOT_NAMES[sl]}: -", cx, y, tier_color(it) if it else STEEL_D, font, True)
            if it:
                for ln in wrap(it["desc"], 40)[:2]: y += 11; text(ln, cx, y, WHITE, font, True)
            y += 16
    text(hint("Press Enter for the main menu", "Press {cross} or {start} for the main menu"), W // 2, 252, STEEL, font, True)


class Game:
    """All game state + one step() per frame. main() drives it with real events; tests drive it with synthetic ones."""

    def __init__(s, dev=False, motions=None):
        s.keys = list(motions or make_motions())  # auto: the hand controller if one is plugged in  # the real input objects (keyboard now, a controller later)
        s.solo, s.ally = SET.get("solo", False), Ally()
        s.motions = list(s.keys)
        s.set_solo(s.solo)
        s.mode, s.msel, s.t, s.quit = "menu", 0, 0.0, False
        s.arena, s.area, s.inv, s.gear, s.heroes, s.first_run = None, 0, [[], []], [{}, {}], ["Knight", "Tank"], False
        s.sel, s.ready, s.sel_t = [0, 1], [False, False], 0.0
        s.s_tab, s.s_row, s.listening, s.dsel, s.psel = 0, 0, False, 0, 0
        s.cuts, s.after, s.tier_override = [], None, None
        s.custom, s.test_back, s.ed, s.csel, s.cmsg, s.events = None, None, None, 0, "", []
        s.cpath, s.cspec, s.cerrs = None, None, []  # castle list: the selected castle's preview  # castle maker: custom = list of level dicts being played
        s.dev = Dev() if dev else None
        s.dt = 1 / 60

    # ---------------------------------------------------------------- helpers
    def set_solo(s, solo):
        """Solo: player 2's Motion is the CPU ally's. Two players: both are real inputs."""
        s.solo = solo
        s.motions[1] = AllyMotion(1) if solo else s.keys[1]
        SET["solo"] = solo

    def menu_items(s):
        return ["START", "TUTORIAL", "CASTLE MAKER", "SETTINGS"] + (["DEV: LEVEL SELECT"] if s.dev else []) + ["EXIT"]

    def new_arena(s, level, **kw):
        ps = [Player(0, s.heroes[0], 80), Player(1, s.heroes[1], 110)]
        ps[1].cpu = s.solo
        if s.custom is not None:  # a castle-maker level: its theme drives the look, its tier the difficulty
            L = s.custom[level]
            return Arena(L["theme"], ps, gear=s.gear, level=L, tier=tier_for(level, len(s.custom)), label=f"LEVEL {level + 1}/{len(s.custom)}: {L['name']}", **kw)
        return Arena(level, ps, gear=s.gear, tier=s.tier_override, **kw)

    def begin_custom(s):
        s.area = 0
        s.arena, s.mode = s.new_arena(0), "game"

    def play_castle(s, spec):
        s.custom, s.test_back = castle_levels(spec), None
        s.mode, s.sel, s.ready = "select", [0, 1], [False, False]

    def start_arena(s, level):
        s.area, s.arena, s.mode = level, s.new_arena(level), "game"

    def play(s, cuts, after):
        s.cuts, s.after, s.mode = cuts, after, "cutscene"

    def start_tutorial(s, first_run):
        s.mode, s.first_run, s.arena = "game", first_run, Arena(0, [Player(0, "Knight", 80)], True)

    def finish_tutorial(s, skipped=False):
        if skipped:  # skipping counts as done, so the first-launch tutorial never nags again
            SET["tutorial_done"] = True
            save_settings()
        s.mode = "select" if s.first_run else "menu"
        s.sel, s.ready, s.first_run = [0, 1], [False, False], False

    def warp(s, level, gallery=False):
        """Dev: jump straight into a level (no cutscene)."""
        s.area, s.custom = level, None
        s.arena = s.new_arena(level, gallery=gallery)
        if gallery: s.arena.spawn("dummy", 300)
        s.mode = "game"

    def advance(s):
        a = s.arena
        for p in range(2): s.inv[p].extend(a.pending[p])
        s.gear = [dict(p.gear) for p in a.players]
        if s.custom is not None:  # castles play straight through (no cutscenes): next level, or the end
            s.area += 1
            if s.area < len(s.custom): s.arena = s.new_arena(s.area); return
            s.custom = None
            s.mode, s.test_back = s.test_back or "victory", None
            return
        frm, s.area = s.area, s.area + 1
        if s.area >= NUM_LEVELS:
            s.play([Ending(s.heroes)], lambda: setattr(s, "mode", "victory"))
        else:
            lvl = s.area
            s.play([AscendCutscene(frm, lvl, s.heroes), IntroCard(lvl)], lambda: s.start_arena(lvl))

    # ---------------------------------------------------------------- frame
    def step(s, dt, events):
        s.dt = dt
        s.t += dt
        s.events = events
        keys = [e.key for e in events if e.type == pygame.KEYDOWN]
        clicks = [e.pos if FAST else (e.pos[0] // 3, e.pos[1] // 3) for e in events if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1]
        if any(e.type == pygame.QUIT for e in events): s.quit = True
        for m in s.motions: m.update(events, dt)
        if s.mode != "game" and not (s.mode == "settings" and s.listening):  # the hand controller also drives the menus
            keys = keys + [k for m in s.motions for k in getattr(m, "menu_keys", lambda: [])()]
        if s.solo and s.mode == "game" and s.arena and not s.arena.tut: s.ally.tick(s.arena, s.motions[1], dt)
        use(main_cv)
        up = any(k in (pygame.K_UP, pygame.K_w) for k in keys)
        dn = any(k in (pygame.K_DOWN, pygame.K_s) for k in keys)
        ok = any(k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER) for k in keys)
        back = pygame.K_ESCAPE in keys
        if up or dn: sound.play("menu")
        if ok: sound.play("select")
        if s.mode == "game": sound.music("battle")
        elif s.mode in ("menu", "devmenu", "settings", "players", "select", "castles", "maker"): sound.music("menu")
        getattr(s, "mode_" + s.mode)(dt, keys, up, dn, ok, back, clicks)
        if s.dev and s.mode == "game" and s.arena:
            s.dev.handle(s, keys)
            s.dev.overlay(s, dt)

    def mode_menu(s, dt, keys, up, dn, ok, back, clicks):
        items = s.menu_items()
        s.msel = (s.msel + dn - up) % len(items)
        if ok:
            it = items[s.msel]
            s.custom = None
            if it == "START":
                if SET["tutorial_done"]: s.mode, s.psel = "players", (0 if SET["solo"] else 1)
                else: s.start_tutorial(True)
            elif it == "TUTORIAL": s.start_tutorial(False)
            elif it == "CASTLE MAKER": s.mode, s.csel, s.cmsg = "castles", 0, ""
            elif it == "SETTINGS": s.mode, s.s_tab, s.s_row, s.listening = "settings", 0, 0, False
            elif it.startswith("DEV"): s.mode, s.dsel = "devmenu", 0
            else: s.quit = True
        draw_menu(s.msel, s.t, items)

    DEV_ROWS = [(f"Level {i + 1}: {LEVELS[i]['name']}", ("warp", i)) for i in range(NUM_LEVELS)] + [
        ("Enemy gallery (Y spawns each enemy)", ("gallery", 0)), ("Preview: level intro card", ("cut", 0)),
        ("Preview: ascend cutscene", ("cut", 1)), ("Preview: ending", ("cut", 2)), ("Back", ("back", 0))]

    def mode_devmenu(s, dt, keys, up, dn, ok, back, clicks):
        n = len(s.DEV_ROWS)
        s.dsel = (s.dsel + dn - up) % n
        if back: s.mode = "menu"
        if ok:
            kind, v = s.DEV_ROWS[s.dsel][1]
            if kind == "warp": s.warp(v)
            elif kind == "gallery": s.warp(0, gallery=True)
            elif kind == "back": s.mode = "menu"
            else:
                cuts = [[IntroCard(0)], [AscendCutscene(0, 1, s.heroes)], [Ending(s.heroes)]][v]
                s.play(cuts, lambda: setattr(s, "mode", "devmenu"))
        gfx.canvas.fill((24, 18, 36))
        title_text("DEV: LEVEL SELECT", W // 2, 6, (120, 255, 150), 2)
        for i, (lab, _) in enumerate(s.DEV_ROWS):
            text(f"> {lab} <" if i == s.dsel else lab, W // 2, 50 + i * 17, GOLD if i == s.dsel else WHITE, mid, True)
        text("W/S: move   Enter: go   Esc: back      (in-level: F1 shows dev keys)", W // 2, 253, STEEL, font, True)

    def mode_settings(s, dt, keys, up, dn, ok, back, clicks):
        n = len(ACTIONS) + 2
        if s.listening:
            for k in keys:
                if k == pygame.K_ESCAPE: s.listening = False
                else:
                    kb, act = SET["keys"][s.s_tab], ACTIONS[s.s_row]
                    for a2 in ACTIONS:
                        if a2 != act and kb[a2] == k: kb[a2] = kb[act]
                    kb[act] = k; save_settings(); s.listening = False
                    break
        else:
            s.s_row = (s.s_row + dn - up) % n
            if any(k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB, pygame.K_a, pygame.K_d) for k in keys): s.s_tab = 1 - s.s_tab
            if back: s.mode = "menu"
            if ok:
                if s.s_row < len(ACTIONS): s.listening = True
                elif s.s_row == len(ACTIONS): SET["keys"] = [dict(k) for k in DEFAULT_KEYS]; save_settings()
                else: s.mode = "menu"
        draw_settings(s.s_tab, s.s_row, s.listening)

    def mode_players(s, dt, keys, up, dn, ok, back, clicks):
        if any(k in (pygame.K_LEFT, pygame.K_a) for k in keys): s.psel = 0
        if any(k in (pygame.K_RIGHT, pygame.K_d) for k in keys): s.psel = 1
        if up or dn: s.psel = 1 - s.psel
        if back: s.mode = "menu"
        if ok:
            s.set_solo(s.psel == 0); save_settings()
            s.mode, s.sel, s.ready = "select", [0, 1], [False, False]
        draw_players(s.psel, s.t)

    def mode_select(s, dt, keys, up, dn, ok, back, clicks):
        s.sel_t += dt
        fresh = False  # P1 just readied this frame (solo): the same key press must not also ready the CPU
        for p in range(2):
            cpu = s.solo and p == 1
            m = s.motions[0] if cpu else s.motions[p]  # in solo, player 1's keys also choose the ally's class (once P1 is ready)
            if cpu and (not s.ready[0] or fresh): continue
            if s.solo and p == 0 and s.ready[0]: continue  # P1 is locked in; their keys now choose the ally
            if not s.ready[p] and m.swing in ("left", "right"): s.sel[p] = (s.sel[p] + (1 if m.swing == "right" else -1)) % len(CLASS_NAMES)
            if m.slash_p:
                s.ready[p] = not s.ready[p]
                if s.solo and p == 0 and s.ready[0]:
                    s.sel[1], s.ready[1], fresh = CLASS_NAMES.index(COMPLEMENT[CLASS_NAMES[s.sel[0]]]), False, True  # sensible default ally
        if back: s.mode = "menu"
        draw_select(s.sel, s.ready, s.sel_t, s.solo)
        if all(s.ready):
            s.heroes, s.inv, s.gear, s.area = [CLASS_NAMES[i] for i in s.sel], [[], []], [{}, {}], 0
            if s.custom is not None: s.begin_custom()
            else: s.play([IntroCard(0)], lambda: s.start_arena(0))

    def mode_cutscene(s, dt, keys, up, dn, ok, back, clicks):
        c = s.cuts[0]
        c.update(dt, s.motions)
        c.draw()
        if back or any(m.skip_p for m in s.motions) or (c.t > 0.5 and any(m.slash_p for m in s.motions)): c.skip()
        if c.done:
            s.cuts.pop(0)
            if not s.cuts: s.after()

    def mode_game(s, dt, keys, up, dn, ok, back, clicks):
        a = s.arena
        if a.tut:
            pos = pygame.mouse.get_pos()
            SKIP_STATE["hot"] = SKIP_RECT.collidepoint(pos if FAST else (pos[0] // 3, pos[1] // 3))
        a.update(dt, s.motions)
        a.draw()
        if back: s.mode = "menu"
        r = a.result
        if a.tut and (s.motions[0].skip_p or any(SKIP_RECT.collidepoint(c) for c in clicks)):
            s.finish_tutorial(skipped=True)
        elif r == "menu": s.finish_tutorial()
        elif r == "retry": s.arena = s.new_arena(s.area)
        elif r == "next": s.advance()

    def mode_castles(s, dt, keys, up, dn, ok, back, clicks):
        rows = list_castles()
        for pos in clicks:  # a click selects a row; clicking the selected row plays / edits it
            h = castle_hit(pos, len(rows))
            if h is None: continue
            if h == s.csel: ok = True
            s.csel = h
        sel = s.csel = (s.csel + dn - up) % (len(rows) + 2)
        if back: s.mode = "menu"
        if pygame.K_e in keys and sel < len(rows):  # E = edit the selected castle
            spec, errs = load_castle(rows[sel][0])
            if errs: s.cmsg = "Cannot edit: " + errs[0]
            else: s.ed, s.mode, s.cmsg = Editor(spec, rows[sel][0]), "maker", ""
        if ok:
            if sel < len(rows):
                spec, errs = load_castle(rows[sel][0])
                if errs: s.cmsg = "Cannot play: " + errs[0]
                else: s.play_castle(spec)
            elif sel == len(rows): s.ed, s.mode, s.cmsg = Editor(), "maker", ""
            else: s.mode = "menu"
        spec = errs = None
        if sel < len(rows):
            if s.cpath != rows[sel][0]: s.cpath, s.cspec, s.cerrs = rows[sel][0], *load_castle(rows[sel][0])
            spec, errs = s.cspec, s.cerrs
        draw_castles([(r[1], r[2], r[3]) for r in rows], sel, s.cmsg, s.t, spec, errs or ())

    def _maker_do(s, act):
        """Run an editor action: 'save', 'play', 'test' or 'back' (None does nothing)."""
        ed = s.ed
        if act == "save": ed.save()
        elif act == "play":
            if ed.save(): s.play_castle(ed.spec)
        elif act == "test":
            lvl = ed.test_level()
            if lvl:
                s.custom, s.test_back, s.gear, s.inv = [lvl], "maker", [{}, {}], [[], []]
                s.begin_custom()
        elif act == "back": s.mode, s.cmsg = "castles", ""

    def mode_maker(s, dt, keys, up, dn, ok, back, clicks):
        ed = s.ed
        if ed.typing:  # the name: letters come from TEXTINPUT; Enter, Esc or a click finish
            for e in s.events:
                if e.type == pygame.TEXTINPUT: ed.type(e.text)
            if pygame.K_BACKSPACE in keys: ed.type("\b")
            if back or clicks or any(k in (pygame.K_RETURN, pygame.K_KP_ENTER) for k in keys): ed.typing, ed.msg = False, ""
        else:
            if any(k in (pygame.K_LEFT, pygame.K_a) for k in keys): ed.change(-1)
            if any(k in (pygame.K_RIGHT, pygame.K_d) for k in keys): ed.change(1)
            if up or dn: ed.move(dn - up)
            for pos in clicks:
                h = editor_hit(ed, pos)
                if h is None: continue
                if h[0] == "level": ed.pick_level(h[1])
                elif h[0] == "addlevel": ed.add_level()
                elif h[0] == "arrow": ed.row = h[1]; ed.change(h[2])
                elif h[0] == "row":
                    if h[1] == ed.row: s._maker_do(ed.act())
                    else: ed.row = h[1]
            if back: s.mode, s.cmsg = "castles", ""
            elif ok: s._maker_do(ed.act())
        draw_editor(ed, s.t)

    def mode_victory(s, dt, keys, up, dn, ok, back, clicks):
        draw_victory(s.heroes, s.inv, s.gear)
        if ok: s.mode = "menu"


def main(dev=False, level=None, gallery=False):
    init_display()
    g = Game(dev=dev or level is not None or gallery)
    if level is not None: g.warp(max(0, min(NUM_LEVELS - 1, level - 1)))
    elif gallery: g.warp(0, gallery=True)
    while not g.quit:
        dt = min(clock.tick(60) / 1000, 0.05)
        g.step(dt, pygame.event.get())
        present()
    pygame.quit()
    sys.exit()
