"""Screens and the main loop."""
import sys
import pygame
from . import gfx
from .config import *
from .gfx import text, title_text, wrap, use, main_cv, VIGNETTE, blit_ent, font, mid, big
from .classes import CLASS_NAMES, CLASSES
from .sprites import HERO
from .levels import AREAS, get_bg, draw_torches
from .inputs import Motion
from .player import Player
from .arena import Arena

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


def draw_menu(sel, t):
    gfx.canvas.blit(get_bg(0), (0, 0)); draw_torches(t)
    gfx.canvas.blit(VIGNETTE, (0, 0))
    title_text("ROGUE LOOT", W // 2, 22, GOLD)
    text("2-PLAYER CO-OP ADVENTURE", W // 2, 76, STEEL, font, True)
    for i, it in enumerate(("START", "TUTORIAL", "SETTINGS", "EXIT")):
        text(f"> {it} <" if i == sel else it, W // 2, 104 + i * 24, GOLD if i == sel else WHITE, mid, True)
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


def main():
    init_display()
    motions = [Motion(0), Motion(1)]
    mode, msel, t = "menu", 0, 0.0
    arena, area, inv, heroes, first_run = None, 0, [[], []], ["Knight", "Tank"], False
    sel, ready, sel_t = [0, 1], [False, False], 0.0
    s_tab, s_row, listening = 0, 0, False

    def new_arena(a):
        return Arena(a, [Player(0, heroes[0], 80), Player(1, heroes[1], 110)])

    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        t += dt
        events = pygame.event.get()
        keys = [e.key for e in events if e.type == pygame.KEYDOWN]
        for e in events:
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        for m in motions: m.update(events, dt)
        use(main_cv)
        up = any(k in (pygame.K_UP, pygame.K_w) for k in keys)
        dn = any(k in (pygame.K_DOWN, pygame.K_s) for k in keys)
        ok = any(k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER) for k in keys)
        back = pygame.K_ESCAPE in keys

        if mode == "menu":
            msel = (msel + dn - up) % 4
            if ok:
                if msel == 0:
                    if SET["tutorial_done"]: mode, sel, ready = "select", [0, 1], [False, False]
                    else: mode, first_run, arena = "tutorial", True, Arena(0, [Player(0, "Knight", 80)], True)
                elif msel == 1: mode, first_run, arena = "tutorial", False, Arena(0, [Player(0, "Knight", 80)], True)
                elif msel == 2: mode, s_tab, s_row, listening = "settings", 0, 0, False
                else: pygame.quit(); sys.exit()
            draw_menu(msel, t)

        elif mode == "settings":
            n = len(ACTIONS) + 2
            if listening:
                for k in keys:
                    if k == pygame.K_ESCAPE: listening = False
                    else:
                        kb, act = SET["keys"][s_tab], ACTIONS[s_row]
                        for a2 in ACTIONS:
                            if a2 != act and kb[a2] == k: kb[a2] = kb[act]
                        kb[act] = k; save_settings(); listening = False
                        break
            else:
                s_row = (s_row + dn - up) % n
                if any(k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB, pygame.K_a, pygame.K_d) for k in keys): s_tab = 1 - s_tab
                if back: mode = "menu"
                if ok:
                    if s_row < len(ACTIONS): listening = True
                    elif s_row == len(ACTIONS): SET["keys"] = [dict(k) for k in DEFAULT_KEYS]; save_settings()
                    else: mode = "menu"
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

        elif mode == "select":
            sel_t += dt
            for p, m in enumerate(motions):
                if not ready[p] and m.swing in ("left", "right"): sel[p] = (sel[p] + (1 if m.swing == "right" else -1)) % len(CLASS_NAMES)
                if m.slash_p: ready[p] = not ready[p]
            if back: mode = "menu"
            draw_select(sel, ready, sel_t)
            if all(ready):
                heroes, area, inv = [CLASS_NAMES[i] for i in sel], 0, [[], []]
                arena, mode = new_arena(0), "game"

        elif mode in ("game", "tutorial"):
            arena.update(dt, motions)
            arena.draw()
            if back: mode = "menu"
            r = arena.result
            if r == "menu":
                mode = "select" if first_run else "menu"
                sel, ready, first_run = [0, 1], [False, False], False
            elif r == "retry": arena = new_arena(area)
            elif r == "next":
                for p in range(2): inv[p].extend(arena.pending[p])
                area += 1
                if area >= len(AREAS): mode = "victory"
                else: arena = new_arena(area)

        else:  # victory
            gfx.canvas.fill((24, 18, 36))
            title_text("VICTORY!", W // 2, 8, GOLD)
            for p in range(2):
                cx = 120 + p * 240
                text(f"P{p + 1} {heroes[p]} - {len(inv[p])} items", cx, 60, P_COL[p], mid, True)
                for k, it in enumerate(sorted(inv[p], key=lambda i: -i["tier"])[:12]):
                    text(it["name"][:32], cx, 82 + k * 13, RARITY[it["tier"]][1], font, True)
            text("Press Enter for the main menu", W // 2, 252, STEEL, font, True)
            if ok: mode = "menu"
        present()
