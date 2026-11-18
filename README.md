# Rogue Loot

A 2-player local co-op, pixel-art action game built with Python and [pygame](https://www.pygame.org/). It was made for the November 2026 hackathon.

Two heroes fight through six castle levels. Each level has waves of enemies and ends with a boss. Beaten enemies drop corpses, and holding the loot key on a corpse starts a short loot mini-game. How well you do in the mini-game decides the rarity of the item.

- **Players:** 2, on the same keyboard
- **Internal resolution:** 480 x 270, scaled up to the window
- **Python:** 3.12 or newer
- **Dependencies:** `pygame >= 2.6` (dev: `pytest`, `ruff`)

---

## Quick start

The project uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # create .venv and install dependencies
uv run python main.py        # run the game
# or: .venv/bin/python main.py
```

Run the tests and the linter:

```bash
uv run pytest                # ~160 headless tests (logic, bosses, flow, full campaign playthrough)
uv run ruff check .          # lint (only E9 and F rules are enabled)
uv run python main.py --selftest      # headless smoke test of every screen, level, boss and cutscene
uv run python qa/run_qa.py            # whole QA gate: lint, tests, selftest, screenshots, balance -> qa/RESULTS.md
```

Developer mode (see [Developer mode](#developer-mode)):

```bash
uv run python main.py --dev          # menu gets "DEV: LEVEL SELECT"
uv run python main.py --level 3      # jump straight into level 3 (dev keys on)
uv run python main.py --gallery      # enemy gallery: Y spawns every enemy and boss in turn
```

## Controls

All keys can be rebound in **Settings**. Bindings are saved to `rogue_settings.json` in the project root. That file is git-ignored.

| Action | Player 1 | Player 2 |
|---|---|---|
| Move | `A` / `D` | `Left` / `Right` |
| Jump (press again for a double jump, or off a wall for a wall jump) | `W` | `Up` |
| Drop through platform / fast-fall | `S` | `Down` |
| Dash (ground and air) | `Left Shift` | `Right Shift` |
| Slash (attack) | `J` | `,` |
| Block (hold) | `K` | `.` |
| Skill 1 | `L` | `/` |
| Skill 2 | `U` | `M` |
| Loot a corpse or the holy chest (hold) | `E` | `Enter` |
| Skip the tutorial or a cutscene | `Tab` (or the on-screen button in the tutorial) | `Tab` |

**Menus:** `W`/`S` or `Up`/`Down` to move, `Enter` or `Space` to select, `Esc` to go back.

**Mechanics worth knowing**

- **Perfect block:** blocking just as a hit lands stuns the attacker (bosses are stunned only briefly). A normal block cuts the damage to 20%.
- **Down and revive:** a hero at 0 HP is "down". Both heroes are revived with 40% HP when a boss spawns and when it is defeated. If both heroes are down, all loot you have not banked in that area is lost.
- **Banking:** loot becomes permanent only when you take the portal to the next level.
- **Wall jump:** touching the arena's left or right edge while airborne lets you slide down and jump off it.

## Game flow

```
Menu ─┬─ Start ──► Class select ──► [intro card] Level 1 ──► [climb cutscene + intro card] Level 2 ... Level 6 ──► [ending] Victory
      ├─ Tutorial (also runs on first launch, before class select; Tab or the SKIP TUTORIAL button skips it)
      ├─ Settings (key rebinding)
      ├─ DEV: Level select (only with --dev)
      └─ Exit
```

Each level runs like this:

1. Enemies spawn in timed waves from the screen edges.
2. When the waves are cleared, the level's boss appears and all downed heroes are revived.
3. Defeating the boss opens a portal (usable after a 1.5 s grace period). Loot the corpses, then walk right into the portal.
4. A short cutscene shows the heroes climbing the castle to the next floor, then an intro card introduces the next level. Every cutscene can be skipped with `Tab`, `Esc`, or the slash key.

Class select lets each player pick a hero. Swap with the left/right keys, and toggle ready with the slash key. The game starts when both are ready.

## Developer mode

Start with `--dev` (or `ROGUE_DEV=1`, or `--level N` / `--gallery`). It is never saved to settings. The main menu gets **DEV: LEVEL SELECT** (warp to any level, the enemy gallery, and cutscene previews). In a level, `F1` shows this list:

| Key | Effect |
|---|---|
| `1`-`6`, `[` / `]` | warp to a level / previous / next |
| `N` | finish the level now (plays the climb cutscene) |
| `B` | spawn the boss now |
| `X` | kill everything |
| `G` | god mode |
| `V` | fly / noclip |
| `T` | cycle the difficulty tier (what the Threat multipliers are at) |
| `Y` | spawn the next enemy type (cycles through all enemies and bosses) |
| `C` | preview the cutscenes |
| `H` | hitboxes + FPS |

## Heroes

Defined in [game/classes.py](game/classes.py). Stats are derived in [game/player.py](game/player.py): max HP is `hp * 12 + 12`, attack is `8 + atk * 2`, and damage taken is reduced by `df * 4%`.

| Class | Role | HP / ATK / DEF | Skill 1 | Skill 2 | Mini-game bonus |
|---|---|---|---|---|---|
| Knight | Vanguard / Support | 8 / 6 / 7 | Holy Charge: invulnerable dash that slashes foes | Aegis Banner: heals nearby allies (+25 HP), knocks foes back | +8% in all mini-games |
| Tank | Juggernaut / Crowd Control | 10 / 4 / 10 | Earthquake Slam: AoE damage plus a 1.5s stun | Iron Taunt: pulls enemies in, gives a 30 HP barrier for 4s | +15% in Parry |
| Fighter | Relentless Bruiser | 7 / 9 / 4 | Whirlwind: 0.7s spin | Blade Wave: piercing crescent | +15% in Slash |
| Mage | Arcane Artillery | 4 / 10 / 2 | Fireball: explosive AoE | Frost Nova: damages and freezes for 2s | +15% in Dice Roll |
| Rogue | Mobile Assassin | 5 / 8 / 3 | Shadow Step: blink behind an enemy for a 2.4x backstab | Fan of Knives: 3 daggers in a spread | +15% in Lock Pick |

## Levels and bosses

Levels are data-driven (the `LEVELS` list in [game/levels.py](game/levels.py)). Bosses are defined in [game/bosses.py](game/bosses.py).

| # | Level | Waves | Boss | Boss HP |
|---|---|---|---|---|
| 1 | Castle Basement | 5 zombies, 3 skeletons | Rotting Gravekeeper | 600 |
| 2 | Overgrown Jungle | 3 bunnies, 2 wolfmen, 2 catmen, 2 wolves | Alpha Beastlord | 560 |
| 3 | Holy Cathedral | 6 knights | Paladin Commander (also has a **holy chest**) | 560 |
| 4 | Necropolis | 2 liches, 3 skeletons, 3 zombies | The Archlich | 560 |
| 5 | Mafia Penthouse | 4 gunmen, 2 wolves, 1 brute | The Don | 560 |
| 6 | Observatory Roof | 3 aliens, 3 drones, 2 wolves, 1 lich | Alien Tycoon (name set by `ALIEN_NAME` in `config.py`) | 640 |

**Bosses** run a pattern script: rest, then a telegraphed wind-up (the boss flashes), then the attack. Patterns unlock by phase (above 66% HP, above 33%, below that). Each phase change shows "ENRAGED!" and speeds the boss up.

**Difficulty scaling** (`difficulty()` in [game/config.py](game/config.py)): each level, enemies take 25% less damage and deal 25% more damage, compounding (level 6: enemies take x0.24 and deal x3.05). These values are `DMG_TAKEN_STEP` and `DMG_DEAL_STEP`. The HUD shows the current "Threat". Damage is never reduced below 1. **This curve is very steep: see [Known issues](#known-issues).**

**Enemy behaviours** are set by keys in `ESTATS` in [game/enemies.py](game/enemies.py): `hop`, `lunge`, `fly`, `ranged`, `summon`, `shield`, `dodge` and `climb`. To add an enemy, add an `ESTATS` entry, a sprite, and put it in a level's `waves`.

## Loot

Implemented in [game/loot.py](game/loot.py). Holding the loot key on a corpse opens a mini-game, picked at random:

| Mini-game | Idea |
|---|---|
| Dice Roll | Mash slash to shake the dice |
| Lock Pick | Find the sweet spot and hold steady |
| Slash the Loot | Swing in the direction the arrow points |
| Parry the Mimic | Strike when the mimic is in the green zone |

A score of 0.4 or higher gives an item. Failing loses the corpse's loot (in the tutorial you can retry). Boss corpses add +0.3 to the score.

Item rarity: **Common, Rare, Epic, Legendary**. Names are built from an adjective, an item (Sword, Shield, Helm, Boots, Ring, Amulet, Potion), and a mini-game suffix for non-common items.

**Holy chest (level 3):** after the Paladin falls, each player rolls their own class weapon and chooses to take or leave it. 75% of rolls are a holy weapon (+25% ATK). 25% are a cursed weapon (+70% ATK) with a drawback such as +30% damage taken, -20% max HP, or +40% skill cooldowns.

## Project layout

```
main.py                 Entry point and command-line flags (--dev, --level, --gallery, --selftest)
pyproject.toml          Project metadata, pytest and ruff config
uv.lock                 Locked dependencies
game/
  app.py                Game state machine (menu, settings, class select, cutscenes, levels, victory, dev menu) and the main loop
  arena.py              Gameplay scene: waves, boss flow, combat, enemy projectiles / hazards, skills, loot, holy chest, HUD, tutorial
  player.py             Player entity, physics, damage intake, gear (apply_gear)
  enemies.py            Enemy entity and data-driven AI (ESTATS)
  bosses.py             Boss pattern engine, six bosses, BOSS_HP
  classes.py            Hero class definitions
  levels.py             The six levels (data), procedural backgrounds, ambient particles
  cutscenes.py          Level intro card, castle-climb cutscene, ending
  devmode.py            Developer-mode keys and overlay
  loot.py               Loot mini-games, item rolling, holy chest weapons
  sprites.py            Procedural hero and enemy sprites
  sprites_extra.py      Procedural sprites for the castle-campaign enemies and bosses
  gfx.py                Surfaces, fonts, pixel-art drawing helpers
  inputs.py             Motion (per-player input abstraction) and make_motions() (where a controller plugs in)
  config.py             Constants, palette, settings / key binds, difficulty
  qabot.py              Scripted bots and FakeMotion for tests, --selftest and balance (not used by the real game)
  selftest.py           Headless smoke test behind --selftest
tests/                  pytest suite (headless)
qa/
  run_qa.py             Runs the whole QA gate and writes qa/RESULTS.md
  balance.py            Bot-driven balance report (win rate, boss time-to-kill)
  render_shots.py       Renders outcome screenshots to qa/shots/ (git-ignored)
  render_sprites.py     Renders a contact sheet of all sprites
  CHECKLIST.md          Requirement -> evidence map
  REPORT.md             Latest QA review report
.claude/agents/qa.md    QA agent definition
docs/controller-protocol.md   Plan for the Elegoo UNO + GY-521 controller
```

### Architecture notes

- **Pure pygame, no image assets.** All art is generated in code at startup, so the repo has no image files.
- **Fixed logical canvas.** The game draws to a 480x270 surface and scales it to the window.
- **Input abstraction.** Gameplay never reads the keyboard directly. It reads fields on a per-player `Motion` object (`axis`, `jump_p`, `slash_p`, `tilt`, `shake`, and so on). The class docstring in [game/inputs.py](game/inputs.py) lists them all. The plan is to support a physical motion controller (the GY-521 gyro/accelerometer board) by subclassing `Motion`.
- **Code style.** The code uses compact one-line statements and `s` as the self name. This is deliberate and ruff is configured to allow it (line length 160).

## Testing

`uv run pytest` runs about 160 headless tests (`SDL_VIDEODRIVER=dummy`, set in `tests/conftest.py`; every test uses a temporary settings file, so your real `rogue_settings.json` is never touched):

- `test_config`, `test_levels`: difficulty maths, settings robustness, level data and level rosters against the brief.
- `test_enemies`, `test_threats`, `test_bosses`: every enemy runs; shield, dodge, ranged, lunge, summon; projectiles, blocking, perfect-block reflect, hazards; every boss pattern in every phase; phases, boss death, portal.
- `test_chest`: 75 / 25 holy-or-cursed roll over 20,000 rolls, curse effects, take / leave flow, gear carried to the next level.
- `test_flow`: skip tutorial (key and click), cutscene flow, retry, victory, every dev-mode key.
- `test_cutscenes_input`: cutscenes finish and skip; `FakeMotion` has the same fields as `Motion`; gameplay modules never read the keyboard (the GY-521 seam).
- `test_campaign`: a bot plays the whole campaign through the real `Game` loop to the victory screen; and checks the content is winnable with the difficulty multipliers off.

`qa/balance.py` prints win rate, wave time and boss time-to-kill per level for scripted bots. The bots are only a rough proxy for a human.

The **QA agent** ([.claude/agents/qa.md](.claude/agents/qa.md)) reviews the code and the outcomes (including the screenshots) and writes `qa/REPORT.md`.

## Known issues

1. **The difficulty curve is very steep.** With the chosen compounding steps (x0.75 damage taken and x1.25 damage dealt per level), a careful scripted bot beats levels 1-2 but none of levels 3-6, although it beats 75-100% of every level with the multipliers off (`uv run python qa/balance.py 4 careful` vs `... --flat`). Bots are not humans, so playtest it. To soften it, change `DMG_TAKEN_STEP` and `DMG_DEAL_STEP` in [game/config.py](game/config.py): at 0.90 / 1.10 the same bot wins 40-75% of levels 2-5 (level 6 still 0%).
2. **The GY-521 controller is not built yet.** Only the input seam (`Motion`, `make_motions()`) and the plan in [docs/controller-protocol.md](docs/controller-protocol.md) exist. The Arduino sketch there is an untested outline.
3. **Enemy corpses are rotated sprites**, so tall enemies (bosses, liches) look odd lying down. Cosmetic.

### Bugs from v4 that were fixed on the way

- Looting a corpse crashed the game when it was drawn (negative colour tint, `ValueError: invalid color argument`).
- Enemies were drawn facing away from the player.
- A player standing at the right edge when an area cleared left the level instantly (now a 1.5 s grace period).
- `tutorial_done` was forgotten if the settings file had no key bindings.
- Damage could round down to 0 (now at least 1).

## Repository

Remote: <https://github.com/angel3matamoros-max/hackathon-nov2026.git>

Nothing has been pushed. The work after commit 55bb2a5 is uncommitted in the working tree. `qa/shots/`, `rogue_settings.json`, `.venv/` and caches are git-ignored.
