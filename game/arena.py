"""Gameplay scene (waves, combat, loot flow) and the tutorial."""
import math, random
import pygame
from . import gfx
from .config import *
from .gfx import (text, title_text, wrap, bar, gem, glow, blit_ent, lerp, use, world, main_cv, VIGNETTE, DIM, font, mid)
from .classes import CLASSES, bonus_for
from .sprites import HERO, ENEMY, CORPSE
from .levels import AREAS, AMB_N, get_bg, draw_torches, draw_runes
from .loot import MINIS, roll_loot, PW
from .player import overlap
from .enemies import Enemy


class Arena:
    def __init__(s, area, players, tut=False):
        s.area, s.A, s.players, s.tut = area, AREAS[area], players, tut
        s.plats = [(0, FLOOR, W)] + s.A["plats"]
        s.enemies, s.corpses, s.projs, s.parts, s.texts = [], [], [], [], []
        s.queue = [] if tut else sorted([random.uniform(1.0, 11.0), k] for k, n in s.A["kinds"] for _ in range(n))
        s.t, s.shake, s.state, s.result, s.loot, s.fail_t = 0.0, 0.0, "play", None, None, 0.0
        s.pending = [[] for _ in players]
        s.portal, s.kills, s.looted, s.dummy_hits = False, 0, 0, 0
        s.banner = [f"AREA {area + 1}/{len(AREAS)}: {s.A['name'].upper()}", 2.5]
        s.amb = [dict(x=random.random() * W, y=random.random() * FLOOR, p=random.random() * 6.28) for _ in range(AMB_N[area])]
        s.step, s.mark = -1, {}
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
        e = Enemy(kind, x, FLOOR - 70 if kind == "bat" else FLOOR, s.area, **kw)
        s.enemies.append(e); s.burst(x, e.y - 10, (200, 150, 255), 8, 60)

    def hurt(s, e, dmg, kb):
        if e.hp <= 0: return
        dmg = int(dmg)
        e.hp -= dmg; e.flash, e.kb = 0.12, kb
        if e.kind != "dummy": e.state, e.st = "rest", 0.3
        s.texts.append([e.x, e.y - e.d["h"] - 6, str(dmg), WHITE, 0.7]); s.burst(e.x, e.y - e.d["h"] / 2, (255, 240, 200), 6, 90)
        s.shake = max(s.shake, 2)
        if e.kind == "dummy": e.hp = 9999; s.dummy_hits += 1

    def kill(s, e):
        s.enemies.remove(e); s.kills += 1
        s.corpses.append(dict(x=e.x, y=FLOOR if e.kind == "bat" else e.y, kind=e.kind, tint=e.tint, hold=0.0, looted=False))
        s.burst(e.x, e.y - 10, (230, 230, 230), 16, 120); s.shake = 5

    def slash_hit(s, p, reach=34, dmg=None):
        x0, x1 = (p.x - 4, p.x + reach) if p.face > 0 else (p.x - reach, p.x + 4)
        for e in list(s.enemies):
            if id(e) not in p.hitset and overlap(x0, x1, p.y - 32, p.y + 2, e):
                p.hitset.add(id(e)); s.hurt(e, dmg or p.atk, p.face * 170)

    def hit_radius(s, x, y, r, dmg, kb=140):
        for e in list(s.enemies):
            if abs(e.x - x) <= r + e.d["w"] / 2 and abs((e.y - e.d["h"] / 2) - y) <= r + e.d["h"] / 2:
                s.hurt(e, dmg, (1 if e.x >= x else -1) * kb)

    # ---- Primary Skill (cast)
    def cast(s, p):
        c = p.cls
        p.cast_cd, p.casts, p.hitset = CLASSES[c]["cd"], p.casts + 1, set()
        if c == "Knight":
            p.skill, p.skill_t, p.inv = "charge", 0.22, max(p.inv, 0.3)
        elif c == "Tank":
            s.hit_radius(p.x, p.y - 10, 58, p.atk * 1.5, 200)
            for e in s.enemies:
                if abs(e.x - p.x) < 62 and e.kind != "dummy": e.stun = 1.5
            s.burst(p.x, p.y, (255, 220, 150), 26, 170); s.shake = 9
        elif c == "Fighter":
            p.skill, p.skill_t, p.tick = "whirl", 0.72, 0.0
        elif c == "Mage":
            s.projs.append(dict(kind="fire", x=p.x + 14 * p.face, y=p.y - 18, vx=255 * p.face, vy=0.0, dmg=p.atk * 1.75, life=1.6, pierce=False, hit=set()))
        else:  # Rogue Shadow Step
            tg = [e for e in s.enemies if abs(e.x - p.x) < 180]
            if not tg:
                p.cast_cd, p.casts = 0.4, p.casts - 1
                return
            e = min(tg, key=lambda e: abs(e.x - p.x))
            s.burst(p.x, p.y - 14, (150, 90, 220), 12, 90)
            p.x, p.y, p.vy, p.inv = max(10, min(W - 10, e.x - e.face * 20)), e.y, 0.0, 0.4
            p.face = 1 if e.x > p.x else -1
            s.burst(p.x, p.y - 14, (150, 90, 220), 12, 90); s.hurt(e, p.atk * 2.4, p.face * 160)

    # ---- Secondary Skill (cast2)
    def cast2(s, p):
        c = p.cls
        p.cast2_cd, p.casts2 = CLASSES[c]["cd2"], p.casts2 + 1
        if c == "Knight":  # Aegis Banner
            for ally in s.players:
                if not ally.down and abs(ally.x - p.x) < 95:
                    heal = min(ally.maxhp - ally.hp, 25)
                    ally.hp += heal
                    ally.inv = max(ally.inv, 0.6)
                    s.texts.append([ally.x, ally.y - 36, f"+{heal} HP", GREEN, 1.0])
            s.hit_radius(p.x, p.y - 14, 52, p.atk * 0.9, 220)
            s.burst(p.x, p.y - 16, GOLD, 24, 140); s.shake = 4
        elif c == "Tank":  # Iron Taunt
            p.shield, p.shield_t = 30.0, 4.0
            s.texts.append([p.x, p.y - 40, "+30 SHIELD", CYAN, 1.0])
            for e in s.enemies:
                if abs(e.x - p.x) < 140 and e.kind != "dummy":
                    e.kb = (1 if p.x > e.x else -1) * 180
                    e.stun = max(e.stun, 0.6)
            s.burst(p.x, p.y - 14, CYAN, 22, 130); s.shake = 5
        elif c == "Fighter":  # Blade Wave
            s.projs.append(dict(kind="wave", x=p.x + 14 * p.face, y=p.y - 16, vx=290 * p.face, vy=0.0, dmg=p.atk * 1.35, life=1.2, pierce=True, hit=set()))
            s.burst(p.x + 10 * p.face, p.y - 16, (180, 230, 255), 10, 80)
        elif c == "Mage":  # Frost Nova
            s.hit_radius(p.x, p.y - 14, 68, p.atk * 1.15, 90)
            for e in s.enemies:
                if abs(e.x - p.x) < 72 and e.kind != "dummy":
                    e.frozen = 2.0
            s.burst(p.x, p.y - 14, CYAN, 28, 160); s.shake = 5
        else:  # Rogue Fan of Knives
            p.vx = -p.face * 150
            p.vy = min(p.vy, -140)
            for vy in (-70, 0, 70):
                s.projs.append(dict(kind="knife", x=p.x + 10 * p.face, y=p.y - 16, vx=310 * p.face, vy=vy, dmg=p.atk * 0.85, life=0.75, pierce=False, hit=set()))
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
                "If you fail, you get NO loot and must retry!"
            ], s.looted > m["looted"], ""
        return "TUTORIAL COMPLETE", [
            "Clear all enemies in an area, loot corpses, then enter the portal.",
            "If both heroes fall, ALL unbanked loot from that area is lost!",
            f"Press {b('slash')} to continue"
        ], False, ""

    # ---- loot mini-game
    def start_loot(s, p, c):
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
                    it = roll_loot(m.kind, m.score)
                    s.pending[p.i].append(it)
                    s.texts.append([c["x"], c["y"] - 34, it["name"], RARITY[it["tier"]][1], 2.5])
                else:
                    c["hold"] = 0.0
                    if not s.tut:
                        c["looted"] = True
                    s.texts.append([c["x"], c["y"] - 34, "Failed - no loot!" + (" Try again!" if s.tut else ""), RED, 2.2])
                s.state, s.loot = "play", None

    # ---- update
    def fx(s, dt):
        for pt in s.parts[:]:
            pt[0] += pt[2] * dt; pt[1] += pt[3] * dt; pt[3] += 300 * dt; pt[4] -= dt
            if pt[4] <= 0: s.parts.remove(pt)
        for tx in s.texts[:]:
            tx[1] -= 18 * dt; tx[4] -= dt
            if tx[4] <= 0: s.texts.remove(tx)
        for m in s.amb:
            i = s.area
            if i == 0: m["y"] -= 4 * dt; m["x"] += math.sin(s.t + m["p"]) * 4 * dt
            elif i == 1: m["x"] += math.sin(s.t * .7 + m["p"]) * 14 * dt; m["y"] += math.cos(s.t * .9 + m["p"]) * 10 * dt
            elif i == 2: m["y"] -= (18 + m["p"] * 3) * dt; m["x"] += math.sin(s.t * 1.4 + m["p"]) * 8 * dt
            elif i == 3: m["y"] -= (25 + m["p"] * 4) * dt; m["x"] += math.sin(s.t + m["p"]) * 10 * dt
            elif i == 4: m["y"] += (20 + m["p"] * 3) * dt; m["x"] += math.sin(s.t + m["p"]) * 10 * dt
            else: m["y"] -= (8 + m["p"] * 2) * dt; m["x"] += math.cos(s.t * .8 + m["p"]) * 12 * dt
            if m["y"] < 0: m["y"] = FLOOR
            if m["y"] > FLOOR: m["y"] = 0
            m["x"] %= W

    def update(s, dt, mo):
        s.t += dt
        s.shake, s.banner[1] = max(0, s.shake - 30 * dt), s.banner[1] - dt
        s.fx(dt)
        if s.state == "loot": s.update_loot(dt, mo); return
        if s.state == "failed":
            s.fail_t += dt
            if s.fail_t > 0.8 and any(m.slash_p for m in mo): s.result = "retry"
            return
        for p in s.players: p.update(dt, mo[p.i], s)
        while s.queue and s.queue[0][0] <= s.t: s.spawn(s.queue.pop(0)[1])
        for e in s.enemies[:]:
            e.update(dt, s)
            if e.hp <= 0: s.kill(e)
        for pr in s.projs[:]:
            pr["x"] += pr["vx"] * dt
            pr["y"] += pr["vy"] * dt
            pr["life"] -= dt
            hits = [e for e in s.enemies if id(e) not in pr["hit"] and overlap(pr["x"] - 6, pr["x"] + 6, pr["y"] - 8, pr["y"] + 8, e)]
            if hits:
                if pr["kind"] == "fire":
                    s.projs.remove(pr)
                    s.hit_radius(pr["x"], pr["y"], 30, pr["dmg"], 160)
                    s.burst(pr["x"], pr["y"], (255, 160, 50), 20, 140); s.shake = 4
                    continue
                for e in hits:
                    pr["hit"].add(id(e))
                    s.hurt(e, pr["dmg"], (1 if pr["vx"] >= 0 else -1) * 130)
                if not pr["pierce"]:
                    s.projs.remove(pr)
                    s.burst(pr["x"], pr["y"], BLADE, 6, 70)
                    continue
            if pr["life"] <= 0 or not 0 < pr["x"] < W or not 0 < pr["y"] < FLOOR:
                if pr in s.projs:
                    if pr["kind"] == "fire":
                        s.hit_radius(pr["x"], pr["y"], 28, pr["dmg"], 160)
                        s.burst(pr["x"], pr["y"], (255, 160, 50), 20, 140)
                    s.projs.remove(pr)
        for c in s.corpses:
            if c["looted"]: continue
            who = [p for p in s.players if not p.down and mo[p.i].interact_h and abs(p.x - c["x"]) < 26 and abs(p.y - c["y"]) < 30]
            c["hold"] = c["hold"] + dt if who else max(0, c["hold"] - 2 * dt)
            if who and c["hold"] >= 0.5:
                s.start_loot(who[0], c)
                break
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
        else:
            if not s.queue and not [e for e in s.enemies if e.kind != "dummy"] and not s.portal:
                s.portal = True; s.banner = ["AREA CLEARED! Loot the corpses, then enter the portal >>", 4.0]
                for p in s.players:
                    if p.down: p.down, p.hp = False, p.maxhp * 0.4
            if s.portal and any(not p.down and p.x > W - 40 for p in s.players): s.result = "next"
            if all(p.down for p in s.players):
                s.state, s.pending = "failed", [[] for _ in s.players]

    # ---- draw
    def draw_hud(s):
        for p in s.players:
            x, d = (8 if p.i == 0 else W - 128), CLASSES[p.cls]
            text(f"P{p.i + 1} {p.cls}", x, 6, P_COL[p.i])
            bar(x, 19, 120, 7, p.hp / p.maxhp, RED if p.hp > p.maxhp * .3 else (255, 120, 40))
            if p.shield > 0:
                bar(x, 19, int(120 * min(1.0, p.shield / 30.0)), 3, 1.0, CYAN)
            cd1 = 1 - p.cast_cd / d["cd"]
            cd2 = 1 - p.cast2_cd / d["cd2"]
            bar(x, 30, 58, 4, cd1, CYAN if cd1 >= 1 else STEEL_D)
            bar(x + 62, 30, 58, 4, cd2, GOLD if cd2 >= 1 else STEEL_D)
            text(f"[{kn(p.i, 'cast')}] {d['skill'][:9]}", x, 37, WHITE if cd1 >= 1 else STEEL_D)
            text(f"[{kn(p.i, 'cast2')}] {d['skill2'][:9]}", x, 48, GOLD if cd2 >= 1 else STEEL_D)
            if not s.tut:
                text(f"Unbanked loot: {len(s.pending[p.i])}", x, 60, GOLD)
        if not s.tut:
            text(f"AREA {s.area + 1}/{len(AREAS)}: {s.A['name']}", W // 2, 6, WHITE, font, True)

    def draw(s):
        use(world)
        world.blit(get_bg(s.area), (0, 0))
        if s.area == 0: draw_torches(s.t)
        elif s.area == 5: draw_runes(s.t)
        for m in s.amb:
            col = [(150, 140, 180), (230, 240, 120), (140, 235, 250), (255, 150, 50), (255, 255, 255), (200, 150, 255)][s.area]
            if s.area == 1 and math.sin(s.t * 3 + m["p"]) > 0:
                glow(m["x"], m["y"], 8, (90, 100, 20))
            if s.area == 2:
                pygame.draw.circle(gfx.canvas, col, (int(m["x"]), int(m["y"])), 2, 1)
            else:
                pygame.draw.rect(gfx.canvas, col, (int(m["x"]), int(m["y"]), 2 if s.area else 1, 2 if s.area else 1))
        if s.portal:
            x, y = W - 28, FLOOR
            col = lerp((90, 60, 200), (160, 230, 255), 0.5 + 0.5 * math.sin(s.t * 4))
            pygame.draw.rect(gfx.canvas, INK, (x - 17, y - 56, 34, 56)); pygame.draw.circle(gfx.canvas, INK, (x, y - 56), 17)
            pygame.draw.rect(gfx.canvas, col, (x - 13, y - 56, 26, 56)); pygame.draw.circle(gfx.canvas, col, (x, y - 56), 13)
            glow(x, y - 40, 50, (60, 50, 120))
            text("NEXT AREA", W - 4, y - 90 + int(math.sin(s.t * 3) * 3), WHITE, font, right=True)
        for c in s.corpses:
            fr = CORPSE[(c["kind"], c["tint"] if c["kind"] == "slime" else 0)]
            blit_ent(fr, c["x"], c["y"], False, (-60, -60, -60) if c["looted"] else None)
            if not c["looted"]:
                gy = c["y"] - 26 + math.sin(s.t * 4 + c["x"]) * 3
                glow(c["x"], gy, 18, (110, 90, 30)); gem(int(c["x"]), int(gy), GOLD, 5)
                near = [p for p in s.players if not p.down and abs(p.x - c["x"]) < 26 and abs(p.y - c["y"]) < 30]
                if near: text(f"HOLD [{kn(near[0].i, 'interact')}]", c["x"], c["y"] - 50, P_COL[near[0].i], font, True)
                if c["hold"] > 0: bar(int(c["x"]) - 12, int(c["y"]) - 42, 24, 4, c["hold"] / 0.5, GOLD)
        ents = [(e.y, e) for e in s.enemies] + [(p.y, p) for p in s.players if not p.down]
        for _, o in sorted(ents, key=lambda z: z[0]):
            if isinstance(o, Enemy):
                fr = ENEMY[(o.kind, o.tint if o.kind == "slime" else 0)]
                sy = FLOOR if o.kind == "bat" else o.y
                pygame.draw.ellipse(gfx.canvas, (10, 8, 16), (o.x - 9, sy - 2, 18, 4))
                tint = (0, 90, 130) if o.frozen > 0 else ((110, 0, 0) if (o.state == "wind" and int(s.t * 14) % 2 == 0) else ((110, 110, 110) if o.flash > 0 else None))
                blit_ent(fr[int(o.anim * 6) % len(fr)], o.x, o.y, o.face > 0, tint)
                if o.frozen > 0:
                    pygame.draw.rect(gfx.canvas, CYAN, (int(o.x) - 8, int(o.y - o.d["h"]), 16, o.d["h"]), 1)
                elif o.state == "wind":
                    text("!", o.x - 2, o.y - o.d["h"] - 16, RED, mid)
                if o.hp < o.maxhp < 9000: bar(int(o.x) - 10, int(o.y - o.d["h"]) - 8, 20, 3, o.hp / o.maxhp, RED)
            else:
                pygame.draw.ellipse(gfx.canvas, (10, 8, 16), (o.x - 9, o.y - 2, 18, 4))
                if o.inv > 0 and o.dash_t <= 0 and int(s.t * 24) % 2: continue
                fr = HERO[o.cls][1][int(o.anim) % 8] if (o.ground and o.anim > 0) else (HERO[o.cls][0] if o.ground else HERO[o.cls][1][2])
                blit_ent(fr, o.x + (o.face * 3 if o.slash_t > 0 else 0), o.y, o.face < 0, (110, 110, 110) if o.flash > 0 else None)
                cx, cy = o.x, o.y - 17
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
        for pt in s.parts: pygame.draw.rect(gfx.canvas, pt[5], (int(pt[0]), int(pt[1]), pt[6], pt[6]))
        for tx in s.texts: text(tx[2], tx[0], tx[1], tx[3], font, True)
        use(main_cv)
        main_cv.fill(INK)
        main_cv.blit(world, (int(random.uniform(-1, 1) * s.shake), int(random.uniform(-1, 1) * s.shake)))
        main_cv.blit(VIGNETTE, (0, 0))
        s.draw_hud()
        if s.banner[1] > 0 and not s.tut: text(s.banner[0], W // 2, 78, GOLD, mid, True)
        if s.tut:
            title, lines, done, prog = s.tut_info()
            ls = [ln for t in lines for ln in wrap(t, 31)]
            h = 28 + len(ls) * 11 + (12 if prog else 0)
            pygame.draw.rect(main_cv, INK, (132, 4, 216, h)); pygame.draw.rect(main_cv, GOLD, (132, 4, 216, h), 1)
            text(f"{'STEP %d/8: ' % (s.step + 1) if s.step < 8 else ''}{title}", 240, 8, GOLD, font, True)
            for k, ln in enumerate(ls): text(ln, 138, 23 + k * 11)
            if prog: text(f"Progress: {prog}", 138, 23 + len(ls) * 11, CYAN)
            text("Esc = menu", W - 6, H - 14, STEEL_D, font, right=True)
        if s.state == "failed":
            main_cv.blit(DIM, (0, 0))
            title_text("DEFEATED", W // 2, 70, RED)
            text("Both heroes fell - no loot kept from this area!", W // 2, 130, WHITE, mid, True)
            text(f"Press Slash  P1 [{kn(0, 'slash')}]  P2 [{kn(1, 'slash')}]  to retry the area", W // 2, 160, STEEL, font, True)
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
