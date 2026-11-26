# Contributing to ForgedInAshes

**English** · [Português (Brasil)](docs/pt-BR/development.md) · [Español](docs/es/development.md)

Thank you for helping! This page explains how to propose changes. The technical details live in
**[docs/en/development.md](docs/en/development.md)**.

## Reporting bugs and ideas

- Search the [existing issues](https://github.com/BirdRa1n/ForgedInAshes/issues) first.
- For a bug, attach the full game log and the steps to reproduce it — see
  [Troubleshooting → Reporting a bug](docs/en/troubleshooting.md#reporting-a-bug).
- For an idea, describe the gameplay you want, not only the block: *what problem does it solve in a factory?*

## Workflow

1. Fork the repository and create a branch from `main`.
2. Make **one change per commit**, with a clear message that says what changed and why.
3. Run `fe.bat mod` (or at least the validators) and test the change in game.
4. Add an entry to `MODLOG.md` describing what you changed and how you verified it.
5. Open a pull request describing the change, how you tested it and any screenshots.

## Ground rules

| Rule | Why |
|---|---|
| **Never commit game files** (DLLs, XML, textures, models or sounds from 7 Days to Die) | They are not ours to redistribute |
| **C# 5 only** in `src/` | The DLL is built with the .NET Framework 4 compiler |
| **Keep the `fe` prefix** on block and item IDs, and never rename an existing ID | IDs live in player saves |
| **Validators must pass** (`check_xpath`, `check_processes`, `check_phase3`, `check_coverage`) | Broken XPath silently breaks the game's XML |
| **Generated regions are generated** — edit `tools/gen_chain.py`, not the `BEGIN/END GENERATED` blocks | Hand edits are overwritten |
| **Only original assets** in `Art/`, `Mods/` and `site/` | Same as the first rule |
| **Localization in English and Brazilian Portuguese** for every new key | Both are maintained |

## Code style

- Follow the style of the file you are editing.
- Explain the *why* in comments, especially when the code works around game behaviour — quote the game method you
  read (for example `PlayerMoveController.HandleInteraction, IL 3.4.0 b10`).
- Log with `ForgedInAshesMod.LogPrefix`; keep chatty diagnostics behind `ForgedInAshesMod.Verbose`.
