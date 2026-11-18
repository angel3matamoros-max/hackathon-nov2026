"""Screens and the main loop."""
import sys
import pygame
from . import gfx
from .config import *
from .gfx import text, title_text, wrap, use, main_cv, VIGNETTE, blit_ent, font, mid, big
from .classes import CLASS_NAMES, CLASSES
from .sprites import HERO
from .levels import LEVELS, NUM_LEVELS, get_bg, draw_torches
from .inputs import make_motions
from .player import Player
from .arena import Arena, SKIP_RECT, SKIP_STATE
from .cutscenes import IntroCard, AscendCutscene, Ending
from .devmode import Dev

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


def draw_menu(sel, t, items=("START", "TUTORIAL", "SETTINGS", "EXIT")):
    gfx.canvas.blit(get_bg(0), (0, 0)); draw_torches(t)
    gfx.canvas.blit(VIGNETTE, (0, 0))
    title_text("ROGUE LOOT", W // 2, 22, GOLD)
    text("2-PLAYER CO-OP ADVENTURE", W // 2, 76, STEEL, font, True)
    for i, it in enumerate(items):
        text(f"> {it} <" if i == sel else it, W // 2, 104 + i * 22, GOLD if i == sel else WHITE, mid, True)
    for k, cls in enumerate(("Knight", "Mage")):
        blit_ent(HERO[cls][1][int(t * 10) % 8], (t * 40 + k * 120) % (W + 60) - 30, FLOOR)
    text("W/S or Up/Down: move    Enter/Space: select" + ("" if SET["tutorial_done"] else "    (First launch runs Tutorial)"), W // 2, 252, STEEL, font, True)


def draw_select(sel, ready, t):
    gfx.canvas.fill((24, 18, 36))
    title_text("CHOOSE YOUR CLASS", W // 2, 4, GOLD, 2)
    pygame.draw.rect(gfx.canvas, (70, 60, 100), (W // 2 - 1, 28, 2, H - 30))
    for p in range(2):
        cx, name = 120 + p * 240, CLASS_NAMES[sel[p]]
        d = CLASSES[name]
        text(f"P{p + 1} - {d['role']}", cx, 28, P_COL[p], font, True)
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
    text("W/S: move   A/D or Left/Right: switch player   Enter: rebind   Esc: back", W // 2, 253, STEEL, font, True)


def draw_victory(heroes, inv, gear):
    gfx.canvas.fill((24, 18, 36))
    title_text("VICTORY!", W // 2, 8, GOLD)
    for p in range(2):
        cx = 120 + p * 240
        text(f"P{p + 1} {heroes[p]} - {len(inv[p])} items", cx, 60, P_COL[p], mid, True)
        w = gear[p]
        if w: text(w["name"] + (" (cursed)" if w["cursed"] else ""), cx, 74, (190, 100, 240) if w["cursed"] else GOLD, font, True)
        for k, it in enumerate(sorted(inv[p], key=lambda i: -i["tier"])[:12]):
            text(it["name"][:32], cx, 90 + k * 13, RARITY[it["tier"]][1], font, True)
    text("Press Enter for the main menu", W // 2, 252, STEEL, font, True)


class Game:
    """All game state + one step() per frame. main() drives it with real events; tests drive it with synthetic ones."""

    def __init__(s, dev=False, motions=None):
        s.motions = motions or make_motions()
        s.mode, s.msel, s.t, s.quit = "menu", 0, 0.0, False
        s.arena, s.area, s.inv, s.gear, s.heroes, s.first_run = None, 0, [[], []], [None, None], ["Knight", "Tank"], False
        s.sel, s.ready, s.sel_t = [0, 1], [False, False], 0.0
        s.s_tab, s.s_row, s.listening, s.dsel = 0, 0, False, 0
        s.cuts, s.after, s.tier_override = [], None, None
        s.dev = Dev() if dev else None
        s.dt = 1 / 60

    # ---------------------------------------------------------------- helpers
    def menu_items(s):
        return ["START", "TUTORIAL", "SETTINGS"] + (["DEV: LEVEL SELECT"] if s.dev else []) + ["EXIT"]

    def new_arena(s, level, **kw):
        return Arena(level, [Player(0, s.heroes[0], 80), Player(1, s.heroes[1], 110)], gear=s.gear, tier=s.tier_override, **kw)

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
        s.area = level
        s.arena = s.new_arena(level, gallery=gallery)
        if gallery: s.arena.spawn("dummy", 300)
        s.mode = "game"

    def advance(s):
        a = s.arena
        for p in range(2): s.inv[p].extend(a.pending[p])
        s.gear = [p.weapon for p in a.players]
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
        keys = [e.key for e in events if e.type == pygame.KEYDOWN]
        clicks = [e.pos if FAST else (e.pos[0] // 3, e.pos[1] // 3) for e in events if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1]
        if any(e.type == pygame.QUIT for e in events): s.quit = True
        for m in s.motions: m.update(events, dt)
        use(main_cv)
        up = any(k in (pygame.K_UP, pygame.K_w) for k in keys)
        dn = any(k in (pygame.K_DOWN, pygame.K_s) for k in keys)
        ok = any(k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER) for k in keys)
        back = pygame.K_ESCAPE in keys
        getattr(s, "mode_" + s.mode)(dt, keys, up, dn, ok, back, clicks)
        if s.dev and s.mode == "game" and s.arena:
            s.dev.handle(s, keys)
            s.dev.overlay(s, dt)

    def mode_menu(s, dt, keys, up, dn, ok, back, clicks):
        items = s.menu_items()
        s.msel = (s.msel + dn - up) % len(items)
        if ok:
            it = items[s.msel]
            if it == "START":
                if SET["tutorial_done"]: s.mode, s.sel, s.ready = "select", [0, 1], [False, False]
                else: s.start_tutorial(True)
            elif it == "TUTORIAL": s.start_tutorial(False)
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

    def mode_select(s, dt, keys, up, dn, ok, back, clicks):
        s.sel_t += dt
        for p, m in enumerate(s.motions):
            if not s.ready[p] and m.swing in ("left", "right"): s.sel[p] = (s.sel[p] + (1 if m.swing == "right" else -1)) % len(CLASS_NAMES)
            if m.slash_p: s.ready[p] = not s.ready[p]
        if back: s.mode = "menu"
        draw_select(s.sel, s.ready, s.sel_t)
        if all(s.ready):
            s.heroes, s.inv, s.gear, s.area = [CLASS_NAMES[i] for i in s.sel], [[], []], [None, None], 0
            s.play([IntroCard(0)], lambda: s.start_arena(0))

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
