# AGENTS.md — ForgedInAshes

Instructions for AI coding agents working in this repository. Humans: see [README.md](README.md) and
[docs/en/development.md](docs/en/development.md).

## Project in one paragraph

ForgedInAshes is a **7 Days to Die V3.4 (b10)** mod that replaces one-click crafting with production lines:
torque networks, fluids and gases with pressure, conveyor logistics, a modular steam power plant, signals and world
machines. It is made of XML patches (`Mods/ForgedInAshes/Config`), data files read by a C# DLL
(`Mods/ForgedInAshes/Data`), the DLL itself (`src/ForgedInAshes`, Harmony patches), an asset bundle built in Unity
from Blender models (`Art/`), and a tutorial website generated from the mod data (`site/`). The project was called
**Ferro & Engrenagem** until 2026-11-26; old names in `MODLOG.md` history are expected.

## Working with the maintainer

- **Talk to the maintainer in Brazilian Portuguese.** Code, comments, commit messages and English docs stay in
  English (Portuguese commit messages are also fine — follow recent history).
- **Never add `Co-Authored-By` trailers** (or any AI attribution) to commits or pull requests.
- **One commit per task.** Do not commit files that another session or the maintainer is still editing unless
  asked to commit everything.
- **Push only when explicitly asked.**
- Record every task in **`MODLOG.md`** (what changed, why, how it was verified, and "**Não verificado no jogo**"
  when it was not tested in game).

## Design decisions that are already settled

- The **Steam Engine** (`feSteamEngine`) stays the simple, cheap stop-gap engine with its original recipe. Big power
  comes from the **modular power plant** (fireboxes, boiler drums, turbines, dynamos).
- **No lava.** Keep it grounded ("Create-like, with feet on the ground").
- **Trains come late. Multiplayer fixes come last.**
- 3D models may stay pending while code and logic advance; list them in `PENDENCIAS_ASSETS.md`.

## Hard rules

| Rule | Details |
|---|---|
| No game files in the repo | Never commit DLLs, XML, textures, models or sounds of 7 Days to Die. Read them in place (`tools/game_path.txt`). The website may only publish the mod's own icons and models. |
| C# 5 only | `src/` is compiled by the .NET Framework 4 `csc.exe` (`tools/build.ps1`): no `$""`, no `?.`, no `=>` members, no `nameof`, no tuples. |
| Never rename IDs | Block and item IDs (`fe*`) are stored in player saves. Add new IDs instead. |
| Generated regions | Do not hand-edit between `BEGIN GENERATED` / `END GENERATED` markers: edit `tools/gen_chain.py` and re-run it. |
| Validators must pass | `python tools/check_xpath.py`, `check_processes.py`, `check_phase3.py`, `check_coverage.py`. |
| Localization | Every new key gets `english` and `brazilian` columns in `Mods/ForgedInAshes/Config/Localization.csv`. |
| Saves | Per-world state goes through `ForgedInAshesMod.SaveFile(name)`. |
| Game folder | Ask before changing anything in the game folder other than the mod link made by `tools/install.ps1`. |

## Commands

```powershell
fe.bat estado                                         # what is out of date (read only)
fe.bat mod                                            # validate + compile DLL + link into the game (game closed!)
fe.bat tudo                                           # models -> icons -> mod
fe.bat site                                           # GLB export + site data + site build
powershell -ExecutionPolicy Bypass -File tools\build.ps1 -Out $env:TEMP\fia.dll   # compile check while the game runs
python tools\check_xpath.py                           # XPath patches vs vanilla XML
python tools\list_assets.py                           # missing models / icons
powershell -File tools\il_inspect.ps1 -Method 'Type::Method'   # read the game's IL (study only)
```

## Verifying changes

- **The running game is the source of truth.** Reading code is not proof; read the log after a test.
- Game log: `%APPDATA%\7DaysToDie\logs\output_log_client__*.txt`; mod lines start with `[ForgedInAshes]`.
  `Mods/ForgedInAshes/debug.txt` enables verbose logging.
- When the game's behaviour is unclear, inspect its IL with `tools/il_inspect.ps1` and cite the method in a
  comment (for example `PlayerMoveController.HandleInteraction, IL 3.4.0 b10`).
- Website changes: `cd site; npm run build`, then check the pages in a browser.

## Map of the repository

| Path | Notes |
|---|---|
| [`src/ForgedInAshes/`](src/ForgedInAshes/AGENTS.md) | C# mod code |
| `Mods/ForgedInAshes/Config/` | XPath patches: `blocks.xml`, `items.xml`, `recipes.xml`, `Localization.csv`, `XUi_InGame/` |
| `Mods/ForgedInAshes/Data/` | `fe_processes.xml` (chains), `fe_settings.xml`, `fe_fallback.xml` |
| [`tools/`](tools/AGENTS.md) | Build, install, validators, generators |
| [`Art/`](Art/AGENTS.md) | Blender sources and the Unity project |
| [`site/`](site/AGENTS.md) | Tutorial website |
| [`docs/`](docs/AGENTS.md) | Documentation in en · pt-BR · es |
| `MODLOG.md` | Engineering journal — read the latest entries before starting |
| `PLANO_*.md`, `TESTE_GERAL.md`, `PENDENCIAS_ASSETS.md` | Plans, in-game test checklist, pending assets (Portuguese) |
