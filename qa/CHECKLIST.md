# QA checklist: requirements -> evidence

Status values: PASS / FAIL / NOT VERIFIED. The QA agent (`.claude/agents/qa.md`) fills the Status and Evidence columns in `qa/REPORT.md`.
Run everything with `.venv/bin/python qa/run_qa.py`.

| # | Requirement (from the brief) | How it is verified |
|---|---|---|
| 1 | Skip-tutorial button | `tests/test_flow.py::test_skip_tutorial_by_mouse_click_on_button`, `..._by_key`, `test_skip_button_is_drawn_during_tutorial`; `qa/shots/tutorial_skip_button.png`; `--selftest` |
| 2a | New enemies after the tutorial: wolf | `tests/test_levels.py::test_spec_level_rosters`, `test_enemies.py` (lunge), `qa/shots/sprites.png` |
| 2b | Lich skeleton | `test_enemies.py::test_lich_summons_skeletons_up_to_cap`, sprite sheet |
| 2c | Mafia gunmen | `test_enemies.py::test_gunman_keeps_distance_and_fires_blockable_bullets`, `test_threats.py` (bullets, block, reflect), sprite sheet |
| 2d | Elon Musk as the alien from space (name in `config.ALIEN_NAME`) | `test_bosses.py::test_boss_kind_names_and_alien_name_constant`, `qa/shots/level6_boss_*.png` |
| 3a | New levels with a boss at the end | `test_bosses.py::test_boss_per_level_matches_data`, `test_boss_spawns_only_after_all_waves_cleared`, `test_portal_waits_for_boss`, every-pattern tests, `qa/shots/level*_boss_*.png` |
| 3b | Next level: enemy damage reduction +25%, +25% damage to players (compounding, small steps) | `test_config.py` (difficulty), `test_enemies.py::test_difficulty_scales_enemy_damage_dealt`, `test_enemy_damage_taken_reduced_per_level_and_floor_of_one`; HUD shows "Threat" |
| 4 | Developer mode to move around all levels | `test_flow.py` dev tests (menu, number keys, brackets, boss, kill, god, fly, tier, spawn, cutscene preview, gallery), `qa/shots/dev_menu.png`, `dev_help.png` |
| 5a | Simple cutscene at the beginning of every level | `test_flow.py::test_class_select_leads_to_intro_cutscene_then_level_one`, `test_cutscenes_input.py`, `qa/shots/cutscene_intro_1.2.png` |
| 5b | Beating a boss = moving up the castle in a cutscene | `test_flow.py::test_finishing_a_level_plays_ascend_then_intro_then_next_level`, `qa/shots/cutscene_ascend_*.png` |
| 6.1 | Level 1: tutorial-like castle basement, simple weak zombies and skeletons | `test_levels.py::test_spec_level_rosters`, `test_level1_zombies_are_weak`, `qa/shots/level1_fight.png` (control hints visible) |
| 6.2 | Level 2: nature-infested jungle, bunny / wolf / cat beast men | rosters test, `qa/shots/level2_*.png` |
| 6.3 | Level 3: holy knights; boss drops a chest: 75% class holy weapon / 25% much stronger cursed weapon; player chooses whether to take it | `test_chest.py` (75/25 over 20k rolls, curse effects, take/leave flow, gear carried), `test_enemies.py` (knight shield), `qa/shots/chest_holy.png`, `chest_cursed.png` |
| 6.4-6.6 | Levels 4-6 (Necropolis, Mafia Penthouse, Observatory Roof) | rosters test, screenshots |
| 7 | Keyboard now, custom controller later (GY-521) without rewriting gameplay | `test_cutscenes_input.py::test_game_code_reads_only_motion_fields`, `test_fake_motion_has_the_same_interface_as_motion`, `docs/controller-protocol.md` |
| 8 | The whole campaign can be completed | `tests/test_campaign.py` (full playthrough through the real Game loop), `--selftest` |
| 9 | Content is winnable; difficulty ramps | `test_campaign.py::test_content_is_winnable_with_multipliers_off`, `qa/balance.py` (see the report's balance section) |
| 10 | v5-1: not every enemy drops loot, only some, sometimes at wave end | `tests/test_loot_system.py::test_drops_are_partial_and_elites_drop_more`, `test_cache_can_appear_between_waves`, `test_tutorial_and_bosses_always_drop` |
| 11 | v5-2: choose 1 player (CPU ally) or 2 players | `tests/test_solo.py` (screen flow, persistence, ally follows / fights / never blocks, full level with a bot + ally), `qa/shots/players_screen.png`, `solo_class_select.png` |
| 12 | v5-3: levels go by waves | `test_bosses.py::test_boss_spawns_only_after_all_waves_cleared`, `test_next_wave_waits_for_the_previous_one_to_be_cleared`, `test_levels.py` (>= 3 waves per level) |
| 13 | v5-4: bigger, better-looking bosses with cooler mechanics | `tests/test_boss_mechanics.py` (entrance, gravestones + grab, wall-daze charge, aegis orbs, crystals, cover + reload, tractor beam, props), `qa/shots/boss*_mechanic.png`, `boss*_entrance.png`, `sprites.png` |
| 14 | v5-5: looted abilities are understandable | `tests/test_loot_system.py` (items have slot / tier / effects / description, stacking, auto-equip, perks work in combat, defeat restores gear), `qa/shots/loot_popup.png`, `gear_screen.png`; tutorial text |
| 15 | v5-6: bosses drop much better loot | `tests/test_chest.py::test_boss_chest_offers_three_epic_or_better_items_one_per_slot`, `test_chest_take_equips_leave_keeps_and_cannot_roll_twice`, `qa/shots/boss_chest_modal.png` |
| 16 | v5-7: board is the ELEGOO MEGA 2560 | `docs/controller-protocol.md` (pins 20 / 21 for I2C) |
