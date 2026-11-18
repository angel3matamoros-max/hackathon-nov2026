"""Gameplay scene (waves, combat, loot flow) and the tutorial."""
import math, random
import pygame
from . import gfx
from .config import *
from .gfx import (text, title_text, wrap, fit_lines, bar, gem, glow, blit_ent, lerp, use, world, main_cv, VIGNETTE, DIM, font, mid, box)
from .classes import CLASSES, bonus_for
from .sprites import HERO, ENEMY, CORPSE
from .levels import LEVELS, NUM_LEVELS, get_bg, draw_torches, draw_runes, new_ambient, move_ambient, waves_of
from .loot import MINIS, roll_holy, PW
from .items import roll_item, power, tier_color, tier_name, SLOTS, SLOT_NAMES
from .player import overlap
from .enemies import Enemy, ESTATS
from .bosses import Boss, BOSSES, BOSS_HP

CACHE_CHANCE = 0.35  # chance a cleared (non-final) wave leaves a supply cache
MAX_ALIVE = 8  # cap on simultaneous foes so a wave never swamps the screen
PORTAL_GRACE = 1.5  # seconds after the portal opens before it can be entered
SKIP_RECT = pygame.Rect(W - 130, H - 31, 124, 15)
SKIP_STATE = dict(hot=False)  # set by app: is the mouse over the skip button  # "SKIP TUTORIAL" button (logical canvas coordinates)


def is_flyer(kind):
    return bool(ESTATS[kind].get("fly"))


class Arena:
    def __init__(s, area, players, tut=False, tier=None, gallery=False, gear=None, level=None, label=None):
        s.area, s.A, s.players, s.tut, s.gallery = area, level or LEVELS[area], players, tut, gallery  # level: a castle-maker level dict
        s.tier = 0 if tut else (area if tier is None else tier)
        s.taken, s.dealt = difficulty(s.tier)  # enemies take x taken damage / deal x dealt damage
        s.god, s.debug = False, False
        s.plats = [(0, FLOOR, W)] + s.A["plats"]
        s.enemies, s.corpses, s.projs, s.eprojs, s.hazards, s.parts, s.texts = [], [], [], [], [], [], []
        s.waves = [] if (tut or gallery) else waves_of(s.A)  # waves are fought one after another; the boss follows the last
        s.wave, s.wave_live, s.wave_gap, s.queue, s.drop_mult = -1, False, 1.0, [], 1.0
        s.toasts, s.gear_view, s.props = [], None, []  # props: destructible boss-fight objects (gravestones, crystals, orbs, crates)
        s.t, s.shake, s.state, s.result, s.loot, s.fail_t = 0.0, 0.0, "play", None, None, 0.0
        s.pending = [[] for _ in players]
        s.portal, s.portal_t, s.kills, s.looted, s.dummy_hits = False, 0.0, 0, 0, 0
        s.boss, s.boss_spawned, s.chest, s.cm = None, False, None, None
        s.label = label or f"LEVEL {area + 1}/{NUM_LEVELS}: {s.A['name']}"
        s.banner = [s.label.upper(), 2.5]
        s.amb = new_ambient(area)
        s.step, s.mark = -1, {}
        for p, g in zip(players, (gear or []) + [{}] * len(players)):  # every hero gets recomputed (the CPU's handicap applies even with no gear)
            for it in (g or {}).values():
                if it: p.gear[it["slot"]] = it
            p.recompute()
        s.snap = [dict(p.gear) for p in players]  # gear at level start: restored if both heroes fall (unbanked loot is lost)
        if tut: s.goto(0)

    def both(s, a):
        return f"[{kn(0, a)}] (P2: [{kn(1, a)}])"

    def nearest(s, x):
        al = [p for p in s.players if not p.down]
        return min(al, key=lambda p: abs(p.x - x)) if al else None

    def burst(s, x, y, color, n, sp):
        for _ in range(n):
            an, v = random.uniform(0, 6.28), random.uniform(0.3, 1) * sp
            s.parts.append([x, y, math.cos(an) * v, math.sin(an) * v - 30, random.uniform(0.3, 0.7), color, random.choice((1, 2, 2, 3))])

    def spawn(s, kind, x=None, **kw):
        if x is None: x = random.choice((14, W - 14))
        cls = Boss if kind in BOSSES else Enemy
        e = cls(kind, x, FLOOR - 70 if is_flyer(kind) else FLOOR, s.A.get("tint", 0), **kw)
        s.enemies.append(e); s.burst(x, e.y - 10, (200, 150, 255), 8, 60)
        if isinstance(e, Boss): e.setup(s)
        return e

    def count(s, kind):
        return sum(1 for e in s.enemies if e.kind == kind and e.hp > 0)

    def revive(s, frac=0.4):
        for p in s.players:
            if p.down: p.down, p.hp = False, max(1, int(round(p.maxhp * frac)))

    def spawn_boss(s):
        kind = s.A["boss"]
        if kind is None:  # a castle-maker level without a boss: clearing the waves opens the portal
            s.boss_spawned, s.portal = True, True
            s.banner = ["LEVEL CLEARED! Take the portal >>", 3.0]
            s.revive()
            return None
        e = s.spawn(kind, W + 40, hp=BOSS_HP[min(s.area, len(BOSS_HP) - 1)])  # enters from the right edge
        s.boss, s.boss_spawned = e, True
        s.banner = [f"BOSS: {e.name.upper()}", 3.0]
        s.revive()
        s.shake = 6
        return e

    def hurt(s, e, dmg, kb, by=None):
        """Damage enemy `e`. `by` is the attacking Player (None for environment): its gear gives crit and lifesteal."""
        if e.hp <= 0: return
        d = e.d
        if d.get("dodge") and e.dodge_cd <= 0 and e.state in ("walk", "wind") and e.stun <= 0 and e.frozen <= 0 and e.kind != "dummy":
            e.dodge_cd = d["dodge"]  # cat beast men sidestep the first hit
            e.x = max(10, min(W - 10, e.x + (44 if kb > 0 else -44)))
            s.texts.append([e.x, e.y - d["h"] - 6, "DODGE", CYAN, 0.6]); s.burst(e.x, e.y - 12, CYAN, 8, 80)
            return
        if d.get("shield") and e.stun <= 0 and e.frozen <= 0 and e.state != "wind" and ((kb > 0 and e.face < 0) or (kb < 0 and e.face > 0)):
            dmg *= 0.1 if getattr(e, "guard_t", 0) > 0 else 0.3  # shield up: frontal hits glance off
            s.texts.append([e.x, e.y - d["h"] - 16, "BLOCKED", STEEL, 0.6]); s.burst(e.x + e.face * 8, e.y - d["h"] / 2, STEEL, 5, 70)
        crit = bool(by and by.crit and random.random() < by.crit)
        if e.invulnerable():
            s.texts.append([e.x, e.y - d["h"] - 8, "IMMUNE", CYAN, 0.6]); s.burst(e.x, e.y - d["h"] / 2, CYAN, 4, 70)
            return
        mult = e.dmg_mult()
        if mult < 1.0: s.texts.append([e.x, e.y - d["h"] - 16, "RESISTED", STEEL, 0.5])
        dmg = max(1, int(dmg * mult * (2.0 if crit else 1.0) * (1.0 if e.kind == "dummy" else s.taken) + 0.5))  # round, not floor: truncation shaved up to 21% extra off weak hits at high tiers
        e.hp -= dmg; e.flash, e.kb = 0.12, kb * e.kb_res
        if e.kind != "dummy" and not e.is_boss: e.state, e.st = "rest", 0.3
        s.texts.append([e.x, e.y - d["h"] - 6, str(dmg) + ("!" if crit else ""), GOLD if crit else WHITE, 0.7]); s.burst(e.x, e.y - d["h"] / 2, (255, 240, 200), 6, 90)
        if by and by.lifesteal and not by.down and e.kind != "dummy":
            by.heal_acc += dmg * by.lifesteal; n = int(by.heal_acc); by.heal_acc -= n  # fractions carry over, no 1 HP minimum per hit
            by.hp = min(by.maxhp, by.hp + n)
        s.shake = max(s.shake, 2)
        if e.kind == "dummy": e.hp = 9999; s.dummy_hits += 1

    def hurt_prop(s, pr, dmg):
        if pr.hp <= 0 or (pr.owner is not None and pr.owner.intro > 0): return  # boss still entering: immune
        pr.hp -= max(1, int(dmg)); pr.flash = 0.12
        s.burst(pr.x, pr.y - pr.d["h"] / 2, (255, 240, 200), 4, 70)

    def prop_died(s, pr):
        s.props.remove(pr)
        if pr.data.get("risen"): return
        s.burst(pr.x, pr.y - pr.d["h"] / 2, (230, 230, 230), 14, 120); s.shake = max(s.shake, 3)
        if pr.owner is not None and pr.owner in s.enemies and pr.owner.hp > 0: pr.owner.on_prop_died(pr, s)

    def kill(s, e):
        s.enemies.remove(e); s.kills += 1
        drop = s.tut or random.random() < e.d.get("drop", 0.3) * s.drop_mult  # only some foes leave something worth looting
        s.corpses.append(dict(x=e.x, y=FLOOR if is_flyer(e.kind) else e.y, kind=e.kind, tint=e.tint, hold=0.0, looted=not drop or e.is_boss, plain=not drop or e.is_boss, boss=e.is_boss))
        s.burst(e.x, e.y - 10, (230, 230, 230), 16, 120); s.shake = 5
        if e.is_boss: e.beam_t = 0.0; s.boss_defeated(e)

    def boss_defeated(s, e):
        s.eprojs, s.hazards, s.props = [], [], []
        for o in s.enemies:  # the boss's summons fall with it
            if o.kind != "dummy": o.hp = 0
        s.portal = True
        s.banner = ["BOSS DEFEATED! Open the boss chest, then take the portal >>", 4.0]
        s.revive()
        s.burst(e.x, e.y - 20, GOLD, 40, 200); s.shake = 12
        # the Boss Chest: dropped beside the corpse so holding [loot] never starts the wrong thing
        s.chest = dict(x=float(max(40, min(W - 70, e.x - 55 if e.x > W / 2 else e.x + 55))), y=FLOOR, hold=0.0, used=set(), holy=bool(s.A.get("chest")))

    # ---- waves
    def next_wave(s):
        s.wave += 1
        if s.wave >= len(s.waves):
            s.spawn_boss()
            return
        kinds = [k for k, n in s.waves[s.wave] for _ in range(n)]
        random.shuffle(kinds)
        s.queue = [[s.t + 0.6 + i * 0.55, k] for i, k in enumerate(kinds)]
        s.wave_live = True
        s.banner = [f"WAVE {s.wave + 1}/{len(s.waves)}", 2.0]

    def wave_cleared(s):
        s.wave_live, s.wave_gap = False, 2.5
        if s.wave + 1 < len(s.waves):
            s.texts.append([W // 2, 96, "WAVE CLEARED", GOLD, 1.6])
            if random.random() < CACHE_CHANCE * s.drop_mult:  # sometimes the fallen leave a supply cache
                x = float(random.randint(120, W - 120))
                s.corpses.append(dict(x=x, y=FLOOR, kind="cache", tint=0, hold=0.0, looted=False, plain=False, boss=False))
                s.texts.append([x, FLOOR - 50, "SUPPLY CACHE!", CYAN, 2.0])

    # ---- gear
    def give(s, p, it):
        """Hand a looted item to player `p`: equip it if it beats what is in that slot, otherwise keep it in the bag."""
        old = p.gear[it["slot"]]
        better = old is None or power(it) > power(old)
        if better: p.equip(it)
        s.pending[p.i].append(it)
        s.toasts.append(dict(p=p.i, it=it, equipped=better, old=old, t=4.0))
        s.texts.append([p.x, p.y - 44, ("Equipped " if better else "Bagged ") + it["name"], tier_color(it), 2.2])
        return better

    # ---- enemy projectiles / hazards
    def eshot(s, src, x, y, vx, vy, dmg, kind, g=0.0, life=3.0, blast=0):
        s.eprojs.append(dict(x=float(x), y=float(y), vx=vx, vy=vy, g=g, dmg=dmg * getattr(src, "dscale", 1.0) * s.dealt, life=life, kind=kind, src=src, blast=blast))

    def enemy_shoot(s, e, r, t):
        sx, sy = e.x + e.face * 12, e.y - e.d["h"] * 0.6
        ang = math.atan2((t.y - 16) - sy, t.x - sx)
        s.eshot(e, sx, sy, math.cos(ang) * r["speed"], math.sin(ang) * r["speed"], r["dmg"], r["shot"])
        s.burst(sx, sy, (255, 230, 120), 4, 60)

    def hazard(s, kind, x0, x1, y0, y1, warn, life, dmg, src):
        s.hazards.append(dict(kind=kind, x0=x0, x1=x1, y0=y0, y1=y1, warn=warn, life=life, dmg=dmg, hit=set(), src=src))

    def update_threats(s, dt):
        for h in s.hazards[:]:
            if h["warn"] > 0:
                h["warn"] -= dt
                continue
            h["life"] -= dt
            for p in s.players:
                if not p.down and p.i not in h["hit"] and h["x0"] <= p.x + 4 and p.x - 4 <= h["x1"] and h["y0"] <= p.y and h["y1"] >= p.y - 30:
                    h["hit"].add(p.i)
                    hp0 = p.hp
                    p.take(h["dmg"], None, s, None)
                    if h["kind"] == "grab" and p.hp < hp0: p.rooted = 1.2; s.texts.append([p.x, p.y - 50, "ROOTED!", GREEN, 0.9])  # hit, not dodged or blocked
            if h["life"] <= 0: s.hazards.remove(h)
        for pr in s.eprojs[:]:
            pr["vy"] += pr["g"] * dt
            pr["x"] += pr["vx"] * dt; pr["y"] += pr["vy"] * dt; pr["life"] -= dt
            gone = pr["life"] <= 0 or not -12 < pr["x"] < W + 12 or pr["y"] < -30
            if pr["kind"] in ("bullet", "laser", "soul") and any(q.kind == "crate" and q.hp > 0 and abs(pr["x"] - q.x) < q.d["w"] / 2 and q.y - q.d["h"] < pr["y"] < q.y for q in s.props):
                crate = next(q for q in s.props if q.kind == "crate" and q.hp > 0 and abs(pr["x"] - q.x) < q.d["w"] / 2 and q.y - q.d["h"] < pr["y"] < q.y)
                s.hurt_prop(crate, 6); s.burst(pr["x"], pr["y"], BROWN, 4, 60)  # cover soaks the shot
                s.eprojs.remove(pr)
                continue
            hit = None
            for p in s.players:
                if p.down or abs(pr["x"] - p.x) > 8 or not (p.y - 32 < pr["y"] < p.y + 2): continue
                if pr["kind"] == "wave" and p.y < FLOOR - 14: continue  # shockwaves travel along the ground: jump them
                hit = p
                break
            if pr["blast"] and (hit or pr["y"] >= FLOOR - 4):
                s.explode(pr)
                s.eprojs.remove(pr)
                continue
            if hit:
                if hit.block and hit.block_t < 0.2 and (pr["x"] - hit.x) * hit.face >= 0 and pr["kind"] != "wave":  # perfect block reflects it
                    hit.blocks += 1; hit.perfects += 1
                    s.projs.append(dict(kind="knife", x=pr["x"], y=pr["y"], vx=-pr["vx"] * 1.2, vy=-pr["vy"], dmg=max(30, hit.atk * 2), life=1.5, pierce=False, hit=set(), by=hit))
                    s.texts.append([hit.x, hit.y - 46, "REFLECTED!", GOLD, 1.0]); s.burst(pr["x"], pr["y"], GOLD, 10, 100)
                else:
                    src = pr["src"] if pr["src"] in s.enemies else None
                    hit.take(pr["dmg"], pr["x"], s, src)
                s.eprojs.remove(pr)
            elif gone or pr["y"] > FLOOR + 6:
                s.eprojs.remove(pr)

    def explode(s, pr):
        s.burst(pr["x"], pr["y"], (255, 160, 50), 22, 150); s.shake = max(s.shake, 5)
        for q in s.props:
            if q.kind == "crate" and abs(q.x - pr["x"]) <= pr["blast"] + 12: s.hurt_prop(q, 60)  # blasts wreck cover
        for p in s.players:
            if not p.down and abs(p.x - pr["x"]) <= pr["blast"] and abs(p.y - pr["y"]) < 40:
                p.take(pr["dmg"], pr["x"], s, None)

    def slash_hit(s, p, reach=34, dmg=None):
        x0, x1 = (p.x - 4, p.x + reach) if p.face > 0 else (p.x - reach, p.x + 4)
        for e in list(s.enemies):
            if id(e) not in p.hitset and overlap(x0, x1, p.y - 32, p.y + 2, e):
                p.hitset.add(id(e)); s.hurt(e, dmg or p.atk, p.face * 170, p)
        for q in list(s.props):
            if id(q) not in p.hitset and overlap(x0, x1, p.y - 32, p.y + 2, q):
                p.hitset.add(id(q)); s.hurt_prop(q, dmg or p.atk)

    def hit_radius(s, x, y, r, dmg, kb=140, by=None):
        for e in list(s.enemies):
            if abs(e.x - x) <= r + e.d["w"] / 2 and abs((e.y - e.d["h"] / 2) - y) <= r + e.d["h"] / 2:
                s.hurt(e, dmg, (1 if e.x >= x else -1) * kb, by)
        for q in list(s.props):
            if abs(q.x - x) <= r + q.d["w"] / 2 and abs((q.y - q.d["h"] / 2) - y) <= r + q.d["h"] / 2: s.hurt_prop(q, dmg)

    # ---- Primary Skill (cast)
    def cast(s, p):
        c = p.cls
        p.cast_cd, p.casts, p.hitset = CLASSES[c]["cd"] * p.cd_mult, p.casts + 1, set()
        if c == "Knight":
            p.skill, p.skill_t, p.inv = "charge", 0.22, max(p.inv, 0.3)
        elif c == "Tank":
            s.hit_radius(p.x, p.y - 10, 58, p.atk * 1.5, 200, by=p)
            for e in s.enemies:
                if abs(e.x - p.x) < 62 and e.kind != "dummy": e.stun = 1.5 * e.stun_mult
            s.burst(p.x, p.y, (255, 220, 150), 26, 170); s.shake = 9
        elif c == "Fighter":
            p.skill, p.skill_t, p.tick = "whirl", 0.72, 0.0
        elif c == "Mage":
            s.projs.append(dict(kind="fire", x=p.x + 14 * p.face, y=p.y - 18, vx=255 * p.face, vy=0.0, dmg=p.atk * 1.75, life=1.6, pierce=False, hit=set(), by=p))
        else:  # Rogue Shadow Step
            tg = [e for e in s.enemies if abs(e.x - p.x) < 180]
            if not tg:
                p.cast_cd, p.casts = 0.4, p.casts - 1
                return
            e = min(tg, key=lambda e: abs(e.x - p.x))
            s.burst(p.x, p.y - 14, (150, 90, 220), 12, 90)
            p.x, p.y, p.vy, p.inv = max(10, min(W - 10, e.x - e.face * 20)), e.y, 0.0, 0.4
            p.face = 1 if e.x > p.x else -1
            s.burst(p.x, p.y - 14, (150, 90, 220), 12, 90); s.hurt(e, p.atk * 2.4, p.face * 160, p)

    # ---- Secondary Skill (cast2)
    def cast2(s, p):
        c = p.cls
        p.cast2_cd, p.casts2 = CLASSES[c]["cd2"] * p.cd_mult, p.casts2 + 1
        if c == "Knight":  # Aegis Banner
            for ally in s.players:
                if not ally.down and abs(ally.x - p.x) < 95:
                    heal = min(ally.maxhp - ally.hp, 25)
                    ally.hp += heal
                    ally.inv = max(ally.inv, 0.6)
                    s.texts.append([ally.x, ally.y - 36, f"+{heal} HP", GREEN, 1.0])
            s.hit_radius(p.x, p.y - 14, 52, p.atk * 0.9, 220, by=p)
            s.burst(p.x, p.y - 16, GOLD, 24, 140); s.shake = 4
        elif c == "Tank":  # Iron Taunt
            p.shield, p.shield_t = 30.0, 4.0
            s.texts.append([p.x, p.y - 40, "+30 SHIELD", CYAN, 1.0])
            for e in s.enemies:
                if abs(e.x - p.x) < 140 and e.kind != "dummy":
                    e.kb = (1 if p.x > e.x else -1) * 180 * e.kb_res
                    e.stun = max(e.stun, 0.6 * e.stun_mult)
            s.burst(p.x, p.y - 14, CYAN, 22, 130); s.shake = 5
        elif c == "Fighter":  # Blade Wave
            s.projs.append(dict(kind="wave", x=p.x + 14 * p.face, y=p.y - 16, vx=290 * p.face, vy=0.0, dmg=p.atk * 1.35, life=1.2, pierce=True, hit=set(), by=p))
            s.burst(p.x + 10 * p.face, p.y - 16, (180, 230, 255), 10, 80)
        elif c == "Mage":  # Frost Nova
            s.hit_radius(p.x, p.y - 14, 68, p.atk * 1.15, 90, by=p)
            for e in s.enemies:
                if abs(e.x - p.x) < 72 and e.kind != "dummy":
                    e.frozen = 2.0 * e.stun_mult
            s.burst(p.x, p.y - 14, CYAN, 28, 160); s.shake = 5
        else:  # Rogue Fan of Knives
            p.vx = -p.face * 150
            p.vy = min(p.vy, -140)
            for vy in (-70, 0, 70):
                s.projs.append(dict(kind="knife", x=p.x + 10 * p.face, y=p.y - 16, vx=310 * p.face, vy=vy, dmg=p.atk * 0.85, life=0.75, pierce=False, hit=set(), by=p))
            s.burst(p.x, p.y - 14, BLADE, 10, 70)

    # ---- tutorial
    def goto(s, n):
        s.step, p = n, s.players[0]
        s.enemies, s.projs, s.corpses = [], [], []
        s.mark = dict(
            travel=p.travel, djumps=p.djumps, dashes=p.dashes, blocks=p.blocks,
            casts=p.casts, casts2=p.casts2, kills=s.kills, hits=s.dummy_hits, looted=s.looted
        )
        if n in (3, 5):
            s.spawn("dummy", 300)
        elif n == 4:
            s.spawn("skeleton", 380, dscale=0.0, hp=9999)
        elif n == 6:
            s.spawn("skeleton", 380, dscale=0.55)
        elif n == 8:
            SET["tutorial_done"] = True
            save_settings()

    def tut_info(s):
        p, m, b, st = s.players[0], s.mark, s.both, s.step
        if st == 0:
            v = p.travel - m["travel"]
            return "MOVE", [f"Left: {b('left')}", f"Right: {b('right')}"], v >= 120, f"{min(120, int(v))}/120"
        if st == 1:
            return "JUMP & WALL-JUMP", [
                f"Jump: {b('jump')} (hold for higher jump)",
                "Press jump AGAIN in mid-air or on a wall for a double / wall jump.",
                f"Drop through a platform: {b('down')}"
            ], p.djumps > m["djumps"], ""
        if st == 2:
            return "DASH", [f"Dash: {b('dash')}", "Works on ground or mid-air with brief invincibility."], p.dashes > m["dashes"], ""
        if st == 3:
            v = s.dummy_hits - m["hits"]
            return "SLASH", [f"Slash: {b('slash')}", "Hit the training dummy 3 times."], v >= 3, f"{min(3, v)}/3"
        if st == 4:
            v = p.blocks - m["blocks"]
            return "BLOCK & PARRY", [
                f"Block: HOLD {b('block')} facing the enemy",
                "Block when the skeleton flashes red and shows '!'",
                "Block at the last instant = PERFECT BLOCK (stuns it)."
            ], v >= 2, f"{min(2, v)}/2"
        if st == 5:
            d = CLASSES[p.cls]
            c1, c2 = p.casts > m["casts"], p.casts2 > m["casts2"]
            return "CAST BOTH SKILLS", [
                f"Skill 1 ({d['skill']}): {b('cast')}",
                f"Skill 2 ({d['skill2']}): {b('cast2')}",
                "Cast BOTH skills once to continue."
            ], c1 and c2, f"{int(c1) + int(c2)}/2"
        if st == 6:
            return "FIGHT!", [
                "Defeat the skeleton! (If you fall, the fight restarts.)",
                f"Slash {b('slash')}   Block {b('block')}   Dash {b('dash')}",
                f"Skill 1 {b('cast')}   Skill 2 {b('cast2')}"
            ], s.kills > m["kills"], ""
        if st == 7:
            return "LOOT THE CORPSE", [
                f"Stand on the corpse and HOLD {b('interact')}",
                "Beat the mini-game (40%+) to claim loot.",
                f"Loot is GEAR (weapon / armor / charm) with real bonuses. See it with {b('gear')}.",
                "In the real game only some foes drop loot."
            ], s.looted > m["looted"], ""
        return "TUTORIAL COMPLETE", [
            "Clear all enemies in an area, loot corpses, then enter the portal.",
            "If both heroes fall, ALL unbanked loot from that area is lost!",
            f"Press {b('slash')} to continue"
        ], False, ""

    # ---- loot mini-game
    def start_loot(s, p, c):
        if p.cpu:  # the CPU ally never opens a mini-game (it would freeze the human): it just gets an average roll
            c["looted"] = True; s.looted += 1
            s.give(p, roll_item(0.5 + (0.3 if c.get("boss") or c["kind"] == "cache" else 0.0)))
            return
        m = random.choice(MINIS)()
        m.hero, m.bonus = p.cls, bonus_for(p.cls, m.kind)
        s.loot, s.state = dict(p=p, c=c, m=m, intro=3.0, after=0.0, panel=pygame.Surface((PW, 180))), "loot"

    def update_loot(s, dt, mo):
        L = s.loot
        m = L["m"]
        if L["intro"] > 0:
            L["intro"] -= dt
            return
        m.update(dt, mo[L["p"].i])
        if m.over:
            L["after"] += dt
            if L["after"] > 1.3:
                p, c = L["p"], L["c"]
                if m.score >= 0.4:
                    c["looted"] = True
                    s.looted += 1
                    s.give(p, roll_item(min(1.0, m.score + (0.3 if c.get("boss") or c["kind"] == "cache" else 0.0))))
                else:
                    c["hold"] = 0.0
                    if not s.tut:
                        c["looted"] = True
                    s.texts.append([c["x"], c["y"] - 34, "Failed - no loot!" + (" Try again!" if s.tut else ""), RED, 2.2])
                s.state, s.loot = "play", None

    # ---- boss chest: every boss drops one. Each hero picks 1 of 3 epic / legendary items (weapon, armor, charm) or leaves. On levels with
    # `chest` set (the Cathedral) the weapon card is the class's holy weapon: 75% blessed, 25% cursed but far stronger.
    def chest_offers(s, p):
        holy = bool(s.chest and s.chest.get("holy"))
        offers = []
        for slot in SLOTS:
            if slot == "weapon" and holy: offers.append(roll_holy(p.cls))
            else: offers.append(roll_item(random.uniform(0.55, 1.0), boss=True, slot=slot, min_tier=2))
        return offers

    def start_chest(s, p):
        s.cm = dict(p=p, offers=s.chest_offers(p), sel=0, t=0.0)
        if p.cpu:  # CPU ally: takes the strongest item that is not cursed
            offers = s.cm["offers"]
            gain = [(power(it) - power(p.gear[it["slot"]]), k) for k, it in enumerate(offers) if not it.get("cursed")]
            best = max(gain) if gain else (0, None)
            s.resolve_chest(p, offers, best[1] if best[0] > 0 else None); s.cm = None
            return
        s.state = "chest"

    def resolve_chest(s, p, offers, idx):
        """Hero `p` takes offers[idx] (equipped straight away) or, with idx None, leaves the chest."""
        if idx is not None:
            w = offers[idx]
            old = p.gear[w["slot"]]
            p.equip(w)
            s.pending[p.i].append(w)
            s.toasts.append(dict(p=p.i, it=w, equipped=True, old=old, t=4.0))
            s.texts.append([p.x, p.y - 44, f"Equipped {w['name']}", tier_color(w), 2.2])
        else:
            s.texts.append([p.x, p.y - 44, "Left it behind", STEEL, 1.5])
        s.chest["used"].add(p.i)

    def update_chest(s, dt, mo):
        C = s.cm
        m = mo[C["p"].i]
        C["t"] += dt
        if C["t"] < 0.5: return
        n = len(C["offers"])
        if m.swing == "left": C["sel"] = max(0, C["sel"] - 1)
        elif m.swing == "right": C["sel"] = min(n, C["sel"] + 1)  # the last slot is LEAVE
        if m.slash_p:
            s.resolve_chest(C["p"], C["offers"], C["sel"] if C["sel"] < n else None)
            s.state, s.cm = "play", None

    # ---- update
    def fx(s, dt):
        for pt in s.parts[:]:
            pt[0] += pt[2] * dt; pt[1] += pt[3] * dt; pt[3] += 300 * dt; pt[4] -= dt
            if pt[4] <= 0: s.parts.remove(pt)
        for tx in s.texts[:]:
            tx[1] -= 18 * dt; tx[4] -= dt
            if tx[4] <= 0: s.texts.remove(tx)
        move_ambient(s.area, s.amb, s.t, dt)

    def update(s, dt, mo):
        s.shake, s.banner[1] = max(0, s.shake - 30 * dt), s.banner[1] - dt
        s.fx(dt)
        if s.state == "gear":  # gear screen (pauses the action)
            if any(m.gear_p or m.skip_p for m in mo): s.state = "play"
            return
        if s.state == "play" and any(m.gear_p for m in mo): s.state = "gear"; return
        if s.state == "loot": s.update_loot(dt, mo); return
        if s.state == "chest": s.update_chest(dt, mo); return
        if s.state == "failed":
            s.fail_t += dt
            if s.fail_t > 0.8 and any(m.slash_p for m in mo): s.result = "retry"
            return
        s.t += dt  # the wave clock only runs while the battle does (see the early returns above)
        for p in s.players: p.update(dt, mo[p.i], s)
        for tz in s.toasts[:]:
            tz["t"] -= dt
            if tz["t"] <= 0: s.toasts.remove(tz)
        alive = sum(1 for e in s.enemies if e.kind != "dummy" and e.hp > 0)
        while s.queue and s.queue[0][0] <= s.t and alive < MAX_ALIVE:
            s.spawn(s.queue.pop(0)[1], dscale=1.0); alive += 1
        for e in s.enemies[:]:
            if e.hp > 0: e.update(dt, s)
            if e.hp <= 0 and e in s.enemies: s.kill(e)
        s.update_threats(dt)
        for q in s.props[:]:
            q.update(dt, s)
            if q.hp <= 0 and q in s.props: s.prop_died(q)
        for pr in s.projs[:]:
            pr["x"] += pr["vx"] * dt
            pr["y"] += pr["vy"] * dt
            pr["life"] -= dt
            hits = [e for e in s.enemies if id(e) not in pr["hit"] and overlap(pr["x"] - 6, pr["x"] + 6, pr["y"] - 8, pr["y"] + 8, e)]
            phits = [q for q in s.props if id(q) not in pr["hit"] and overlap(pr["x"] - 6, pr["x"] + 6, pr["y"] - 8, pr["y"] + 8, q)]
            if hits or phits:
                if pr["kind"] == "fire":
                    s.projs.remove(pr)
                    s.hit_radius(pr["x"], pr["y"], 30, pr["dmg"], 160, by=pr.get("by"))
                    s.burst(pr["x"], pr["y"], (255, 160, 50), 20, 140); s.shake = 4
                    continue
                for e in hits:
                    pr["hit"].add(id(e))
                    s.hurt(e, pr["dmg"], (1 if pr["vx"] >= 0 else -1) * 130, pr.get("by"))
                for q in phits:
                    pr["hit"].add(id(q)); s.hurt_prop(q, pr["dmg"])
                if not pr["pierce"]:
                    s.projs.remove(pr)
                    s.burst(pr["x"], pr["y"], BLADE, 6, 70)
                    continue
            if pr["life"] <= 0 or not 0 < pr["x"] < W or not 0 < pr["y"] < FLOOR:
                if pr in s.projs:
                    if pr["kind"] == "fire":
                        s.hit_radius(pr["x"], pr["y"], 28, pr["dmg"], 160, by=pr.get("by"))
                        s.burst(pr["x"], pr["y"], (255, 160, 50), 20, 140)
                    s.projs.remove(pr)
        for c in s.corpses:
            if c["looted"]: continue
            who = [p for p in s.players if not p.down and mo[p.i].interact_h and abs(p.x - c["x"]) < 26 and abs(p.y - c["y"]) < 30]
            c["hold"] = c["hold"] + dt if who else max(0, c["hold"] - 2 * dt)
            if who and c["hold"] >= 0.5:
                s.start_loot(who[0], c)
                break
        ch = s.chest
        if ch and s.state == "play":
            who = [p for p in s.players if not p.down and p.i not in ch["used"] and mo[p.i].interact_h and abs(p.x - ch["x"]) < 28 and abs(p.y - ch["y"]) < 30]
            ch["hold"] = ch["hold"] + dt if who else max(0, ch["hold"] - 2 * dt)
            if who and ch["hold"] >= 0.5:
                ch["hold"] = 0.0
                s.start_chest(who[0])
        if s.tut:
            for p in s.players:
                if p.down:
                    p.down, p.hp = False, p.maxhp
                    s.texts.append([p.x, p.y - 36, "TRY AGAIN!", RED, 1.2])
                    s.goto(s.step)
                    return
            if s.step == 8:
                if mo[0].slash_p and s.t > 0.5: s.result = "menu"
            elif s.tut_info()[2]:
                s.goto(s.step + 1)
        elif s.gallery:
            s.revive(1.0)
        else:
            foes = [e for e in s.enemies if e.kind != "dummy"]
            if not s.boss_spawned and not s.queue and not foes:
                if s.wave_live: s.wave_cleared()
                s.wave_gap -= dt
                if s.wave_gap <= 0: s.next_wave()
            if s.portal: s.portal_t += dt
            # grace period: a player who happens to stand at the exit when the boss falls must not be whisked away before looting
            if s.portal and s.portal_t > PORTAL_GRACE and any(not p.down and p.x > W - 40 for p in s.players): s.result = "next"
            if all(p.down for p in s.players):
                s.state, s.pending = "failed", [[] for _ in s.players]
                for p, g in zip(s.players, s.snap):  # unbanked loot is lost: back to the gear we started the level with
                    p.gear = dict(g); p.recompute()

    # ---- draw
    def draw_toasts(s):
        """Loot popups under each player's HUD: name, plain-language effect, and whether it was equipped."""
        used = {0: 96, 1: 96}
        shown = {0: 0, 1: 0}
        for tz in reversed(s.toasts):
            if shown[tz["p"]] >= 2: continue
            shown[tz["p"]] += 1
            it = tz["it"]
            lines = wrap(it["desc"], 31)[:3]
            h, x = 26 + 11 * len(lines), (6 if tz["p"] == 0 else W - 202)
            y = used[tz["p"]]
            used[tz["p"]] += h + 4
            pygame.draw.rect(gfx.canvas, INK, (x, y, 196, h)); pygame.draw.rect(gfx.canvas, tier_color(it), (x, y, 196, h), 1)
            text(it["name"][:33], x + 4, y + 3, tier_color(it))
            for j, ln in enumerate(lines): text(ln, x + 4, y + 14 + j * 11, WHITE)
            lab = f"{tier_name(it)} {SLOT_NAMES[it['slot']]}: "
            text(lab + ("EQUIPPED" if tz["equipped"] else "bagged (yours is better)"), x + 4, y + h - 11, GREEN if tz["equipped"] else STEEL)

    def draw_chest(s):
        C = s.cm
        p, offers = C["p"], C["offers"]
        gfx.canvas.blit(DIM, (0, 0))
        pygame.draw.rect(gfx.canvas, INK, (14, 14, W - 28, H - 28)); pygame.draw.rect(gfx.canvas, GOLD, (14, 14, W - 28, H - 28), 1)
        title_text("BOSS CHEST", W // 2, 18, GOLD, 2)
        text(f"P{p.i + 1} {p.cls}: pick ONE", W // 2, 44, P_COL[p.i], mid, True)
        for k, it in enumerate(offers):
            x, y, on = 22 + k * 148, 62, C["sel"] == k
            col = tier_color(it)
            pygame.draw.rect(gfx.canvas, (30, 24, 44), (x, y, 140, 128)); pygame.draw.rect(gfx.canvas, col, (x, y, 140, 128), 3 if on else 1)
            text(f"{SLOT_NAMES[it['slot']].upper()}  [{tier_name(it)}]", x + 70, y + 4, col, font, True)
            for j, ln in enumerate(fit_lines(it["name"], 134, 2)): text(ln, x + 70, y + 17 + j * 11, WHITE, font, True)
            for j, ln in enumerate(fit_lines(it["desc"], 132, 6)): text(ln, x + 6, y + 44 + j * 11, GREEN if not it.get("cursed") else (230, 150, 255))
            if on: text("> TAKE <", x + 70, y + 114, GOLD, font, True)
            if it["slot"] == "weapon":
                cur = p.gear["weapon"]
                new_atk = int(round((8 + CLASSES[p.cls]["atk"] * 2) * it.get("atk", 1.0)))
                text(f"ATK {p.atk} -> {new_atk}" if not cur else f"ATK -> {new_atk}", x + 70, y + 104, STEEL, font, True)
        on = C["sel"] == len(offers)
        text("> LEAVE <" if on else "LEAVE", W // 2, 198, RED if on else STEEL_D, mid, True)
        text(f"[{kn(p.i, 'left')}]/[{kn(p.i, 'right')}] choose   [{kn(p.i, 'slash')}] confirm   (equipped at once)", W // 2, 220, P_COL[p.i], font, True)

    def draw_gear(s):
        gfx.canvas.blit(DIM, (0, 0))
        n = len(s.players)
        pygame.draw.rect(gfx.canvas, INK, (14, 14, W - 28, H - 28)); pygame.draw.rect(gfx.canvas, GOLD, (14, 14, W - 28, H - 28), 1)
        title_text("GEAR", W // 2, 18, GOLD, 2)
        for p in s.players:
            cx = 22 + p.i * (W - 28) // n
            text(f"P{p.i + 1} {p.cls}{' (CPU)' if p.cpu else ''}", cx, 44, P_COL[p.i], mid)
            text(f"HP {p.maxhp}  ATK {p.atk}  Dmg taken x{p.dmg_taken:.2f}", cx, 58, STEEL)
            text(f"Cooldowns x{p.cd_mult:.2f}  Speed x{p.speed:.2f}  Crit {int(p.crit * 100)}%", cx, 69, STEEL)
            y = 84
            for sl in SLOTS:
                it = p.gear[sl]
                text(SLOT_NAMES[sl].upper(), cx, y, STEEL_D)
                if it:
                    text(f"{it['name']} [{tier_name(it)}]"[:40], cx, y + 10, tier_color(it))
                    lines = wrap(it["desc"], 34)[:3]
                    for k, ln in enumerate(lines): text(ln, cx + 4, y + 21 + k * 11, WHITE)
                    y += 24 + 11 * len(lines)
                else:
                    text("(empty)", cx, y + 10, STEEL_D); y += 30
        text("Better items auto-equip. If both heroes fall, this area's loot is lost.", W // 2, H - 38, STEEL, font, True)
        text("Press the Gear key again to close", W // 2, H - 27, STEEL_D, font, True)

    def draw_hud(s):
        for p in s.players:
            x, d = (8 if p.i == 0 else W - 128), CLASSES[p.cls]
            text(f"P{p.i + 1} {p.cls}" + (" (CPU)" if p.cpu else ""), x, 6, P_COL[p.i])
            bar(x, 19, 120, 7, p.hp / p.maxhp, RED if p.hp > p.maxhp * .3 else (255, 120, 40))
            if p.shield > 0:
                bar(x, 19, int(120 * min(1.0, p.shield / 30.0)), 3, 1.0, CYAN)
            cd1 = 1 - p.cast_cd / (d["cd"] * p.cd_mult)
            cd2 = 1 - p.cast2_cd / (d["cd2"] * p.cd_mult)
            bar(x, 30, 58, 4, cd1, CYAN if cd1 >= 1 else STEEL_D)
            bar(x + 62, 30, 58, 4, cd2, GOLD if cd2 >= 1 else STEEL_D)
            text(f"[{kn(p.i, 'cast')}] {d['skill']}", x, 37, WHITE if cd1 >= 1 else STEEL_D)
            text(f"[{kn(p.i, 'cast2')}] {d['skill2']}", x, 48, GOLD if cd2 >= 1 else STEEL_D)
            if not s.tut:
                text(f"Found: {len(s.pending[p.i])}  Gear [{kn(p.i, 'gear')}]", x, 60, GOLD)
                for k, sl in enumerate(SLOTS):  # the three gear slots, coloured by rarity (grey = empty)
                    it = p.gear[sl]
                    pygame.draw.rect(gfx.canvas, INK, (x + k * 14, 71, 12, 12)); pygame.draw.rect(gfx.canvas, tier_color(it) if it else STEEL_D, (x + k * 14, 71, 12, 12), 1)
                    if it: pygame.draw.rect(gfx.canvas, tier_color(it), (x + k * 14 + 3, 74, 6, 6))
        if not s.tut:
            b = s.boss if (s.boss and s.boss.hp > 0) else None
            wv = f"  WAVE {s.wave + 1}/{len(s.waves)}" if (s.waves and not s.boss_spawned and s.wave >= 0) else ""
            text(b.name.upper() if b else s.label + wv, W // 2, 6, RED if b else WHITE, font, True)
            if b:
                bar(136, 18, 208, 9, b.hp / b.maxhp, RED)
                for f in (.66, .33): pygame.draw.rect(gfx.canvas, INK, (136 + int(208 * f), 18, 2, 9))  # phase marks
                st = b.status()
                if st: text(st[0], W // 2, 30, st[1], font, True)
            if s.tier > 0:
                text(f"Threat x{s.dealt:.2f}  (foes take x{s.taken:.2f})", W // 2, 42 if b else 17, (255, 150, 70), font, True)
            if s.god: text("GOD MODE", W // 2, 54, GREEN, font, True)
            if b and b.intro > 0:  # entrance name card
                pygame.draw.rect(gfx.canvas, INK, (0, 96, W, 56)); pygame.draw.rect(gfx.canvas, RED, (0, 96, W, 56), 1)
                title_text(b.name.upper(), W // 2, 100, GOLD, 2)
                text(b.cfg["tag"], W // 2, 136, STEEL, font, True)

    def draw(s):
        use(world)
        world.blit(get_bg(s.area, s.A["plats"]), (0, 0))
        A = s.A
        if A.get("torches"): draw_torches(s.t, (130, 76, 24) if s.area != 2 else (150, 120, 50))
        if A.get("runes"): draw_runes(s.t, (80, 40, 130) if s.area != 3 else (30, 110, 60))
        n, col, shape, _ = A["amb"]
        for m in s.amb:
            if shape == "glow" and math.sin(s.t * 3 + m["p"]) > 0:
                glow(m["x"], m["y"], 8, (90, 100, 20))
            sz = 2 if s.area else 1
            pygame.draw.rect(gfx.canvas, col, (int(m["x"]), int(m["y"]), sz, sz))
        if s.portal:
            x, y = W - 28, FLOOR
            col = lerp((90, 60, 200), (160, 230, 255), 0.5 + 0.5 * math.sin(s.t * 4))
            pygame.draw.rect(gfx.canvas, INK, (x - 17, y - 56, 34, 56)); pygame.draw.circle(gfx.canvas, INK, (x, y - 56), 17)
            pygame.draw.rect(gfx.canvas, col, (x - 13, y - 56, 26, 56)); pygame.draw.circle(gfx.canvas, col, (x, y - 56), 13)
            glow(x, y - 40, 50, (60, 50, 120))
            text("UP THE CASTLE", W - 4, y - 90 + int(math.sin(s.t * 3) * 3), WHITE, font, right=True)
        for c in s.corpses:
            if c["kind"] == "cache":
                if not c["looted"]:
                    x, y = int(c["x"]), int(c["y"])
                    box(gfx.canvas, BROWN, x - 8, y - 9, 16, 9); box(gfx.canvas, (150, 96, 60), x - 8, y - 13, 16, 5); pygame.draw.rect(gfx.canvas, CYAN, (x - 1, y - 10, 3, 4))
                else: continue
            else:
                fr = CORPSE[(c["kind"], c["tint"] if c["kind"] == "slime" else 0)]
                blit_ent(fr, c["x"], c["y"], False, (-60, -60, -60) if (c["looted"] and not c.get("plain")) else None)
            if not c["looted"]:
                gy = c["y"] - 26 + math.sin(s.t * 4 + c["x"]) * 3
                glow(c["x"], gy, 18, (110, 90, 30)); gem(int(c["x"]), int(gy), GOLD, 5)
                near = [p for p in s.players if not p.down and abs(p.x - c["x"]) < 26 and abs(p.y - c["y"]) < 30]
                if near: text(f"HOLD [{kn(near[0].i, 'interact')}]", c["x"], c["y"] - 50, P_COL[near[0].i], font, True)
                if c["hold"] > 0: bar(int(c["x"]) - 12, int(c["y"]) - 42, 24, 4, c["hold"] / 0.5, GOLD)
        ch = s.chest
        if ch:
            used = len(ch["used"]) >= len(s.players)
            x, y = int(ch["x"]), int(ch["y"])
            box(gfx.canvas, BROWN_D if used else BROWN, x - 11, y - 12, 22, 12); box(gfx.canvas, BROWN_D if used else (150, 96, 60), x - 11, y - 19, 22, 8)
            pygame.draw.rect(gfx.canvas, GOLD, (x - 11, y - 13, 22, 2)); pygame.draw.rect(gfx.canvas, GOLD, (x - 2, y - 14, 4, 5))
            if not used:
                glow(x, y - 14 + math.sin(s.t * 4) * 2, 30, (130, 110, 40))
                near = [p for p in s.players if not p.down and p.i not in ch["used"] and abs(p.x - ch["x"]) < 28 and abs(p.y - ch["y"]) < 30]
                if near: text(f"HOLD [{kn(near[0].i, 'interact')}] BOSS CHEST", ch["x"], y - 40, P_COL[near[0].i], font, True)
                if ch["hold"] > 0: bar(x - 12, y - 32, 24, 4, ch["hold"] / 0.5, GOLD)
        for hz in s.hazards:
            r = pygame.Rect(int(hz["x0"]), int(hz["y0"]), int(hz["x1"] - hz["x0"]), int(hz["y1"] - hz["y0"]))
            if hz["warn"] > 0:
                pygame.draw.rect(gfx.canvas, (220, 60, 60) if hz["kind"] != "grab" else (90, 200, 90), r, 1)
                if int(s.t * 12) % 2: pygame.draw.rect(gfx.canvas, (120, 30, 40), r.inflate(-2, -2), 1)
            elif hz["kind"] == "grab":
                pygame.draw.rect(gfx.canvas, (60, 150, 70), r)
                for k in range(3): pygame.draw.line(gfx.canvas, (150, 230, 120), (r.x + 3 + k * 7, r.bottom), (r.x + 1 + k * 7 + (int(s.t * 12) % 3), r.y), 2)
            elif hz["kind"] == "beam":
                pygame.draw.rect(gfx.canvas, (255, 90, 90), r); pygame.draw.rect(gfx.canvas, WHITE, r.inflate(0, -r.h + 4))
            else:
                pygame.draw.rect(gfx.canvas, (255, 240, 170), r); pygame.draw.rect(gfx.canvas, WHITE, r.inflate(-r.w // 2, 0))
                glow(r.centerx, FLOOR - 20, 40, (120, 100, 40))
        for q in s.props: q.draw(s)
        b = s.boss
        if b and b.beam_t > 0 and b.hp > 0:  # tractor beam (a dead boss's beam is off)
            col = (120, 230, 255)
            pts = [(b.x - 10, b.y), (b.x + 10, b.y), (b.x + 46, FLOOR), (b.x - 46, FLOOR)]
            beam = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.polygon(beam, col + (70 + int(30 * math.sin(s.t * 14)),), pts)
            gfx.canvas.blit(beam, (0, 0))
            for k in range(5): pygame.draw.line(gfx.canvas, WHITE, (b.x - 30 + k * 15, FLOOR - ((s.t * 120 + k * 30) % 120)), (b.x - 30 + k * 15, FLOOR - ((s.t * 120 + k * 30) % 120) - 6), 1)
        ents = [(e.y, e) for e in s.enemies] + [(p.y, p) for p in s.players if not p.down]
        for _, o in sorted(ents, key=lambda z: z[0]):
            if isinstance(o, Enemy):
                fr = ENEMY[(o.kind, o.tint if o.kind == "slime" else 0)]
                sy = FLOOR if is_flyer(o.kind) else o.y
                sw = max(18, o.d["w"] + 4)
                pygame.draw.ellipse(gfx.canvas, (10, 8, 16), (o.x - sw / 2, sy - 2, sw, 4))
                tint = (0, 90, 130) if o.frozen > 0 else ((110, 0, 0) if (o.state == "wind" and int(s.t * 14) % 2 == 0) else ((110, 110, 110) if o.flash > 0 else None))
                blit_ent(fr[int(o.anim * 6) % len(fr)], o.x, o.y + o.d.get("foot", 0), o.face < 0, tint)
                if o.frozen > 0:
                    pygame.draw.rect(gfx.canvas, CYAN, (int(o.x - o.d["w"] / 2), int(o.y - o.d["h"]), o.d["w"], o.d["h"]), 1)
                elif o.state == "wind":
                    text("!", o.x - 2, o.y - o.d["h"] - 16, RED, mid)
                if o.d.get("shield") and o.state != "wind" and o.stun <= 0:
                    pygame.draw.line(gfx.canvas, STEEL, (o.x + o.face * 9, o.y - o.d["h"] + 6), (o.x + o.face * 9, o.y - 4), 2)
                if o.hp < o.maxhp < 9000 and not o.is_boss: bar(int(o.x) - 10, int(o.y - o.d["h"]) - 8, 20, 3, o.hp / o.maxhp, RED)
            else:
                pygame.draw.ellipse(gfx.canvas, (10, 8, 16), (o.x - 9, o.y - 2, 18, 4))
                if o.inv > 0 and o.dash_t <= 0 and int(s.t * 24) % 2: continue
                fr = HERO[o.cls][1][int(o.anim) % 8] if (o.ground and o.anim > 0) else (HERO[o.cls][0] if o.ground else HERO[o.cls][1][2])
                blit_ent(fr, o.x + (o.face * 3 if o.slash_t > 0 else 0), o.y, o.face < 0, (110, 110, 110) if o.flash > 0 else None)
                cx, cy = o.x, o.y - 17
                if o.rooted > 0:
                    for k in range(4): pygame.draw.line(gfx.canvas, (150, 230, 120), (o.x - 8 + k * 5, o.y), (o.x - 6 + k * 4, o.y - 14), 2)
                if o.shield > 0:
                    pygame.draw.circle(gfx.canvas, CYAN, (int(cx), int(cy)), 16, 1)
                if o.slash_t > 0:
                    for r, col, w in ((28, WHITE, 3), (22, (180, 220, 255), 2)):
                        pts = [(cx + o.face * math.cos(math.radians(-70 + 140 * k / 6)) * r, cy + math.sin(math.radians(-70 + 140 * k / 6)) * r) for k in range(7)]
                        pygame.draw.lines(gfx.canvas, col, False, pts, w)
                if o.block:
                    pts = [(cx + o.face * (6 + math.cos(math.radians(-80 + 160 * k / 6)) * 18), cy + math.sin(math.radians(-80 + 160 * k / 6)) * 18) for k in range(7)]
                    pygame.draw.lines(gfx.canvas, GOLD if o.block_t < 0.2 else CYAN, False, pts, 2)
                if o.skill == "whirl":
                    pygame.draw.circle(gfx.canvas, WHITE, (int(cx), int(cy)), 32, 1)
                    for k in range(3):
                        an = s.t * 22 + k * 2.1
                        pygame.draw.line(gfx.canvas, WHITE, (cx, cy), (cx + math.cos(an) * 32, cy + math.sin(an) * 32), 2)
        for pr in s.projs:
            if pr["kind"] == "fire":
                glow(pr["x"], pr["y"], 22, (200, 90, 20))
                pygame.draw.circle(gfx.canvas, (255, 140, 40), (int(pr["x"]), int(pr["y"])), 5); pygame.draw.circle(gfx.canvas, GOLD, (int(pr["x"]), int(pr["y"])), 3)
            elif pr["kind"] == "wave":
                d = 1 if pr["vx"] >= 0 else -1
                pts = [(pr["x"] - d * 4, pr["y"] - 12), (pr["x"] + d * 6, pr["y"]), (pr["x"] - d * 4, pr["y"] + 12)]
                pygame.draw.lines(gfx.canvas, CYAN, False, pts, 3)
            else:
                d = 1 if pr["vx"] >= 0 else -1
                pygame.draw.line(gfx.canvas, BLADE, (pr["x"] - d * 5, pr["y"]), (pr["x"] + d * 5, pr["y"]), 2)
        for pr in s.eprojs:
            x, y, k = int(pr["x"]), int(pr["y"]), pr["kind"]
            if k == "bullet":
                pygame.draw.line(gfx.canvas, (255, 240, 140), (x, y), (x - int(pr["vx"] / 60), y - int(pr["vy"] / 60)), 2); glow(x, y, 8, (120, 100, 30))
            elif k == "soul":
                glow(x, y, 16, (30, 120, 60)); pygame.draw.circle(gfx.canvas, (110, 240, 140), (x, y), 4); pygame.draw.circle(gfx.canvas, WHITE, (x, y), 2)
            elif k == "laser":
                pygame.draw.line(gfx.canvas, (255, 90, 120), (x, y), (x - int(pr["vx"] / 25), y - int(pr["vy"] / 25)), 2); glow(x, y, 10, (120, 30, 50))
            elif k == "wave":
                d = 1 if pr["vx"] >= 0 else -1
                pygame.draw.polygon(gfx.canvas, (255, 220, 150), [(x - d * 6, y), (x + d * 4, y - 8), (x + d * 4, y)])
            elif k == "dyn":
                pygame.draw.rect(gfx.canvas, (200, 50, 50), (x - 3, y - 2, 6, 4)); pygame.draw.rect(gfx.canvas, GOLD, (x - 1, y - 5, 2, 3))
            else:  # rocket
                pygame.draw.rect(gfx.canvas, WHITE, (x - 3, y - 2, 6, 4)); glow(x, y, 14, (160, 90, 30))
        for pt in s.parts: pygame.draw.rect(gfx.canvas, pt[5], (int(pt[0]), int(pt[1]), pt[6], pt[6]))
        for tx in s.texts: text(tx[2], tx[0], tx[1], tx[3], font, True)
        if s.debug:
            for o in s.enemies: pygame.draw.rect(gfx.canvas, (255, 60, 60), (int(o.x - o.d["w"] / 2), int(o.y - o.d["h"]), o.d["w"], o.d["h"]), 1)
            for o in s.players: pygame.draw.rect(gfx.canvas, (60, 255, 120), (int(o.x - 6), int(o.y - 30), 12, 30), 1)
        use(main_cv)
        main_cv.fill(INK)
        main_cv.blit(world, (int(random.uniform(-1, 1) * s.shake), int(random.uniform(-1, 1) * s.shake)))
        main_cv.blit(VIGNETTE, (0, 0))
        s.draw_hud()
        if s.A.get("hint") and not s.tut and not s.gallery and s.t < 14:
            text(f"Slash {s.both('slash')}  Block {s.both('block')}  Dash {s.both('dash')}", W // 2, H - 40, STEEL, font, True)
            text(f"Skill 1 {s.both('cast')}  Skill 2 {s.both('cast2')}  Loot corpses: HOLD {s.both('interact')}", W // 2, H - 29, STEEL, font, True)
        if s.banner[1] > 0 and not s.tut: text(s.banner[0], W // 2, 78, GOLD, mid, True)
        s.draw_toasts()
        if s.state == "gear": s.draw_gear()
        if s.tut:
            title, lines, done, prog = s.tut_info()
            ls = [ln for t in lines for ln in wrap(t, 31)]
            h = 28 + len(ls) * 11 + (12 if prog else 0)
            pygame.draw.rect(main_cv, INK, (132, 4, 216, h)); pygame.draw.rect(main_cv, GOLD, (132, 4, 216, h), 1)
            text(f"{'STEP %d/8: ' % (s.step + 1) if s.step < 8 else ''}{title}", 240, 8, GOLD, font, True)
            for k, ln in enumerate(ls): text(ln, 138, 23 + k * 11)
            if prog: text(f"Progress: {prog}", 138, 23 + len(ls) * 11, CYAN)
            text("Esc = menu", W - 6, H - 12, STEEL_D, font, right=True)
            hot = SKIP_STATE["hot"]
            pygame.draw.rect(main_cv, INK, SKIP_RECT); pygame.draw.rect(main_cv, GOLD if hot else STEEL_D, SKIP_RECT, 1)
            text("SKIP TUTORIAL [TAB]", SKIP_RECT.centerx, SKIP_RECT.y + 3, GOLD if hot else WHITE, font, True)
        if s.state == "failed":
            main_cv.blit(DIM, (0, 0))
            title_text("DEFEATED", W // 2, 70, RED)
            text("Both heroes fell - no loot kept from this area!", W // 2, 130, WHITE, mid, True)
            text(f"Press Slash  P1 [{kn(0, 'slash')}]  P2 [{kn(1, 'slash')}]  to retry the area", W // 2, 160, STEEL, font, True)
        if s.state == "chest": s.draw_chest()
        if s.state == "loot":
            L = s.loot
            main_cv.blit(DIM, (0, 0))
            use(L["panel"]); L["m"].draw()
            if L["intro"] > 0:
                pygame.draw.rect(gfx.canvas, INK, (8, 24, 144, 142)); pygame.draw.rect(gfx.canvas, GOLD, (8, 24, 144, 142), 1)
                text(L["m"].title, 80, 32, GOLD, mid, True)
                for k, ln in enumerate(wrap(L["m"].hint, 21) + [""] + wrap(L["m"].ctrl(L["p"].i), 21) + [""] + wrap("Score 40%+ to win the loot!", 21)):
                    text(ln, 80, 62 + k * 12, WHITE if k < 3 else CYAN, font, True)
            elif L["m"].over:
                b = f" (+{int(L['m'].bonus * 100)}% class)" if L["m"].bonus else ""
                text(f"{int(L['m'].score * 100)}%{b}", 80, 154, GOLD if L["m"].score >= .4 else RED, font, True)
            text(f"P{L['p'].i + 1} {L['p'].cls}", 80, 165, P_COL[L["p"].i], font, True)
            use(main_cv)
            main_cv.blit(L["panel"], ((W - PW) // 2, (H - 180) // 2))
