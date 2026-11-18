# QA report: Rogue Loot (castle campaign build)

Review by the QA agent (an independent reviewer following `.claude/agents/qa.md`), saved here by the developer because the reviewer's tool could not write files.
The "Resolution" column was added afterwards by the developer. Numbers marked *(re-measured)* were re-run after the fixes.

**Verdict at review time: SHIP WITH NOTES.** No blockers, no crashes. Every checklist requirement was implemented and exercised.

## 1. Automated gate (at review time)

| Step | Result |
|---|---|
| `ruff check .` | All checks passed (weak evidence, see N5) |
| `pytest` | 163 passed, 0 failed (two runs) |
| `main.py --selftest` | 30 ok, 0 FAIL |
| `qa/render_shots.py` + `render_sprites.py` | 32 PNGs, all viewed |
| `main.py --level 3 / --gallery / --dev / --level 99 / ROGUE_DEV=1` | each ran 4 s, no traceback |
| Fuzz: 12 seeds, ~72,000 frames, random dev keys, random dt (20/30/60 Hz), random inputs, drawing every frame | 0 exceptions |
| Cost | update + draw about 0.35 ms per frame headless |

## 2. Requirements

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Skip-tutorial button | PASS | 3 flow tests, `tutorial_skip_button.png`; Tab works through the real `Motion` |
| 2a-d | Wolf, lich, mafia gunmen, "Elon Musk" alien | PASS | sprite sheet, level shots, lunge / summon / bullet-block-reflect tests. Note: a real person's name is on an enemy, as requested; it lives in `config.ALIEN_NAME` |
| 3a | 6 levels, each ending in a boss | PASS | per-level boss test, 18 every-pattern cases, 18 boss shots, selftest kills every boss |
| 3b | Per level enemies take 25% less / deal 25% more, compounding | PASS, with a caveat | `difficulty()` = 0.75^n / 1.25^n; every damage path scales exactly once. See balance |
| 4 | Developer mode | PASS | all dev keys tested; dev screens viewed; dev keys do nothing during cutscenes |
| 5a/b | Cutscenes at level start and climbing the castle after a boss | PASS | flow tests, cutscene shots |
| 6.1-6.6 | Level rosters, holy chest 75/25, player chooses | PASS | roster test; 40,000 rolls gave a cursed rate of 0.250; Take/Leave works, modal state does not leak |
| 7 | Gameplay reads only `Motion` | PASS for gameplay, NOT VERIFIED for hardware | seam test + grep; menus and the skip click still use keyboard/mouse (N7); no GY-521 code exists |
| 8 | Campaign completable | PASS (god mode) | full campaign test and selftest reach victory through the real `Game` loop |
| 9 | Content winnable; difficulty ramps | PASS (re-measured) | see section 4 |

v4 fixes (negative-tint crash, enemy facing, portal grace, `tutorial_done`, damage floor) all hold.

## 3. Defects

| ID | Sev | Finding | Resolution |
|---|---|---|---|
| M1 | major | Balance bot starved player 2 at 30 Hz (`int(t*60) % N` timers): `game/qabot.py`, `qa/balance.py:18`. Published win rates were biased low | **Fixed**: per-player real timers. Balance re-measured below |
| M2 | major (design) | The approved 0.75/1.25 curve is steep | **Open, owner decision.** See section 4: after the M1 fix it is a cliff at levels 5-6, not level 3 |
| D1 | minor | `int()` truncation of damage taken shaved up to 21% extra off weak hits at high tiers (`arena.py` `hurt`) | **Fixed**: rounds |
| D2 | minor | Holy chest line "A blessed weapon. No strings attached." clipped (appears in 75% of offers) | **Fixed**: shorter text |
| D3 | minor | Revive set float HP; popup read `+24.799999999999997 HP` | **Fixed**: integer HP on revive |
| D4 | minor | A boss's summon updating after the boss died could still fire one shot | **Fixed**: enemies with hp <= 0 no longer update |
| D5 | minor | Jump height depended on frame rate (`player.py` jump cut was per frame) | **Fixed**: cut scaled by dt |
| D6 | minor | Wide corpses (wolf) were rotated upright and looked like a key | **Fixed**: only tall corpses rotate |
| D7 | minor | HUD skill names truncated mid-word | **Fixed**: full names (they fit) |
| D8 | minor (design) | Esc abandons the level with no confirmation | **Open** |
| N1 | nit | "ENRAGED!" can flash on the boss's death frame | **Fixed** by the D4 change (dead enemies do not update) |
| N2 | nit | Some overlapping / clipped labels ("HOLD [E]" at the edge, doubled BLOCKED/REFLECTED, Threat line over the L5 window, dev help over the banner) | Open, cosmetic |
| N3 | nit | Drawing consumes the global RNG, so seeded runs differ with/without drawing | Open |
| N4 | nit | Dead/duplicated code (`FLYERS`, tint only matters for slimes, ATK formula repeated 3x, garbled comment) | `FLYERS` removed; rest open |
| N5 | nit | ruff only checks `E9,F` and ignores `F403,F405` because of `from .config import *` | Open |
| N6 | nit | `"false"` in the settings file loaded as True | **Fixed** |
| N7 | nit | Menus, settings, skip click and key-name labels assume a keyboard; need `Motion` equivalents for the GY-521 | Open (later stage) |
| N8 | nit | Enter dismisses the victory screen and is P2's loot key | Open |
| N9 | nit | Dev key N inside the gallery leaves the gallery | Open |
| N10 | nit | Dev tier override persists across menu round-trips | Open |

## 4. Balance *(re-measured after the M1 fix; careful bot, 3 teams x 4 seeds per level)*

| | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---|---|---|---|---|---|
| Multipliers off, win % | 100 | 100 | 100 | 100 | 100 | 100 |
| Approved curve 0.75 / 1.25, win % | 100 | 100 | 100 | 100 | 8 | 25 |
| Curve 0.80 / 1.20, win % | 100 | 100 | 100 | 100 | 66 | 58 |
| Curve 0.85 / 1.15, win % | 100 | 100 | 100 | 100 | 75 | 83 |
| Curve 0.90 / 1.10, win % | 100 | 100 | 100 | 100 | 100 | 91 |

- Content on its own is fine. Boss time-to-kill with the approved curve grows from 8 s (L1) to 55 s (L6).
- The approved curve is comfortable through level 4 and then falls off a cliff at levels 5-6. Per the reviewer, enemy hits at L5/L6 take 40-67% of a Mage's HP (a Mage dies in two hits on L6).
- Bots are only a rough proxy for a human: they do not kite, use platforms or combo skills. A human playtest of levels 4-6 is still needed. Tune with `DMG_TAKEN_STEP` / `DMG_DEAL_STEP` in `game/config.py`.
- Earlier numbers in this repo (100/58/0/0/0/0) came from the M1 bot bug and should not be used.

## 5. Not verified
- Anything on a real display, real audio, or a physical keyboard/mouse (the skip-button mouse mapping was checked with synthetic events only).
- GY-521 hardware and the Arduino sketch.
- Human difficulty and fun; the feel of the four loot mini-games.
- What wrote `rogue_settings.json` in the repo root (it is git-ignored; tests and QA scripts do not touch it).
