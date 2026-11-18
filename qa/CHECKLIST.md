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
