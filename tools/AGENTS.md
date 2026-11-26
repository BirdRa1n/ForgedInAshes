# AGENTS.md — `tools/`

Read the [root AGENTS.md](../AGENTS.md) first.

PowerShell and Python scripts that build, install, validate and generate the mod. Shared Python helpers (repo
paths, game XML loading) are in `fe_common.py`; the game path comes from `game_path.txt` (git-ignored, first line).

| Script | Purpose | Notes |
|---|---|---|
| `fe.ps1` (`fe.bat`) | One entry point: `estado`, `modelos`, `icones`, `mod`, `tudo`, `site` | Paths to Blender / Unity at the top of the file |
| `build.ps1` | Compile the DLL (C# 5) | `-Out <path>` builds elsewhere while the game locks the DLL |
| `install.ps1` | Junction `<game>/Mods/ForgedInAshes` → repo | Removes only links/copies of this mod (and the legacy `FerroEngrenagem` one) |
| `check_xpath.py` | Every XPath patch vs vanilla XML | Must report 0 problems |
| `check_processes.py` | `Data/fe_processes.xml` consistency | Must report 0 problems |
| `check_phase3.py` | Progression / recipe rules | All rules must pass |
| `check_coverage.py` | Every vanilla craftable item has a path | |
| `list_assets.py` | Missing models / icons → `PENDENCIAS_ASSETS.md` | |
| `gen_chain.py` | Production chains (blocks, items, recipes, localization, processes) | Writes only between `BEGIN/END GENERATED`; reuses own prefab/icon when the asset exists |
| `gen_ui.py` | XUi windows | |
| `gen_site.py` | `site/public/data/mod.json` + site icons | |
| `gen_docs_art.py` | `docs/assets/*.png` | Uses only the mod's own icons |
| `blender_export_hd.py` / `blender_export_glb.py` | FBX for Unity / GLB for the site | Run by Blender in background mode |
| `apply_icons.py` | Point `CustomIcon` at the mod's own icons | |
| `il_inspect.ps1` | Read the game's IL with Mono.Cecil | Study only — never copy game code into the repo |

Rules:

- Scripts must stay idempotent: running a generator twice produces no diff.
- Write files as UTF-8; keep the BOM where the file already has one (`.ps1`, some `.cs`).
- Do not write into the game folder from a script except through `install.ps1`.
