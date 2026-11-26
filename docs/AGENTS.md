# AGENTS.md — `docs/`

Read the [root AGENTS.md](../AGENTS.md) first.

## Structure

```text
README.md · README.pt-BR.md · README.es.md      Project front pages (root of the repo)
CONTRIBUTING.md                                  English only
docs/
├─ assets/          banner.png, social-preview.png, machines.png  (python tools/gen_docs_art.py)
├─ en/              README.md (index), installation.md, gameplay.md, troubleshooting.md, development.md
├─ pt-BR/           same files, Brazilian Portuguese
└─ es/              same files, Spanish
```

## Rules

- **English is the primary version.** Every change to an English page is mirrored in `pt-BR/` and `es/` in the
  same commit; the three trees keep the same files and the same section order.
- Every page starts with the breadcrumb + language switcher line and ends with previous / next links.
- Block names: English pages use the in-game English names, pt-BR pages the Brazilian names from
  `Localization.csv`, Spanish pages the English in-game names (the mod has no Spanish localization yet) with a
  translation on first mention.
- Numbers (UT, RPM, L/min, bar, W) must come from `Localization.csv`, `blocks.xml` or the code — never invent them.
  Mark anything not verified in game.
- GitHub-flavoured Markdown: tables, `> [!NOTE]` style alerts, Mermaid diagrams. Keep Mermaid labels plain text.
- Images: only the mod's own art (`docs/assets/`, `Mods/ForgedInAshes/UIAtlases/ItemIconAtlas/`).
- Before committing, check that every relative link and anchor resolves.
