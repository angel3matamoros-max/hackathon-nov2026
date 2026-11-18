# Rogue Loot

A 2-player local co-op, pixel-art action game built with Python and [pygame](https://www.pygame.org/). It was made for the November 2026 hackathon.

One or two heroes fight through six castle levels. Each level has waves of enemies and ends with a boss. Some beaten enemies drop a lootable corpse, and holding the loot key on it starts a short loot mini-game. How well you do decides the rarity of the **gear** (weapon, armor or charm) you win. Gear has real bonuses that you can see on pickup and on the Gear screen.

- **Players:** 1 (with a CPU ally) or 2, on the same keyboard
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

## Hand controller (optional)

The ELEGOO MEGA 2560 hand controller (joystick, two buttons, a stick click, and an accelerometer) drives **player 1** when it is plugged in. The game finds it automatically (`/dev/cu.usbmodem*`) and prints its status. The keyboard keeps working alongside it. `ROGUE_PAD=0` turns it off, and `ROGUE_PAD_PORT=/dev/...` picks another port.

Run `.venv/bin/python main.py --pad-monitor` to see the raw values and every gesture, and to tune the thresholds. The full mapping, how the gestures work, and how to tune them are in [docs/controller-protocol.md](docs/controller-protocol.md).

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
| Gear screen (pauses the game, works in the tutorial too) | `I` | `O` |

*Hand controller (player 1 when plugged in): stick = walk and jump (up) and drop (down), stick click = dash, button 1 / 2 = skills, a swing = attack, hold the pad up = shield, a shove = interact.*
| Skip the tutorial or a cutscene | `Tab` (or the on-screen button in the tutorial) | `Tab` |

**Menus:** `W`/`S` or `Up`/`Down` to move, `Enter` or `Space` to select, `Esc` to go back.

**Mechanics worth knowing**

- **Perfect block:** blocking just as a hit lands stuns the attacker (bosses are stunned only briefly). A normal block cuts the damage to 20%.
- **Down and revive:** a hero at 0 HP is "down". Both heroes are revived with 40% HP when a boss spawns and when it is defeated. If both heroes are down, all loot you have not banked in that area is lost.
- **Banking:** loot becomes permanent only when you take the portal to the next level.
- **Wall jump:** touching the arena's left or right edge while airborne lets you slide down and jump off it.

## Castle Maker

From the main menu choose **CASTLE MAKER**. It lists the castles you have saved (plus a **+ NEW CASTLE** row).

- **Enter** on a castle plays it. **E** edits it. Invalid castles are marked and show the reason.
- In the editor, **W/S** moves between rows, **A/D** (or the arrows) changes the value, and **Enter** does the row's action. The name row needs Enter to start typing and Enter again to finish.
- A castle has **1 to 10 levels**. Each level has a **theme** (Basement, Jungle, Cathedral, Necropolis, Penthouse, Observatory), a **platform layout** (A, B, C or none), a **boss** (or none, in which case clearing the waves opens the portal), and **1 to 8 waves**. Each wave is one kind of enemy with a count from 1 to 5.
- **TEST this level** plays that one level and returns to the editor. **SAVE** writes the castle to the `castles/` folder. **PLAY** saves and then plays the whole castle.
- A castle plays straight through, with no cutscenes. Difficulty rises with the level number (a 10-level castle is spread across the same six difficulty steps).

Saved castles are JSON files in `castles/`. That folder is git-ignored, except `castles/examples/`, which ships with a starter castle.

## Game flow

```
Menu ─┬─ Start ──► 1 or 2 players ──► Class select ──► [intro card] Level 1 ──► [climb cutscene + intro card] Level 2 ... Level 6 ──► [ending] Victory
      ├─ Tutorial (also runs on first launch, before class select; Tab or the SKIP TUTORIAL button skips it)
      ├─ Settings (key rebinding)
      ├─ DEV: Level select (only with --dev)
      └─ Exit
```

Each level runs like this:

1. Enemies come in **waves**, one after another ("WAVE 2/3"). The next wave starts about 2.5 s after you clear the previous one. Foes spawn staggered from the screen edges, at most 8 alive at a time. Sometimes a cleared wave leaves a **supply cache** (35%, never after the last wave) that you can loot like a corpse.
2. When the last wave is cleared, the level's boss appears and all downed heroes are revived.
3. Defeating the boss opens a portal (usable after a 1.5 s grace period). Loot the corpses, then walk right into the portal.
4. A short cutscene shows the heroes climbing the castle to the next floor, then an intro card introduces the next level. Every cutscene can be skipped with `Tab`, `Esc`, or the slash key.

Class select lets each player pick a hero. Swap with the left/right keys, and toggle ready with the slash key. The game starts when both are ready.

**Solo mode:** after Start, choose **1 PLAYER** or **2 PLAYERS** (remembered for next time). In solo mode player 2 is a CPU **assistant** ([game/ally.py](game/ally.py)). After you ready up, your keys also pick the ally's class (a complementary one is pre-selected). The assistant stays near you, fights what is close to you, and reacts to a boss's wind-up only after a short delay. Its hits are weaker and its skills come rarely. It never loots corpses (those are yours). It takes a boss-chest item only after you have chosen. It never opens a mini-game or modal, so it can never block you.

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

| # | Level | Waves (kind x count) | Boss | Boss HP |
|---|---|---|---|---|
| 1 | Castle Basement | 3 zombies / 2 zombies + 1 skeleton / 2 skeletons | Rotting Gravekeeper | 600 |
| 2 | Overgrown Jungle | 2 bunnies + 1 wolf / 2 wolfmen + 1 catman / bunny + catman + wolf | Alpha Beastlord | 560 |
| 3 | Holy Cathedral | 3 waves of 2 knights | Paladin Commander (boss chest has the **holy weapon**) | 560 |
| 4 | Necropolis | 2 skeletons + zombie / lich + 2 zombies / lich + skeleton | The Archlich | 560 |
| 5 | Mafia Penthouse | 2 gunmen / 2 wolves + gunman / gunman + brute | The Don | 560 |
| 6 | Observatory Roof | 3 drones / 2 aliens + wolf / alien + wolf + lich | Alien Tycoon (name set by `ALIEN_NAME` in `config.py`) | 640 |

**Bosses** are big (about 2.5x the size of a hero, with a cape, mane, halo or saucer drawn on top) and enter from the right with a name card, immune for about 2 s. They run a pattern script: rest, then a telegraphed wind-up (the boss flashes), then the attack. Patterns unlock by phase (above 66% HP, above 33%, below that). Each phase change shows "ENRAGED!" and speeds the boss up. A status line under the boss's health bar tells you what to do. Every boss has a signature mechanic built on **props** (breakable objects, [game/props.py](game/props.py)):

| Boss | Signature mechanic |
|---|---|
| Rotting Gravekeeper | "Raise" pushes up gravestones with a countdown bar. Break them in 4 s or a zombie rises from each. Grave hands (green warning) **root** a hero for 1.2 s (a dash breaks free). The slam sends a ground shockwave to jump. |
| Alpha Beastlord | **Chain-charge**: he runs until he hits a hero or the wall. A wall hit leaves him **dazed** for 1.8 s (hit him now). The howl calls wolves and starts a 6 s **moon rage** (faster). |
| Paladin Commander | Held by 3 orbiting **aegis orbs**: while any lives he takes only 10% damage. Break them to expose him. The "guard" move re-forms the aegis. Holy pillars rain down. |
| The Archlich | **Immune** while his crystals stand. Each crystal you shatter staggers him and makes him blink. When a phase starts the crystals reform. |
| The Don | A bulletproof vest (takes 60% damage) except during the 2.2 s **reload** after a burst. Crates are **cover** that soak bullets (dynamite wrecks them). |
| Alien Tycoon | A **tractor beam** lifts heroes under the saucer (walk or dash sideways to escape; getting pulled to the top hurts). Lasers, rockets, drones. While 2+ drones live he takes half damage. |

**Difficulty scaling** (`difficulty()` in [game/config.py](game/config.py)): each level, enemies take 25% less damage and deal 25% more damage, compounding (level 6: enemies take x0.24 and deal x3.05). These values are `DMG_TAKEN_STEP` and `DMG_DEAL_STEP`. The HUD shows the current "Threat". Damage is never reduced below 1. **This curve is very steep: see [Known issues](#known-issues).**

**Enemy behaviours** are set by keys in `ESTATS` in [game/enemies.py](game/enemies.py): `hop`, `lunge`, `fly`, `ranged`, `summon`, `shield`, `dodge` and `climb`. To add an enemy, add an `ESTATS` entry, a sprite, and put it in a level's `waves`.

## Loot and gear

Implemented in [game/loot.py](game/loot.py) (mini-games, holy chest) and [game/items.py](game/items.py) (items).

**Drops.** Not every enemy leaves loot. Each enemy type has a drop chance (weak fodder 10-30%, elites such as the brute, knight and wolfman 45-60%, bosses always). Foes that do not drop leave a plain corpse. Cleared waves sometimes leave a supply cache.

**Looting.** Holding the loot key on a gem-marked corpse opens a mini-game, picked at random:

| Mini-game | Idea |
|---|---|
| Dice Roll | Mash slash to shake the dice |
| Lock Pick | Find the sweet spot and hold steady |
| Slash the Loot | Swing in the direction the arrow points |
| Parry the Mimic | Strike when the mimic is in the green zone |

A score of 0.4 or higher gives an item. Failing loses that corpse's loot (in the tutorial you can retry). Boss corpses and caches add +0.3 to the score.

**Items are gear.** Every item has a slot (**Weapon, Armor, Charm**), a rarity (**Common, Rare, Epic**, and **Legendary** which only bosses give), and real effects written out in plain words:

| Slot | Main effect | Possible perks (Rare and up) |
|---|---|---|
| Weapon | +6% to +32% ATK | crit chance (hits deal x2), lifesteal |
| Armor | more max HP, less damage taken | thorns (reflect damage to attackers), +move speed |
| Charm | shorter skill cooldowns | lifesteal, +speed, a wider perfect-block window, crit |

A popup shows the name, the effects and "EQUIPPED". A better item (by a simple power score) equips automatically, and a worse one is bagged. Effects from the three slots stack. Press the Gear key (`I` / `O`) to open the Gear screen (it pauses) for every effect, plus your total ATK, HP and cooldowns. If both heroes fall, the gear found in that area is lost and you go back to what you had at the start of the area. Gear becomes permanent when you take the portal.

**Boss chest (every boss).** A boss drops no corpse. It drops a chest instead. Each hero holds the loot key on it and then picks **one of three** epic-or-better items (one weapon, one armor, one charm; boss-only **Legendary** items can appear) or leaves. The pick is equipped at once. The chest can be opened once per hero. The CPU ally takes the strongest item that is not cursed.

**Holy chest (level 3):** the Paladin's chest has the hero's **class holy weapon** as its weapon card. 75% of rolls are a blessed weapon (+25% ATK). 25% are a cursed weapon (+70% ATK) with a drawback such as +30% damage taken, -20% max HP, or +40% skill cooldowns, shown on the card before you choose.

## Project layout

```
main.py                 Entry point and command-line flags (--dev, --level, --gallery, --selftest)
pyproject.toml          Project metadata, pytest and ruff config
uv.lock                 Locked dependencies
game/
  app.py                Game state machine (menu, settings, class select, cutscenes, levels, victory, dev menu) and the main loop
  arena.py              Gameplay scene: waves, boss flow, combat, enemy projectiles / hazards, skills, loot, holy chest, HUD, tutorial
  player.py             Player entity, physics, damage intake, equipped gear (equip / recompute)
  enemies.py            Enemy entity and data-driven AI (ESTATS)
  bosses.py             Boss pattern engine, six bosses, BOSS_HP
  classes.py            Hero class definitions
  levels.py             The six levels (data), procedural backgrounds, ambient particles
  cutscenes.py          Level intro card, castle-climb cutscene, ending
  devmode.py            Developer-mode keys and overlay
  items.py              Gear: slots, rarities, effects, item rolling and descriptions
  loot.py               Loot mini-games, holy chest weapons
  padbridge.py          Hand controller: serial reader thread, gesture logic (PadState), PadMotion, --pad-monitor
  castle.py             Castle Maker data: validation, building levels, saving and loading castles
  maker.py              Castle Maker editor (rows and values) and its screens
  scroll.py             Floor, pit and camera helpers for side-scrolling levels (not wired in yet)
  props.py              Breakable boss-fight objects (gravestones, crystals, aegis orbs, crates)
  ally.py               CPU ally for solo play (AllyMotion + Ally brain)
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
docs/controller-protocol.md   The hand controller: wire format, mapping, gestures and how to tune them
```

### Architecture notes

- **Pure pygame, no image assets.** All art is generated in code at startup, so the repo has no image files.
- **Fixed logical canvas.** The game draws to a 480x270 surface and scales it to the window.
- **Input abstraction.** Gameplay never reads the keyboard directly. It reads fields on a per-player `Motion` object (`axis`, `jump_p`, `slash_p`, `tilt`, `shake`, and so on). The class docstring in [game/inputs.py](game/inputs.py) lists them all. The hand controller is a `Motion` subclass (`PadMotion` in [game/padbridge.py](game/padbridge.py)).
- **Code style.** The code uses compact one-line statements and `s` as the self name. This is deliberate and ruff is configured to allow it (line length 160).

## Testing

`uv run pytest` runs about 160 headless tests (`SDL_VIDEODRIVER=dummy`, set in `tests/conftest.py`; every test uses a temporary settings file, so your real `rogue_settings.json` is never touched):

- `test_config`, `test_levels`: difficulty maths, settings robustness, level data and level rosters against the brief.
- `test_enemies`, `test_threats`, `test_bosses`: every enemy runs; shield, dodge, ranged, lunge, summon; projectiles, blocking, perfect-block reflect, hazards; every boss pattern in every phase; phases, boss death, portal.
- `test_chest`: 75 / 25 holy-or-cursed roll over 20,000 rolls, curse effects, take / leave flow, gear carried to the next level.
- `test_flow`: skip tutorial (key and click), cutscene flow, retry, victory, every dev-mode key.
- `test_cutscenes_input`: cutscenes finish and skip; `FakeMotion` has the same fields as `Motion`; gameplay modules never read the keyboard (the input seam).
- `test_padbridge`: the hand controller's logic on recorded sample streams (calibration, debounce, hysteresis, swings, shove, shield, menu keys), without hardware.
- `test_campaign`: a bot plays the whole campaign through the real `Game` loop to the victory screen; and checks the content is winnable with the difficulty multipliers off.

`qa/balance.py` prints win rate, wave time and boss time-to-kill per level for scripted bots. The bots are only a rough proxy for a human.

The **QA agent** ([.claude/agents/qa.md](.claude/agents/qa.md)) reviews the code and the outcomes (including the screenshots) and writes `qa/REPORT.md`.

## Known issues

1. **The difficulty curve falls off a cliff at levels 5-6.** With the chosen compounding steps (x0.75 damage taken and x1.25 damage dealt per level, level 6 = x0.24 / x3.05), a careful scripted bot wins 100% of levels 1-4 but only about 8% of level 5 and 25% of level 6 (`uv run python qa/balance.py 4 careful`). With the multipliers off it wins 100% of every level. Bots are not humans, so playtest levels 4-6. To soften it, change `DMG_TAKEN_STEP` and `DMG_DEAL_STEP` in [game/config.py](game/config.py): at 0.85 / 1.15 the bot wins 75-83% of levels 5-6, at 0.90 / 1.10 it wins 100% / 91%.
2. **Not built yet:** the side-scrolling Mario-style levels (levels 1-3 are still one-screen arenas; [game/scroll.py](game/scroll.py) has the helpers ready) and the castle-maker "free placement" mode (the maker is a wave composer only). The Gear screen and the boss chest are keyboard-only menus.
3. **Minor QA nits left open:** the class-select title overlaps the role labels, the boss name and status text are hard to read over busy backgrounds, and "RESISTED" overlaps damage numbers. Thorns also reflect bullets (the description does not say so).
4. **Hand controller gestures are untuned.** The board reads correctly, but the thresholds are first guesses. Use `--pad-monitor`, then the table in [docs/controller-protocol.md](docs/controller-protocol.md).
3. **Minor open QA notes** (Esc leaves a level without asking, a few overlapping labels, menus assume a keyboard): see [qa/REPORT.md](qa/REPORT.md).

### Bugs from v4 that were fixed on the way

- Looting a corpse crashed the game when it was drawn (negative colour tint, `ValueError: invalid color argument`).
- Enemies were drawn facing away from the player.
- A player standing at the right edge when an area cleared left the level instantly (now a 1.5 s grace period).
- `tutorial_done` was forgotten if the settings file had no key bindings.
- Damage could round down to 0 (now at least 1).

## Repository

Remote: <https://github.com/angel3matamoros-max/hackathon-nov2026.git>

`main` is pushed to origin (commit f7fe0b1). The QA fixes made after that commit are uncommitted in the working tree. `qa/shots/`, `rogue_settings.json`, `.venv/` and caches are git-ignored.
